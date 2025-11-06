"""DataUpdateCoordinator for SVK Heatpump integration."""

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SVKAuthenticationError,
    SVKConnectionError,
    SVKHeatpumpAPI,
    SVKTimeoutError,
    SVKWriteAccessError,
    SVKInvalidResponseError,
)
from .const import (
    CONF_FETCH_INTERVAL,
    CONF_WRITE_ACCESS,
    DEFAULT_FETCH_INTERVAL,
    DEFAULT_WRITE_ACCESS,
    DOMAIN,
    async_load_catalog,
    get_unique_id,
    load_catalog,
    transform_value,
)
from .const import Catalog, CatalogEntity

_LOGGER = logging.getLogger(__name__)

# Maximum number of consecutive failures before entering extended backoff
MAX_CONSECUTIVE_FAILURES = 5
# Extended backoff time in seconds after max failures
EXTENDED_BACKOFF = 300  # 5 minutes
# Maximum retry interval
MAX_RETRY_INTERVAL = 60  # 1 minute


class SVKDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the SVK Heatpump."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the SVK Heatpump coordinator.

        Args:
            hass: The Home Assistant instance.
            config_entry: The config entry for this integration.
        """
        self.config_entry = config_entry
        self.host = config_entry.data[CONF_HOST]
        self.username = config_entry.data[CONF_USERNAME]
        self.password = config_entry.data[CONF_PASSWORD]
        
        # Get options with defaults from config_entry.options first, then fallback to data for migration
        self.write_access = config_entry.options.get(
            CONF_WRITE_ACCESS,
            config_entry.data.get(CONF_WRITE_ACCESS, DEFAULT_WRITE_ACCESS)
        )
        self.fetch_interval = config_entry.options.get(
            CONF_FETCH_INTERVAL,
            config_entry.data.get(CONF_FETCH_INTERVAL, DEFAULT_FETCH_INTERVAL)
        )

        # Initialize API client
        self.api = SVKHeatpumpAPI(
            host=self.host,
            username=self.username,
            password=self.password,
        )

        # Catalog will be loaded asynchronously in async_setup
        self.catalog = None
        self.enabled_entities = []
        
        # Track last successful update time
        self.last_update_success = None
        
        # Track connection state and error handling
        self._consecutive_failures = 0
        self._last_failure_time = None
        self._extended_backoff_until = None
        self._reauth_in_progress = False
        self._connection_state = "disconnected"  # disconnected, connecting, connected, error

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=self.fetch_interval),
        )

    async def async_load_catalog(self) -> None:
        """Load the catalog asynchronously."""
        try:
            self.catalog = await load_catalog(self.hass)
            self.enabled_entities = self.catalog.get_enabled_entities()
        except Exception as ex:
            _LOGGER.error("Failed to load catalog: %s", ex)
            self.catalog = None
            self.enabled_entities = []

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library.

        Returns:
            Dictionary mapping entity unique IDs to their data.

        Raises:
            UpdateFailed: If an error occurs while updating.
        """
        # Check if we're in extended backoff period
        if self._extended_backoff_until and time.time() < self._extended_backoff_until:
            _LOGGER.debug("In extended backoff period, skipping update")
            raise UpdateFailed("In extended backoff period after multiple failures")
        
        # Check if reauth is in progress
        if self._reauth_in_progress:
            _LOGGER.debug("Reauthentication in progress, skipping update")
            raise UpdateFailed("Reauthentication in progress")
        
        # Set connection state to connecting
        self._connection_state = "connecting"
        
        try:
            # Check if catalog is available
            if not self.catalog:
                _LOGGER.warning("Catalog not available")
                # Try to reload catalog
                try:
                    self.catalog = await async_load_catalog()
                    self.enabled_entities = self.catalog.get_enabled_entities()
                except Exception as ex:
                    _LOGGER.error("Failed to reload catalog: %s", ex)
                    raise UpdateFailed(f"Catalog unavailable: {ex}")
            
            # Get ALL entities from catalog (both enabled and disabled)
            all_entities = self.catalog.get_all_entities()
            
            # Filter entities based on user-enabled status in entity registry
            registry = er.async_get(self.hass)
            enabled_entities = []
            
            for entity in all_entities:
                # Construct the expected entity ID using the same format as in sensor.py
                # Use get_unique_id to ensure consistency
                unique_id = get_unique_id(self.host, entity.id)
                # Find the entity ID from the unique ID in the registry
                entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
                
                # Check if entity exists in registry and is enabled by user
                try:
                    entity_entry = registry.async_get(entity_id) if entity_id else None
                    
                    # Determine if entity should be fetched
                    should_fetch = False
                    
                    if entity_entry is None:
                        # Entity not in registry yet (first setup)
                        # Only fetch if catalog-enabled
                        should_fetch = entity.enabled
                        _LOGGER.debug(
                            "Entity %s not in registry, catalog_enabled=%s, will_fetch=%s",
                            entity_id, entity.enabled, should_fetch
                        )
                    else:
                        # Entity exists in registry
                        if entity_entry.disabled:
                            # User has disabled the entity
                            should_fetch = False
                            _LOGGER.debug(
                                "Entity %s is disabled by user, skipping fetch",
                                entity_id
                            )
                        else:
                            # User has enabled the entity (entity_entry.disabled is False)
                            # Fetch if either:
                            # 1. Entity is catalog-enabled (default behavior)
                            # 2. Entity is catalog-disabled but user has explicitly enabled it
                            should_fetch = entity.enabled or entity_entry.disabled_by is None
                            _LOGGER.debug(
                                "Entity %s is enabled by user, catalog_enabled=%s, disabled_by=%s, will_fetch=%s",
                                entity_id, entity.enabled, entity_entry.disabled_by, should_fetch
                            )
                    
                    if should_fetch:
                        enabled_entities.append(entity)
                        
                except Exception as ex:
                    _LOGGER.warning("Error checking entity registry status for %s: %s", entity_id, ex)
                    # Include entity if we can't determine status (fail-safe)
                    # But only if it's catalog-enabled
                    if entity.enabled:
                        enabled_entities.append(entity)
            
            entity_ids = [entity.id for entity in enabled_entities]
            
            if not entity_ids:
                _LOGGER.warning("No enabled entities found (catalog + user enabled)")
                self._connection_state = "error"
                return {}
            
            # Fetch data from API
            raw_data = await self.api.async_read_values(entity_ids)
            
            # Transform and store data
            data_dict = {}
            for entity in enabled_entities:
                entity_id = entity.id
                if entity_id in raw_data:
                    raw_value = raw_data[entity_id]
                    # Apply value transformation based on catalog definition
                    transformed_value = transform_value(entity, raw_value)
                    
                    # Store with unique ID for Home Assistant
                    unique_id = get_unique_id(self.host, entity_id)
                    data_dict[unique_id] = {
                        "value": transformed_value,
                        "raw_value": raw_value,
                        "entity": entity,
                        "last_updated": self.hass.loop.time(),
                    }
                else:
                    _LOGGER.debug("Entity %s not found in API response", entity_id)
            
            # Reset failure counters on success
            self._consecutive_failures = 0
            self._last_failure_time = None
            self._extended_backoff_until = None
            self._connection_state = "connected"
            self.last_update_success = self.hass.loop.time()
            
            _LOGGER.debug("Successfully updated %d entities", len(data_dict))
            return data_dict
            
        except SVKAuthenticationError as ex:
            _LOGGER.error("Authentication error: %s", ex)
            self._connection_state = "error"
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            
            # Trigger reauth flow if not already in progress
            if not self._reauth_in_progress:
                self._reauth_in_progress = True
                self.hass.async_create_task(
                    self.config_entry.async_start_reauth(self.hass)
                )
            
            raise UpdateFailed(f"Authentication failed: {ex}")
            
        except (SVKConnectionError, SVKTimeoutError, SVKInvalidResponseError) as ex:
            _LOGGER.error("Connection error: %s", ex)
            self._connection_state = "error"
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            
            # Check if we need to enter extended backoff
            if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                self._extended_backoff_until = time.time() + EXTENDED_BACKOFF
                _LOGGER.warning(
                    "Too many consecutive failures (%d), entering extended backoff for %d seconds",
                    self._consecutive_failures,
                    EXTENDED_BACKOFF
                )
            
            # Implement exponential backoff for update interval
            if self._consecutive_failures > 0:
                backoff_interval = min(2 ** (self._consecutive_failures - 1), MAX_RETRY_INTERVAL)
                _LOGGER.debug("Setting update interval to %d seconds due to failures", backoff_interval)
                self.update_interval = timedelta(seconds=backoff_interval)
            
            raise UpdateFailed(f"Connection error: {ex}")
            
        except Exception as ex:
            _LOGGER.error("Unexpected error updating data: %s", ex)
            self._connection_state = "error"
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            raise UpdateFailed(f"Error communicating with SVK Heatpump: {ex}")

    async def async_write_value(
        self, entity_id: str, value: Any
    ) -> bool:
        """Write a value to the heat pump.

        Args:
            entity_id: The entity ID to write to.
            value: The value to write.

        Returns:
            True if successful, False otherwise.

        Raises:
            HomeAssistantError: If write access is disabled or entity not found.
            SVKWriteAccessError: If write access is denied.
            SVKConnectionError: If connection fails.
            SVKAuthenticationError: If authentication fails.
        """
        # Check if write access is enabled
        if not self.write_access:
            raise HomeAssistantError(
                "Write access is disabled in configuration. "
                "Enable write access in the integration options to use this feature."
            )
        
        # Check if catalog is available
        if not self.catalog:
            raise HomeAssistantError("Catalog is not available")
        
        # Find the entity in the catalog
        entity = self.catalog.get_entity_by_id(entity_id)
        if not entity:
            raise HomeAssistantError(f"Entity with ID {entity_id} not found in catalog")
        
        # Check if entity supports write operations
        if not entity.write_access:
            raise HomeAssistantError(
                f"Entity {entity.key} (ID: {entity_id}) does not support write operations"
            )
        
        # Check if reauth is in progress
        if self._reauth_in_progress:
            raise HomeAssistantError(
                "Cannot write value while reauthentication is in progress"
            )
        
        try:
            # Write value to the heat pump
            success = await self.api.async_write_value(
                itemno=entity_id,
                value=value,
                write_access_enabled=self.write_access,
            )
            
            if success:
                # Get current data from parent class
                current_data = self.data if self.data is not None else {}
                
                # Update local state if write was successful
                unique_id = get_unique_id(self.host, entity_id)
                if unique_id in current_data:
                    # Apply transformation to the new value
                    transformed_value = transform_value(entity, value)
                    current_data[unique_id]["value"] = transformed_value
                    current_data[unique_id]["raw_value"] = value
                    current_data[unique_id]["last_updated"] = self.hass.loop.time()
                
                # Notify listeners of data change
                self.async_set_updated_data(current_data)
                
                # Reset failure counters on successful write
                self._consecutive_failures = 0
                self._last_failure_time = None
                self._extended_backoff_until = None
                
                _LOGGER.info(
                    "Successfully wrote value %s to entity %s (%s)",
                    value,
                    entity.key,
                    entity_id,
                )
                return True
            else:
                _LOGGER.error(
                    "Failed to write value %s to entity %s (%s)",
                    value,
                    entity.key,
                    entity_id,
                )
                return False
                
        except SVKAuthenticationError as ex:
            _LOGGER.error("Authentication error during write: %s", ex)
            self._connection_state = "error"
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            
            # Trigger reauth flow if not already in progress
            if not self._reauth_in_progress:
                self._reauth_in_progress = True
                self.hass.async_create_task(
                    self.config_entry.async_start_reauth(self.hass)
                )
            raise
            
        except SVKWriteAccessError as ex:
            _LOGGER.error("Write access error: %s", ex)
            self._connection_state = "error"
            raise
            
        except (SVKConnectionError, SVKTimeoutError, SVKInvalidResponseError) as ex:
            _LOGGER.error("Connection error during write: %s", ex)
            self._connection_state = "error"
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            
            # Check if we need to enter extended backoff
            if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                self._extended_backoff_until = time.time() + EXTENDED_BACKOFF
                _LOGGER.warning(
                    "Too many consecutive failures (%d), entering extended backoff for %d seconds",
                    self._consecutive_failures,
                    EXTENDED_BACKOFF
                )
            raise
            
        except Exception as ex:
            _LOGGER.error("Unexpected error during write: %s", ex)
            self._connection_state = "error"
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            raise HomeAssistantError(f"Failed to write value: {ex}")

    async def async_test_connection(self) -> bool:
        """Test connection to the heat pump.

        Returns:
            True if connection is successful, False otherwise.

        Raises:
            ConfigEntryNotReady: If connection fails during setup.
        """
        self._connection_state = "connecting"
        
        try:
            result = await self.api.async_test_connection()
            if result:
                self._connection_state = "connected"
                _LOGGER.info("Connection test successful")
            else:
                self._connection_state = "error"
                _LOGGER.warning("Connection test returned False")
            return result
        except SVKAuthenticationError as ex:
            _LOGGER.error("Authentication failed during connection test: %s", ex)
            self._connection_state = "error"
            # Don't raise ConfigEntryNotReady for auth errors - let reauth flow handle it
            return False
        except (SVKConnectionError, SVKTimeoutError, SVKInvalidResponseError) as ex:
            _LOGGER.error("Connection test failed: %s", ex)
            self._connection_state = "error"
            raise ConfigEntryNotReady(f"Connection to SVK Heatpump failed: {ex}")
        except Exception as ex:
            _LOGGER.error("Unexpected error during connection test: %s", ex)
            self._connection_state = "error"
            raise ConfigEntryNotReady(f"Connection to SVK Heatpump failed: {ex}")

    def get_entity_value(self, entity_id: str) -> Optional[Any]:
        """Get the current value of an entity.

        Args:
            entity_id: The entity ID.

        Returns:
            The current value, or None if not available.
        """
        unique_id = get_unique_id(self.host, entity_id)
        if self.data is not None and unique_id in self.data:
            return self.data[unique_id]["value"]
        return None

    def get_entity_raw_value(self, entity_id: str) -> Optional[Any]:
        """Get the raw (untransformed) value of an entity.

        Args:
            entity_id: The entity ID.

        Returns:
            The raw value, or None if not available.
        """
        unique_id = get_unique_id(self.host, entity_id)
        if self.data is not None and unique_id in self.data:
            return self.data[unique_id]["raw_value"]
        return None

    def get_entity_last_updated(self, entity_id: str) -> Optional[float]:
        """Get the last update time for an entity.

        Args:
            entity_id: The entity ID.

        Returns:
            The last update time as a timestamp, or None if not available.
        """
        unique_id = get_unique_id(self.host, entity_id)
        if self.data is not None and unique_id in self.data:
            return self.data[unique_id]["last_updated"]
        return None

    def get_entity_by_id(self, entity_id: str) -> Optional[CatalogEntity]:
        """Get an entity from the catalog by ID.

        Args:
            entity_id: The entity ID.

        Returns:
            The catalog entity, or None if not found.
        """
        return self.catalog.get_entity_by_id(entity_id)

    def get_entity_by_key(self, key: str) -> Optional[CatalogEntity]:
        """Get an entity from the catalog by key.

        Args:
            key: The entity key.

        Returns:
            The catalog entity, or None if not found.
        """
        return self.catalog.get_entity_by_key(key)

    def get_writable_entities(self) -> List[CatalogEntity]:
        """Get all entities that support write operations.

        Returns:
            List of writable catalog entities.
        """
        return self.catalog.get_writable_entities()

    async def async_update_config(self, options: Dict[str, Any]) -> None:
        """Update configuration options.

        Args:
            options: The new configuration options.
        """
        try:
            # Update configuration
            old_write_access = self.write_access
            old_fetch_interval = self.fetch_interval
            
            self.write_access = options.get(CONF_WRITE_ACCESS, self.write_access)
            new_fetch_interval = options.get(CONF_FETCH_INTERVAL, self.fetch_interval)
            
            # Update fetch interval if changed
            if new_fetch_interval != self.fetch_interval:
                self.fetch_interval = new_fetch_interval
                self.update_interval = timedelta(seconds=self.fetch_interval)
                _LOGGER.info("Updated fetch interval to %d seconds", self.fetch_interval)
            
            # Reset failure counters when configuration is updated
            self._consecutive_failures = 0
            self._last_failure_time = None
            self._extended_backoff_until = None
            
            # Log changes
            if old_write_access != self.write_access or old_fetch_interval != self.fetch_interval:
                _LOGGER.info(
                    "Updated configuration: write_access=%s->%s, fetch_interval=%d->%d",
                    old_write_access, self.write_access,
                    old_fetch_interval, self.fetch_interval,
                )
            
            # Note: Config entry options are updated by the options flow
            # This avoids circular import issues
            
        except Exception as ex:
            _LOGGER.error("Error updating configuration: %s", ex)
            raise HomeAssistantError(f"Failed to update configuration: {ex}")

    async def async_update_connection(self, connection_data: Dict[str, Any]) -> None:
        """Update connection parameters.

        Args:
            connection_data: The new connection parameters.
        """
        try:
            # Store old values for logging
            old_host = self.host
            old_username = self.username
            
            # Update connection parameters
            self.host = connection_data.get(CONF_HOST, self.host)
            self.username = connection_data.get(CONF_USERNAME, self.username)
            self.password = connection_data.get(CONF_PASSWORD, self.password)
            
            # Reinitialize API client with new connection parameters
            self.api = SVKHeatpumpAPI(
                host=self.host,
                username=self.username,
                password=self.password,
            )
            
            # Reset failure counters when connection is updated
            self._consecutive_failures = 0
            self._last_failure_time = None
            self._extended_backoff_until = None
            self._connection_state = "disconnected"
            
            # Log changes
            if old_host != self.host or old_username != self.username:
                _LOGGER.info(
                    "Updated connection parameters: host=%s->%s, username=%s->%s",
                    old_host, self.host,
                    old_username, self.username,
                )
            
            # Test the new connection
            try:
                await self.async_test_connection()
                _LOGGER.info("New connection test successful")
            except Exception as ex:
                _LOGGER.warning("New connection test failed: %s", ex)
                # Don't raise here - let the next update cycle handle it
            
        except Exception as ex:
            _LOGGER.error("Error updating connection parameters: %s", ex)
            raise HomeAssistantError(f"Failed to update connection parameters: {ex}")

    async def async_shutdown(self) -> None:
        """Clean up resources when shutting down."""
        try:
            _LOGGER.info("Shutting down SVK Heatpump coordinator")
            # Close the API client to clean up resources
            await self.api.async_close()
            await super().async_shutdown()
        except Exception as ex:
            _LOGGER.error("Error during shutdown: %s", ex)
    
    def get_connection_state(self) -> str:
        """Get the current connection state.
        
        Returns:
            The current connection state (disconnected, connecting, connected, error).
        """
        return self._connection_state
    
    def get_consecutive_failures(self) -> int:
        """Get the number of consecutive failures.
        
        Returns:
            The number of consecutive failures.
        """
        return self._consecutive_failures
    
    def is_reauth_in_progress(self) -> bool:
        """Check if reauthentication is in progress.
        
        Returns:
            True if reauthentication is in progress.
        """
        return self._reauth_in_progress
    
    def set_reauth_complete(self) -> None:
        """Mark reauthentication as complete."""
        self._reauth_in_progress = False
        _LOGGER.info("Reauthentication marked as complete")
    
    async def async_refresh_entity_registry_status(self) -> None:
        """Force refresh of data to account for entity registry changes.
        
        This method should be called when entities are enabled/disabled by the user
        to ensure the coordinator starts/stops fetching data for those entities.
        """
        _LOGGER.debug("Refreshing coordinator data due to entity registry changes")
        try:
            # Reset failure counters to ensure immediate update
            self._consecutive_failures = 0
            self._last_failure_time = None
            self._extended_backoff_until = None
            
            # Force an immediate update
            await self.async_request_refresh()
            _LOGGER.debug("Entity registry status refresh initiated")
        except Exception as ex:
            _LOGGER.error("Error refreshing entity registry status: %s", ex)