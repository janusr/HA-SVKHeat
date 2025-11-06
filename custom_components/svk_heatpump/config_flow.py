"""Config flow for SVK Heatpump integration."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .api import SVKHeatpumpAPI, SVKAuthenticationError, SVKConnectionError, SVKTimeoutError, SVKInvalidResponseError
from .const import CONF_FETCH_INTERVAL, CONF_WRITE_ACCESS, DOMAIN, DEFAULT_FETCH_INTERVAL, DEFAULT_WRITE_ACCESS

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
) -> bool:
    """Migrate old entry format to new format."""
    if config_entry.version == 1:
        _LOGGER.info("Migrating config entry from version 1 to 2")
        
        # Extract options from data
        old_data = dict(config_entry.data)
        
        options = {
            CONF_WRITE_ACCESS: old_data.pop(CONF_WRITE_ACCESS, DEFAULT_WRITE_ACCESS),
            CONF_FETCH_INTERVAL: old_data.pop(CONF_FETCH_INTERVAL, DEFAULT_FETCH_INTERVAL),
        }
        
        # Update entry with separated data and options
        hass.config_entries.async_update_entry(
            config_entry,
            data=old_data,
            options=options,
            version=2
        )
        
        _LOGGER.info(
            "Migration completed: data=%s, options=%s",
            old_data,
            options
        )
        
    return True


class SVKHeatpumpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SVK Heatpump."""

    VERSION = 2

    @staticmethod
    async def async_migrate_entry(
        hass: HomeAssistant, config_entry: config_entries.ConfigEntry
    ) -> bool:
        """Migrate old entry format to new format."""
        return await async_migrate_entry(hass, config_entry)

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
        existing_entries = self._async_current_entries()
        if existing_entries:
            return self.async_abort(reason="single_instance_allowed")
            
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
                    vol.Required(CONF_HOST): str,
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
                # Create the config entry with core connection data only
                # Options will be stored separately
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
                    },
                    options={
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
                                    # Use the async_update_connection method for consistency
                                    await coordinator.async_update_connection({
                                        CONF_HOST: coordinator.host,
                                        CONF_USERNAME: self._username,
                                        CONF_PASSWORD: self._password,
                                    })
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
    """Handle enhanced options flow for SVK Heatpump."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._connection_data = {}
        self._options_data = {}
        self._configure_connection = False
        self._configure_options = False

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step - menu selection."""
        if user_input is not None:
            # Get the selected menu option
            selected_option = user_input.get("next_step_id")
            
            # Determine what to configure based on user selection
            if selected_option == "connection":
                self._configure_connection = True
                self._configure_options = False
                return await self.async_step_connection()
            elif selected_option == "options":
                self._configure_connection = False
                self._configure_options = True
                return await self.async_step_options()
            elif selected_option == "all":
                self._configure_connection = True
                self._configure_options = True
                return await self.async_step_connection()

        # Show menu selection
        return self.async_show_menu(
            step_id="init",
            menu_options=["connection", "options", "all"],
        )

    async def async_step_connection(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle connection configuration step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Validate input
            host = user_input.get(CONF_HOST, "").strip()
            username = user_input.get(CONF_USERNAME, "").strip()
            password = user_input.get(CONF_PASSWORD, "").strip()
            
            if not host:
                errors["base"] = "invalid_host"
            elif not username:
                errors["base"] = "invalid_username"
            elif not password:
                errors["base"] = "invalid_password"
            else:
                # Test connection
                try:
                    _LOGGER.debug(
                        "Testing connection for host %s with user %s",
                        host, username
                    )
                    
                    api = SVKHeatpumpAPI(
                        host=host,
                        username=username,
                        password=password
                    )
                    await api.async_test_connection()
                    
                    # Connection successful, store data
                    self._connection_data = {
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    }
                    
                    _LOGGER.info(
                        "Connection test successful for host %s",
                        host
                    )
                    
                    # If we also need to configure options, go to options step
                    if self._configure_options:
                        return await self.async_step_options()
                    else:
                        # Save and exit
                        return await self._save_configuration()
                        
                except SVKAuthenticationError as ex:
                    _LOGGER.error(
                        "Authentication error during options flow: %s",
                        ex
                    )
                    errors["base"] = "invalid_auth"
                except SVKConnectionError as ex:
                    _LOGGER.error(
                        "Connection error during options flow: %s",
                        ex
                    )
                    errors["base"] = "cannot_connect"
                except SVKTimeoutError as ex:
                    _LOGGER.error(
                        "Timeout error during options flow: %s",
                        ex
                    )
                    errors["base"] = "timeout"
                except SVKInvalidResponseError as ex:
                    _LOGGER.error(
                        "Invalid response during options flow: %s",
                        ex
                    )
                    errors["base"] = "invalid_response"
                except Exception as ex:  # pragma: no cover
                    _LOGGER.error(
                        "Unexpected error during options flow: %s",
                        ex, exc_info=True
                    )
                    errors["base"] = "unknown"

        # Get current values from config entry data
        current_host = self.config_entry.data.get(CONF_HOST, "")
        current_username = self.config_entry.data.get(CONF_USERNAME, "")

        return self.async_show_form(
            step_id="connection",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current_host): str,
                    vol.Required(CONF_USERNAME, default=current_username): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_options(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle options configuration step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Validate the options
            write_access = user_input.get(CONF_WRITE_ACCESS, DEFAULT_WRITE_ACCESS)
            fetch_interval = user_input.get(CONF_FETCH_INTERVAL, DEFAULT_FETCH_INTERVAL)
            
            # Validate fetch interval range
            if not isinstance(fetch_interval, int) or fetch_interval < 10 or fetch_interval > 300:
                errors["base"] = "invalid_fetch_interval"
            else:
                # Store options data
                self._options_data = {
                    CONF_WRITE_ACCESS: write_access,
                    CONF_FETCH_INTERVAL: fetch_interval,
                }
                
                # Save and exit
                return await self._save_configuration()

        # Get current values from config entry options, fallback to data for migration
        current_write_access = self.config_entry.options.get(
            CONF_WRITE_ACCESS,
            self.config_entry.data.get(CONF_WRITE_ACCESS, DEFAULT_WRITE_ACCESS)
        )
        current_fetch_interval = self.config_entry.options.get(
            CONF_FETCH_INTERVAL,
            self.config_entry.data.get(CONF_FETCH_INTERVAL, DEFAULT_FETCH_INTERVAL)
        )

        return self.async_show_form(
            step_id="options",
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

    async def async_step_all(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle configuring all settings."""
        # This is a menu option that routes to connection first
        self._configure_connection = True
        self._configure_options = True
        return await self.async_step_connection()

    async def _save_configuration(self) -> FlowResult:
        """Save the configuration based on what was changed."""
        try:
            # Update connection data if changed
            if self._configure_connection and self._connection_data:
                new_data = dict(self.config_entry.data)
                new_data.update(self._connection_data)
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
                
                # Update coordinator with new connection parameters
                if DOMAIN in self.hass.data:
                    coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
                    if coordinator:
                        _LOGGER.info(
                            "Updating coordinator connection for entry %s",
                            self.config_entry.entry_id
                        )
                        await coordinator.async_update_connection(self._connection_data)
            
            # Update options if changed
            if self._configure_options and self._options_data:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=self._options_data
                )
                
                # Update coordinator with new options
                if DOMAIN in self.hass.data:
                    coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
                    if coordinator:
                        _LOGGER.info(
                            "Updating coordinator options for entry %s: %s",
                            self.config_entry.entry_id, self._options_data
                        )
                        await coordinator.async_update_config(self._options_data)
            
            _LOGGER.info(
                "Configuration updated successfully for entry %s",
                self.config_entry.entry_id
            )
            return self.async_create_entry(title="", data={})
            
        except Exception as ex:
            _LOGGER.error(
                "Error saving configuration: %s",
                ex, exc_info=True
            )
            
            # Determine which step to return to based on what was being configured
            if self._configure_connection and self._configure_options:
                # If both were being configured, return to connection step
                return await self.async_step_connection()
            elif self._configure_connection:
                # If only connection was being configured, return to connection step
                return await self.async_step_connection()
            elif self._configure_options:
                # If only options were being configured, return to options step
                return await self.async_step_options()
            else:
                # Fallback to menu if no configuration flags are set
                return self.async_show_menu(
                    step_id="init",
                    menu_options=["connection", "options", "all"],
                    errors={"base": "save_failed"},
                )