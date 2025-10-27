"""Config flow for SVK Heatpump integration."""

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .client import (
    LOMJsonClient,
    SVKAuthenticationError,
    SVKConnectionError,
    SVKHTMLResponseError,
    SVKInvalidDataFormatError,
    SVKParseError,
    SVKTimeoutError,
)
from .const import (
    CONF_ENABLE_WRITES,
    CONF_ID_LIST,
    CONF_SCAN_INTERVAL,
    DEFAULT_IDS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    validate_id_list,
)

# Configuration constants for authentication


_LOGGER = logging.getLogger(__name__)


class SVKHeatpumpConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for SVK Heatpump."""

    VERSION = 1
    
    # Set the domain for compatibility
    DOMAIN = DOMAIN

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: str | None = None
        self._username: str | None = None
        self._password: str | None = None
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._username = user_input.get(CONF_USERNAME, "")
            self._password = user_input.get(CONF_PASSWORD, "")

            # Test connection
            await self.async_set_unique_id(self._host)
            self._abort_if_unique_id_configured()

            client = LOMJsonClient(
                self._host or "",
                self._username or "",
                self._password or "",
                DEFAULT_TIMEOUT,
            )

            try:
                # Start the client session
                await client.start()

                # First, test basic connectivity
                _LOGGER.info("Testing basic connectivity to heat pump")
                connection_test = await client.test_connection()
                if not connection_test:
                    _LOGGER.error(
                        "Basic connectivity test failed for host %s", self._host
                    )
                    errors["base"] = "cannot_connect"
                    await client.close()
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONF_HOST): str,
                                vol.Optional(CONF_USERNAME, default=""): str,
                                vol.Optional(CONF_PASSWORD, default=""): str,
                            }
                        ),
                        errors=errors,
                    )

                # If basic connectivity works, try with actual data request
                # Use a smaller subset of essential IDs for validation to avoid timeout
                essential_ids = [253, 254, 255, 256, 257]  # Core temperature sensors

                # Validate connection by calling read_values with test IDs
                # Accept any successful JSON response as validation
                _LOGGER.debug(
                    "Testing connection with %d essential IDs: %s",
                    len(essential_ids),
                    essential_ids,
                )  # Log first 5 IDs

                # Add timeout protection to prevent blocking Home Assistant startup
                try:
                    json_data = await asyncio.wait_for(
                        client.read_values(essential_ids),
                        timeout=15.0,  # 15 second timeout for connection test
                    )
                except asyncio.TimeoutError:
                    _LOGGER.error(
                        "Connection test timed out after 15 seconds for host %s",
                        self._host,
                    )
                    errors["base"] = "timeout"
                    await client.close()
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONF_HOST): str,
                                vol.Optional(CONF_USERNAME, default=""): str,
                                vol.Optional(CONF_PASSWORD, default=""): str,
                            }
                        ),
                        errors=errors,
                    )

                _LOGGER.debug(
                    "Received response type: %s, length: %d",
                    type(json_data),
                    len(json_data) if json_data else 0,
                )

                if json_data is None:
                    errors["base"] = "invalid_response"
                elif not json_data:
                    errors["base"] = "invalid_response"
                    _LOGGER.error("Empty data response from host %s", self._host)
                elif not isinstance(json_data, list):
                    errors["base"] = "invalid_response"
                    _LOGGER.error(
                        "Invalid response format from host %s: expected list, got %s",
                        self._host,
                        type(json_data),
                    )
                elif len(json_data) == 0:
                    errors["base"] = "invalid_response"
                    _LOGGER.error("No data items returned from host %s", self._host)
                else:
                    # Validate that response contains expected structure
                    valid_items = 0
                    sample_items = []  # Store a few sample items for debugging
                    for item in json_data:
                        if isinstance(item, dict) and "id" in item and "value" in item:
                            valid_items += 1
                            if len(sample_items) < 3:  # Store first 3 valid items
                                sample_items.append(item)

                    if valid_items == 0:
                        errors["base"] = "invalid_response"
                        _LOGGER.error(
                            "No valid items found in response from host %s", self._host
                        )
                        _LOGGER.debug(
                            "Response items: %s", json_data[:5]
                        )  # Log first 5 items for debugging
                    else:
                        _LOGGER.debug(
                            "Successfully validated connection to %s: %d valid items",
                            self._host,
                            valid_items,
                        )
                        _LOGGER.debug("Sample items: %s", sample_items)
                        # Connection successful, proceed to entity management explanation
                        self._client = client
                        return await self.async_step_entity_management()

            except SVKAuthenticationError as auth_err:
                # Check if this is a Digest authentication issue
                error_msg = str(auth_err)
                if "does not support Digest authentication" in error_msg:
                    errors["base"] = "unexpected_auth_scheme"
                    _LOGGER.error(
                        "Device at %s returned unexpected auth scheme (not Digest)",
                        self._host,
                    )
                elif "Invalid username or password" in error_msg:
                    errors["base"] = "invalid_auth"
                    _LOGGER.error(
                        "Digest authentication failed for host %s", self._host
                    )
                else:
                    errors["base"] = "invalid_auth"
                    _LOGGER.error(
                        "Authentication failed for host %s: %s", self._host, error_msg
                    )
            except SVKTimeoutError as timeout_err:
                errors["base"] = "timeout"
                _LOGGER.error(
                    "Connection timeout for host %s: %s", self._host, timeout_err
                )
            except SVKParseError as parse_err:
                # Handle different types of parse errors with specific messages
                if isinstance(parse_err, SVKInvalidDataFormatError):
                    errors["base"] = "invalid_data_format"
                    _LOGGER.error(
                        "Invalid data format from host %s: %s",
                        self._host,
                        parse_err.message,
                    )
                elif isinstance(parse_err, SVKHTMLResponseError):
                    errors["base"] = "html_error_response"
                    _LOGGER.error(
                        "Received HTML error page from host %s: %s",
                        self._host,
                        parse_err.message,
                    )
                else:
                    errors["base"] = "parse_error"
                    _LOGGER.error(
                        "Failed to parse response from host %s: %s",
                        self._host,
                        parse_err,
                    )
            except SVKConnectionError as conn_err:
                errors["base"] = "cannot_connect"
                _LOGGER.error("Connection error for host %s: %s", self._host, conn_err)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            finally:
                if "_client" not in locals():
                    await client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_USERNAME, default=""): str,
                    vol.Optional(CONF_PASSWORD, default=""): str,
                }
            ),
            errors=errors,
        )

    async def async_step_entity_management(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the entity management explanation step."""
        # This step is shown for information only and automatically proceeds
        # Close the client if it's still open
        if hasattr(self, "_client"):
            await self._client.close()
            delattr(self, "_client")

        # Always proceed to create entry after showing the explanation
        return self.async_create_entry(
            title=f"SVK Heatpump ({self._host or 'unknown'})",
            data={
                CONF_HOST: self._host or "",
                CONF_USERNAME: self._username or "",
                CONF_PASSWORD: self._password or "",
            },
            options={
                # Keep empty options for new configurations
                # Entity management will be handled through the UI
            },
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        return await self.async_step_reauth_confirm(user_input)

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if self._reauth_entry is None:
                errors["base"] = "invalid_reauth"
                return self.async_show_form(
                    step_id="reauth_confirm",
                    data_schema=vol.Schema(
                        {
                            vol.Optional(CONF_USERNAME, default=""): str,
                            vol.Optional(CONF_PASSWORD, default=""): str,
                        }
                    ),
                    errors=errors,
                )
            
            host = self._reauth_entry.data[CONF_HOST]
            username = user_input.get(CONF_USERNAME, "")
            password = user_input.get(CONF_PASSWORD, "")

            client = LOMJsonClient(
                host or "",
                username or "",
                password or "",
                DEFAULT_TIMEOUT,
            )

            try:
                # Start the client session
                await client.start()

                # First, test basic connectivity
                _LOGGER.info("Testing basic connectivity during reauth")
                connection_test = await client.test_connection()
                if not connection_test:
                    _LOGGER.error(
                        "Basic connectivity test failed during reauth for host %s", host
                    )
                    errors["base"] = "cannot_connect"
                    await client.close()
                    return self.async_show_form(
                        step_id="reauth_confirm",
                        data_schema=vol.Schema(
                            {
                                vol.Optional(CONF_USERNAME, default=""): str,
                                vol.Optional(CONF_PASSWORD, default=""): str,
                            }
                        ),
                        errors=errors,
                    )

                # If basic connectivity works, try with actual data request
                # Use a smaller subset of essential IDs for validation to avoid timeout
                essential_ids = [253, 254, 255, 256, 257]  # Core temperature sensors

                # Validate connection by calling read_values with test IDs
                _LOGGER.debug(
                    "Testing connection during reauth with %d essential IDs: %s",
                    len(essential_ids),
                    essential_ids,
                )  # Log first 5 IDs

                # Add timeout protection to prevent blocking Home Assistant startup
                try:
                    json_data = await asyncio.wait_for(
                        client.read_values(essential_ids),
                        timeout=15.0,  # 15 second timeout for connection test
                    )
                except asyncio.TimeoutError:
                    _LOGGER.error(
                        "Connection test timed out after 15 seconds during reauth for host %s",
                        host,
                    )
                    errors["base"] = "timeout"
                    await client.close()
                    return self.async_show_form(
                        step_id="reauth_confirm",
                        data_schema=vol.Schema(
                            {
                                vol.Optional(CONF_USERNAME, default=""): str,
                                vol.Optional(CONF_PASSWORD, default=""): str,
                            }
                        ),
                        errors=errors,
                    )

                _LOGGER.debug(
                    "Received response type during reauth: %s, length: %d",
                    type(json_data),
                    len(json_data) if json_data else 0,
                )

                if json_data is None:
                    errors["base"] = "invalid_response"
                elif not json_data:
                    errors["base"] = "invalid_response"
                    _LOGGER.error(
                        "Empty data response from host %s during reauth", host
                    )
                elif not isinstance(json_data, list):
                    errors["base"] = "invalid_response"
                    _LOGGER.error(
                        "Invalid response format from host %s during reauth: expected list, got %s",
                        host,
                        type(json_data),
                    )
                elif len(json_data) == 0:
                    errors["base"] = "invalid_response"
                    _LOGGER.error(
                        "No data items returned from host %s during reauth", host
                    )
                else:
                    # Validate that response contains expected structure
                    valid_items = 0
                    sample_items = []  # Store a few sample items for debugging
                    for item in json_data:
                        if isinstance(item, dict) and "id" in item and "value" in item:
                            valid_items += 1
                            if len(sample_items) < 3:  # Store first 3 valid items
                                sample_items.append(item)

                    if valid_items == 0:
                        errors["base"] = "invalid_response"
                        _LOGGER.error(
                            "No valid items found in response from host %s during reauth",
                            host,
                        )
                        _LOGGER.debug(
                            "Response items during reauth: %s", json_data[:5]
                        )  # Log first 5 items for debugging
                    else:
                        _LOGGER.debug(
                            "Successfully validated connection to %s during reauth: %d valid items",
                            host,
                            valid_items,
                        )
                        _LOGGER.debug("Sample items during reauth: %s", sample_items)
                        # Update entry with new credentials
                        if self._reauth_entry is not None:
                            self.hass.config_entries.async_update_entry(
                                self._reauth_entry,
                                data={
                                    **self._reauth_entry.data,
                                    CONF_USERNAME: username,
                                    CONF_PASSWORD: password,
                                },
                            )
                            await self.hass.config_entries.async_reload(
                                self._reauth_entry.entry_id
                            )
                        return self.async_abort(reason="reauth_successful")

            except SVKAuthenticationError as auth_err:
                # Check if this is a Digest authentication issue
                error_msg = str(auth_err)
                if "does not support Digest authentication" in error_msg:
                    errors["base"] = "unexpected_auth_scheme"
                    _LOGGER.error(
                        "Device at %s returned unexpected auth scheme (not Digest)",
                        host,
                    )
                elif "Invalid username or password" in error_msg:
                    errors["base"] = "invalid_auth"
                    _LOGGER.error(
                        "Digest authentication failed during reauth for host %s", host
                    )
                else:
                    errors["base"] = "invalid_auth"
                    _LOGGER.error(
                        "Authentication failed during reauth for host %s: %s",
                        host,
                        error_msg,
                    )
            except SVKTimeoutError as timeout_err:
                errors["base"] = "timeout"
                _LOGGER.error(
                    "Connection timeout during reauth for host %s: %s",
                    host,
                    timeout_err,
                )
            except SVKParseError as parse_err:
                # Handle different types of parse errors with specific messages
                if isinstance(parse_err, SVKInvalidDataFormatError):
                    errors["base"] = "invalid_data_format"
                    _LOGGER.error(
                        "Invalid data format during reauth for host %s: %s",
                        host,
                        parse_err.message,
                    )
                elif isinstance(parse_err, SVKHTMLResponseError):
                    errors["base"] = "html_error_response"
                    _LOGGER.error(
                        "Received HTML error page during reauth for host %s: %s",
                        host,
                        parse_err.message,
                    )
                else:
                    errors["base"] = "parse_error"
                    _LOGGER.error(
                        "Failed to parse response during reauth for host %s: %s",
                        host,
                        parse_err,
                    )
            except SVKConnectionError as conn_err:
                errors["base"] = "cannot_connect"
                _LOGGER.error(
                    "Connection error during reauth for host %s: %s", host, conn_err
                )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            finally:
                await client.close()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_USERNAME, default=""): str,
                    vol.Optional(CONF_PASSWORD, default=""): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return SVKHeatpumpOptionsFlow(config_entry)


class SVKHeatpumpOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for SVK Heatpump."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry_id = config_entry.entry_id

    def _get_options_schema(self) -> vol.Schema:
        """Get the options schema."""
        config_entry = self.hass.config_entries.async_get_entry(self._entry_id)
        options = config_entry.options

        # Check if this is a legacy configuration with custom ID list
        has_custom_id_list = (
            CONF_ID_LIST in options and options.get(CONF_ID_LIST) != DEFAULT_IDS
        )

        # Get the warning description for enable_writes
        # We'll use a hardcoded warning here since we can't easily access translations in schema
        # The warning will be shown in the form display instead

        # Build schema based on configuration type
        schema_fields = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): int,
            vol.Optional(
                CONF_ENABLE_WRITES,
                default=options.get(CONF_ENABLE_WRITES, False)
            ): bool,
        }

        # Only include ID list field for legacy configurations
        if has_custom_id_list:
            schema_fields[
                vol.Optional(
                    CONF_ID_LIST, default=options.get(CONF_ID_LIST, DEFAULT_IDS)
                )
            ] = str

        return vol.Schema(schema_fields)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate scan interval
                scan_interval = user_input.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
                if not isinstance(scan_interval, int) or not 10 <= scan_interval <= 120:
                    errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"

                # Handle ID list only for legacy configurations
                config_entry = self.hass.config_entries.async_get_entry(self._entry_id)
                if CONF_ID_LIST in config_entry.options:
                    id_list_str = user_input.get(CONF_ID_LIST, "").strip()

                    # If empty, use default
                    if not id_list_str:
                        id_list_str = DEFAULT_IDS
                        user_input[CONF_ID_LIST] = DEFAULT_IDS

                    # Validate ID list format if provided
                    if id_list_str and not validate_id_list(id_list_str):
                        errors[CONF_ID_LIST] = "invalid_id_list"

                if not errors:
                    # Save options
                    result = self.async_create_entry(
                        title="",
                        data=user_input,
                    )

                    # Trigger coordinator reload to apply new settings
                    try:
                        await self.hass.config_entries.async_reload(self._entry_id)
                    except Exception as ex:
                        _LOGGER.error("Failed to reload config entry: %s", ex)
                        errors["base"] = "reload_failed"
                        return self.async_show_form(
                            step_id="init",
                            data_schema=self._get_options_schema(),
                            errors=errors,
                            description_placeholders={
                                "default_ids": DEFAULT_IDS,
                                "id_list_example": "299;255;256",
                            },
                        )

                    return result
            except Exception as ex:
                _LOGGER.exception("Unexpected error in options flow: %s", ex)
                errors["base"] = "unknown"

        # Determine if this is a legacy configuration
        config_entry = self.hass.config_entries.async_get_entry(self._entry_id)
        has_custom_id_list = (
            CONF_ID_LIST in config_entry.options
            and config_entry.options.get(CONF_ID_LIST) != DEFAULT_IDS
        )

        # Set appropriate description placeholders
        if has_custom_id_list:
            description_placeholders = {
                "default_ids": DEFAULT_IDS,
                "id_list_example": "299;255;256",
                "id_list_description": "The ID List field is shown because you have a legacy configuration with custom IDs. For new installations, entity management is handled through the UI.",
            }
        else:
            description_placeholders = {"id_list_description": ""}

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(),
            errors=errors,
            description_placeholders=description_placeholders,
        )
