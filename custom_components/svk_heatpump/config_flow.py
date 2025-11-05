"""Config flow for SVK Heatpump integration."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .api import SVKHeatpumpAPI, SVKAuthenticationError, SVKConnectionError, SVKTimeoutError, SVKInvalidResponseError
from .const import CONF_FETCH_INTERVAL, CONF_WRITE_ACCESS, DOMAIN, DEFAULT_FETCH_INTERVAL, DEFAULT_WRITE_ACCESS

_LOGGER = logging.getLogger(__name__)


class SVKHeatpumpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SVK Heatpump."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: Optional[str] = None
        self._username: Optional[str] = None
        self._password: Optional[str] = None
        self._reauth: bool = False

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            # Validate input
            if not self._host.strip():
                errors["base"] = "invalid_host"
            elif not self._username.strip():
                errors["base"] = "invalid_username"
            elif not self._password.strip():
                errors["base"] = "invalid_password"
            else:
                # Validate connection
                try:
                    _LOGGER.debug(
                        "Testing connection for host %s with user %s",
                        self._host, self._username
                    )
                    
                    api = SVKHeatpumpAPI(
                        host=self._host,
                        username=self._username,
                        password=self._password
                    )
                    await api.async_test_connection()
                    
                    # If connection is successful, proceed to options step
                    _LOGGER.info(
                        "Connection test successful for host %s",
                        self._host
                    )
                    return await self.async_step_options()
                    
                except SVKAuthenticationError as ex:
                    _LOGGER.error(
                        "Authentication error during config flow: %s",
                        ex
                    )
                    errors["base"] = "invalid_auth"
                except SVKConnectionError as ex:
                    _LOGGER.error(
                        "Connection error during config flow: %s",
                        ex
                    )
                    errors["base"] = "cannot_connect"
                except SVKTimeoutError as ex:
                    _LOGGER.error(
                        "Timeout error during config flow: %s",
                        ex
                    )
                    errors["base"] = "timeout"
                except SVKInvalidResponseError as ex:
                    _LOGGER.error(
                        "Invalid response during config flow: %s",
                        ex
                    )
                    errors["base"] = "invalid_response"
                except Exception as ex:  # pragma: no cover
                    _LOGGER.error(
                        "Unexpected error during config flow: %s",
                        ex, exc_info=True
                    )
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): vol.All(str, vol.Match(r'^[a-zA-Z0-9\.\-\:]+$')),
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_options(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the options step."""
        if user_input is not None:
            # Validate options
            fetch_interval = user_input.get(CONF_FETCH_INTERVAL, DEFAULT_FETCH_INTERVAL)
            
            # Validate fetch interval
            if not isinstance(fetch_interval, int) or fetch_interval < 10 or fetch_interval > 300:
                return self.async_show_form(
                    step_id="options",
                    data_schema=vol.Schema(
                        {
                            vol.Optional(
                                CONF_WRITE_ACCESS, default=DEFAULT_WRITE_ACCESS
                            ): bool,
                            vol.Optional(
                                CONF_FETCH_INTERVAL, default=DEFAULT_FETCH_INTERVAL
                            ): vol.All(int, vol.Range(min=10, max=300)),
                        }
                    ),
                    errors={"base": "invalid_fetch_interval"},
                )
            
            try:
                # Create the config entry with all data
                _LOGGER.info(
                    "Creating config entry for host %s with write_access=%s, fetch_interval=%d",
                    self._host,
                    user_input[CONF_WRITE_ACCESS],
                    fetch_interval
                )
                
                return self.async_create_entry(
                    title=f"SVK Heatpump ({self._host})",
                    data={
                        CONF_HOST: self._host,
                        CONF_USERNAME: self._username,
                        CONF_PASSWORD: self._password,
                        CONF_WRITE_ACCESS: user_input[CONF_WRITE_ACCESS],
                        CONF_FETCH_INTERVAL: fetch_interval,
                    },
                )
            except Exception as ex:
                _LOGGER.error(
                    "Error creating config entry: %s",
                    ex, exc_info=True
                )
                return self.async_show_form(
                    step_id="options",
                    data_schema=vol.Schema(
                        {
                            vol.Optional(
                                CONF_WRITE_ACCESS, default=DEFAULT_WRITE_ACCESS
                            ): bool,
                            vol.Optional(
                                CONF_FETCH_INTERVAL, default=DEFAULT_FETCH_INTERVAL
                            ): vol.All(int, vol.Range(min=10, max=300)),
                        }
                    ),
                    errors={"base": "unknown"},
                )

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_WRITE_ACCESS, default=DEFAULT_WRITE_ACCESS
                    ): bool,
                    vol.Optional(
                        CONF_FETCH_INTERVAL, default=DEFAULT_FETCH_INTERVAL
                    ): vol.All(int, vol.Range(min=10, max=300)),
                }
            ),
        )

    async def async_step_reauth(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle reauthentication step."""
        self._reauth = True
        
        # Get existing config entry to preserve host
        if self.context.get("entry_id"):
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            if entry:
                self._host = entry.data.get(CONF_HOST)
                _LOGGER.info(
                    "Starting reauth flow for host %s",
                    self._host
                )
        
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            # Validate input
            if not self._username.strip():
                errors["base"] = "invalid_username"
            elif not self._password.strip():
                errors["base"] = "invalid_password"
            else:
                # Validate connection with new credentials
                try:
                    _LOGGER.debug(
                        "Testing reauth connection for host %s with user %s",
                        self._host, self._username
                    )
                    
                    api = SVKHeatpumpAPI(
                        host=self._host,
                        username=self._username,
                        password=self._password
                    )
                    await api.async_test_connection()
                    
                    # Update the existing entry with new credentials
                    if self.context.get("entry_id"):
                        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                        if entry:
                            data = dict(entry.data)
                            data[CONF_USERNAME] = self._username
                            data[CONF_PASSWORD] = self._password
                            
                            self.hass.config_entries.async_update_entry(
                                entry, data=data
                            )
                            
                            # Update coordinator credentials if it exists
                            if DOMAIN in self.hass.data:
                                coordinator = self.hass.data[DOMAIN].get(entry.entry_id)
                                if coordinator:
                                    _LOGGER.info(
                                        "Updating coordinator credentials for entry %s",
                                        entry.entry_id
                                    )
                                    coordinator.username = self._username
                                    coordinator.password = self._password
                                    # Reinitialize API client with new credentials
                                    coordinator.api = SVKHeatpumpAPI(
                                        host=coordinator.host,
                                        username=self._username,
                                        password=self._password,
                                    )
                                    # Mark reauth as complete
                                    coordinator.set_reauth_complete()
                    
                    _LOGGER.info(
                        "Reauthentication successful for host %s",
                        self._host
                    )
                    return self.async_abort(reason="reauth_successful")
                    
                except SVKAuthenticationError as ex:
                    _LOGGER.error(
                        "Authentication error during reauth: %s",
                        ex
                    )
                    errors["base"] = "invalid_auth"
                except SVKConnectionError as ex:
                    _LOGGER.error(
                        "Connection error during reauth: %s",
                        ex
                    )
                    errors["base"] = "cannot_connect"
                except SVKTimeoutError as ex:
                    _LOGGER.error(
                        "Timeout error during reauth: %s",
                        ex
                    )
                    errors["base"] = "timeout"
                except SVKInvalidResponseError as ex:
                    _LOGGER.error(
                        "Invalid response during reauth: %s",
                        ex
                    )
                    errors["base"] = "invalid_response"
                except Exception as ex:  # pragma: no cover
                    _LOGGER.error(
                        "Unexpected error during reauth: %s",
                        ex, exc_info=True
                    )
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )


class SVKHeatpumpOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for SVK Heatpump."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Validate the options
            write_access = user_input.get(CONF_WRITE_ACCESS, DEFAULT_WRITE_ACCESS)
            fetch_interval = user_input.get(CONF_FETCH_INTERVAL, DEFAULT_FETCH_INTERVAL)
            
            # Validate fetch interval range
            if not isinstance(fetch_interval, int) or fetch_interval < 10 or fetch_interval > 300:
                errors["base"] = "invalid_fetch_interval"
            else:
                try:
                    # Update the config entry
                    data = dict(self.config_entry.data)
                    data[CONF_WRITE_ACCESS] = write_access
                    data[CONF_FETCH_INTERVAL] = fetch_interval
                    
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=data
                    )
                    
                    # Get coordinator and update its configuration
                    if DOMAIN in self.hass.data:
                        coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
                        if coordinator:
                            _LOGGER.info(
                                "Updating coordinator configuration for entry %s: write_access=%s, fetch_interval=%d",
                                self.config_entry.entry_id, write_access, fetch_interval
                            )
                            await coordinator.async_update_config({
                                CONF_WRITE_ACCESS: write_access,
                                CONF_FETCH_INTERVAL: fetch_interval,
                            })
                    
                    _LOGGER.info(
                        "Options updated successfully for entry %s",
                        self.config_entry.entry_id
                    )
                    return self.async_create_entry(title="", data={})
                except Exception as ex:
                    _LOGGER.error(
                        "Error updating options: %s",
                        ex, exc_info=True
                    )
                    errors["base"] = "unknown"

        # Get current values
        current_write_access = self.config_entry.data.get(CONF_WRITE_ACCESS, DEFAULT_WRITE_ACCESS)
        current_fetch_interval = self.config_entry.data.get(CONF_FETCH_INTERVAL, DEFAULT_FETCH_INTERVAL)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_WRITE_ACCESS, default=current_write_access
                    ): bool,
                    vol.Optional(
                        CONF_FETCH_INTERVAL, default=current_fetch_interval
                    ): vol.All(int, vol.Range(min=10, max=300)),
                }
            ),
            errors=errors,
        )