"""Config flow for SVK Heatpump integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .client import LOMJsonClient, SVKConnectionError, SVKAuthenticationError
from .const import (
    CONF_ENABLE_COUNTERS,
    CONF_ENABLE_SOLAR,
    CONF_ENABLE_WRITES,
    CONF_ID_LIST,
    CONF_SCAN_INTERVAL,
    DEFAULT_IDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    DEFAULT_TIMEOUT,
    parse_id_list,
    validate_id_list,
)

# Configuration constants for authentication
CONF_ALLOW_BASIC_AUTH = "allow_basic_auth"


_LOGGER = logging.getLogger(__name__)


class SVKHeatpumpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SVK Heatpump."""
    
    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self._host: Optional[str] = None
        self._username: Optional[str] = None
        self._password: Optional[str] = None
        self._allow_basic_auth: bool = False
        self._reauth_entry: Optional[config_entries.ConfigEntry] = None
    
    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._username = user_input.get(CONF_USERNAME, "")
            self._password = user_input.get(CONF_PASSWORD, "")
            self._allow_basic_auth = user_input.get(CONF_ALLOW_BASIC_AUTH, False)
            id_list_str = user_input.get(CONF_ID_LIST, DEFAULT_IDS)
            
            # Validate ID list format if provided
            if id_list_str and not validate_id_list(id_list_str):
                errors[CONF_ID_LIST] = "invalid_id_list"
            else:
                # Test connection
                await self.async_set_unique_id(self._host)
                self._abort_if_unique_id_configured()
                
                client = LOMJsonClient(
                    self._host,
                    self._username,
                    self._password,
                    DEFAULT_TIMEOUT,
                    allow_basic_auth=self._allow_basic_auth
                )
                
                try:
                    # Start the client session
                    await client.start()
                    
                    # Parse ID list for validation
                    test_ids = parse_id_list(id_list_str or DEFAULT_IDS)
                    
                    # Validate connection by calling read_values with test IDs
                    # Accept any successful JSON response as validation
                    json_data = await client.read_values(test_ids)
                    
                    if json_data is None:
                        errors["base"] = "invalid_response"
                    else:
                        # Connection successful, create entry
                        return self.async_create_entry(
                            title=f"SVK Heatpump ({self._host})",
                            data={
                                CONF_HOST: self._host,
                                CONF_USERNAME: self._username,
                                CONF_PASSWORD: self._password,
                                CONF_ALLOW_BASIC_AUTH: self._allow_basic_auth,
                            },
                            options={
                                CONF_ID_LIST: id_list_str or DEFAULT_IDS,
                            }
                        )
                        
                except SVKAuthenticationError as auth_err:
                    # Check if this is a Digest authentication issue
                    error_msg = str(auth_err)
                    if "does not support Digest authentication" in error_msg:
                        errors["base"] = "unexpected_auth_scheme"
                        _LOGGER.error("Device at %s returned unexpected auth scheme (not Digest)", self._host)
                    elif "Invalid username or password" in error_msg:
                        errors["base"] = "invalid_auth"
                        _LOGGER.error("Digest authentication failed for host %s", self._host)
                    else:
                        errors["base"] = "invalid_auth"
                        _LOGGER.error("Authentication failed for host %s: %s", self._host, error_msg)
                except SVKConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                finally:
                    await client.close()
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_USERNAME, default=""): str,
                vol.Optional(CONF_PASSWORD, default=""): str,
                vol.Optional(CONF_ID_LIST, default=DEFAULT_IDS): str,
                vol.Optional(CONF_ALLOW_BASIC_AUTH, default=False): bool,
            }),
            errors=errors,
        )
    
    async def async_step_reauth(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle reauthentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        
        return await self.async_step_reauth_confirm(user_input)
    
    async def async_step_reauth_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle reauthentication confirmation."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            host = self._reauth_entry.data[CONF_HOST]
            username = user_input.get(CONF_USERNAME, "")
            password = user_input.get(CONF_PASSWORD, "")
            allow_basic_auth = user_input.get(CONF_ALLOW_BASIC_AUTH, False)
            
            client = LOMJsonClient(host, username, password, DEFAULT_TIMEOUT, allow_basic_auth=allow_basic_auth)
            
            try:
                # Start the client session
                await client.start()
                
                # Get ID list from options or use default
                id_list_str = self._reauth_entry.options.get(CONF_ID_LIST, DEFAULT_IDS)
                test_ids = parse_id_list(id_list_str)
                
                # Validate connection by calling read_values with test IDs
                json_data = await client.read_values(test_ids)
                
                if json_data is None:
                    errors["base"] = "invalid_response"
                else:
                    # Update entry with new credentials
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry,
                        data={
                            **self._reauth_entry.data,
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                        }
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
                    _LOGGER.error("Device at %s returned unexpected auth scheme (not Digest)", host)
                elif "Invalid username or password" in error_msg:
                    errors["base"] = "invalid_auth"
                    _LOGGER.error("Digest authentication failed during reauth for host %s", host)
                else:
                    errors["base"] = "invalid_auth"
                    _LOGGER.error("Authentication failed during reauth for host %s: %s", host, error_msg)
            except SVKConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            finally:
                await client.close()
        
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({
                vol.Optional(CONF_USERNAME, default=""): str,
                vol.Optional(CONF_PASSWORD, default=""): str,
                vol.Optional(CONF_ALLOW_BASIC_AUTH, default=False): bool,
            }),
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
    
    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
    
    def _get_options_schema(self) -> vol.Schema:
        """Get the options schema."""
        options = self.config_entry.options
        return vol.Schema({
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ): int,
            vol.Optional(
                CONF_ENABLE_SOLAR,
                default=options.get(CONF_ENABLE_SOLAR, True)
            ): bool,
            vol.Optional(
                CONF_ENABLE_COUNTERS,
                default=options.get(CONF_ENABLE_COUNTERS, True)
            ): bool,
            vol.Optional(
                CONF_ENABLE_WRITES,
                default=options.get(CONF_ENABLE_WRITES, False)
            ): bool,
            vol.Optional(
                CONF_ID_LIST,
                default=options.get(CONF_ID_LIST, DEFAULT_IDS)
            ): str,
        })
    
    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            try:
                # Validate scan interval
                scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                if not isinstance(scan_interval, int) or not 10 <= scan_interval <= 120:
                    errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
                
                # Handle ID list
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
                    
                    # Trigger coordinator reload to apply new ID list
                    try:
                        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    except Exception as ex:
                        _LOGGER.error("Failed to reload config entry: %s", ex)
                        errors["base"] = "reload_failed"
                        return self.async_show_form(
                            step_id="init",
                            data_schema=self._get_options_schema(),
                            errors=errors,
                            description_placeholders={
                                "default_ids": DEFAULT_IDS,
                                "id_list_example": "299;255;256"
                            }
                        )
                    
                    return result
            except Exception as ex:
                _LOGGER.exception("Unexpected error in options flow: %s", ex)
                errors["base"] = "unknown"
        
        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(),
            errors=errors,
            description_placeholders={
                "default_ids": DEFAULT_IDS,
                "id_list_example": "299;255;256"
            }
        )