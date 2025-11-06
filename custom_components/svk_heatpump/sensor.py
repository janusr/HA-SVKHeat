"""Sensor platform for SVK Heatpump integration."""

import logging
from typing import Any, Dict, List, Optional, Union

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CatalogEntity, get_unique_id
from .coordinator import SVKDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class SVKSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SVK Heatpump sensor."""

    def __init__(
        self,
        coordinator: SVKDataUpdateCoordinator,
        entry_id: str,
        entity: CatalogEntity,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entity = entity
        self._attr_unique_id = get_unique_id(coordinator.host, entity.id)
        
        # Set entity registry enabled default based on catalog enabled status
        self._attr_entity_registry_enabled_default = entity.enabled
        
        # Set up entity name with translation key if available
        if entity.translation_key:
            self._attr_has_entity_name = True
            self._attr_translation_key = entity.translation_key
        else:
            self._attr_name = entity.key.replace("_", " ").title()
        
        # Set up device class
        if entity.device_class:
            self._attr_device_class = entity.device_class
        
        # Set up unit of measurement
        if entity.unit_of_measurement:
            self._attr_native_unit_of_measurement = entity.unit_of_measurement
        
        # Set up state class
        if entity.state_class:
            self._attr_state_class = entity.state_class
        
        # Set up icon
        if entity.icon:
            self._attr_icon = entity.icon
        
        # Set up suggested display precision
        if entity.precision > 0:
            self._attr_suggested_display_precision = entity.precision
        
        # Set up entity category based on device class or key
        self._attr_entity_category = self._get_entity_category()
        
        # Set up extra attributes for writable entities
        self._attr_extra_state_attributes = {}
        if entity.write_access:
            self._attr_extra_state_attributes["write_access"] = True

    def _get_entity_category(self) -> Optional[EntityCategory]:
        """Determine the entity category based on the sensor type."""
        key = self._entity.key
        
        # Temperature sensors
        if "temperature" in key:
            return EntityCategory.DIAGNOSTIC if "error" in key else EntityCategory.MEASUREMENT
        
        # Energy and power sensors
        if "energy" in key or "power" in key or "cop" in key:
            return EntityCategory.DIAGNOSTIC if "consumption" in key else EntityCategory.MEASUREMENT
        
        # Control and settings - sensors should not use CONFIG category
        # Use DIAGNOSTIC for setpoints and modes to avoid config category error
        if "setpoint" in key or "mode" in key or "curve" in key:
            return EntityCategory.DIAGNOSTIC
        
        # Runtime and maintenance
        if "runtime" in key or "error" in key or "warning" in key:
            return EntityCategory.DIAGNOSTIC
        
        # Default to None for other sensors
        return None

    @property
    def native_value(self) -> Optional[Union[str, int, float]]:
        """Return the state of the sensor."""
        try:
            # Get the value from the coordinator
            value = self.coordinator.get_entity_value(self._entity.id)
            return value
        except Exception as ex:
            _LOGGER.error(
                "Error getting value for entity %s: %s",
                self._entity.id, ex
            )
            return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        try:
            # Check if coordinator is available and has data for this entity
            if not self.coordinator:
                _LOGGER.warning(
                    "Coordinator not available for entity %s",
                    self._entity.id
                )
                return False
            
            # Check if reauth is in progress
            if self.coordinator.is_reauth_in_progress():
                _LOGGER.debug(
                    "Reauth in progress for entity %s, marking as unavailable",
                    self._entity.id
                )
                return False
            
            # Check connection state
            connection_state = self.coordinator.get_connection_state()
            if connection_state == "error":
                _LOGGER.debug(
                    "Coordinator in error state for entity %s",
                    self._entity.id
                )
                return False
            
            # Note: We don't check catalog enabled status here because
            # users should be able to enable catalog-disabled entities through the UI
            # The data fetching logic will handle whether to actually fetch data for this entity
            
            # Check if entity is enabled by the user in the entity registry
            try:
                registry = er.async_get(self.hass)
                # Try to find the entity by unique_id first, then by entity_id
                entity_entry = registry.async_get_entity_id(
                    "sensor", DOMAIN, self._attr_unique_id
                )
                
                if entity_entry:
                    # Get the full entity entry to check if it's disabled
                    full_entity_entry = registry.async_get(entity_entry)
                    if full_entity_entry and full_entity_entry.disabled:
                        _LOGGER.debug(
                            "Entity %s is disabled by the user",
                            self._entity.id
                        )
                        return False
            except Exception as ex:
                _LOGGER.debug(
                    "Error checking entity registry for %s: %s",
                    self._entity.id, ex
                )
                # If we can't check the registry, assume it's enabled
                pass
            
            # Check if entity value is available
            value = self.coordinator.get_entity_value(self._entity.id)
            is_available = value is not None
            
            if not is_available:
                _LOGGER.debug(
                    "Entity %s not available (value=None)",
                    self._entity.id
                )
            
            return is_available
        except Exception as ex:
            _LOGGER.error(
                "Error checking availability for entity %s: %s",
                self._entity.id, ex
            )
            return False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="SVK Heatpump",
            manufacturer="SVK",
            model="Heat Pump",
        )

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}
        
        try:
            # Add connection state information
            if self.coordinator:
                attrs["connection_state"] = self.coordinator.get_connection_state()
                attrs["consecutive_failures"] = self.coordinator.get_consecutive_failures()
                attrs["reauth_in_progress"] = self.coordinator.is_reauth_in_progress()
            
            # Add raw value if different from transformed value
            raw_value = self.coordinator.get_entity_raw_value(self._entity.id)
            if raw_value is not None and raw_value != self.native_value:
                attrs["raw_value"] = raw_value
            
            # Add last updated timestamp
            last_updated = self.coordinator.get_entity_last_updated(self._entity.id)
            if last_updated is not None:
                attrs["last_updated"] = last_updated
            
            # Add entity ID for reference
            attrs["entity_id"] = self._entity.id
            attrs["entity_key"] = self._entity.key
            
            # Add write access status
            attrs["write_access"] = self._entity.write_access
            
            return attrs
        except Exception as ex:
            _LOGGER.error(
                "Error getting extra attributes for entity %s: %s",
                self._entity.id, ex
            )
            # Return basic attributes even if there's an error
            return {
                "entity_id": self._entity.id,
                "entity_key": self._entity.key,
                "write_access": self._entity.write_access,
                "error": str(ex)
            }
    
    async def async_entity_registry_updated(self) -> None:
        """Handle entity registry updates (enable/disable events)."""
        try:
            # Get the current entity registry entry
            registry = er.async_get(self.hass)
            entity_entry = registry.async_get(self.entity_id)
            
            # Check if the entity was just enabled or disabled
            was_disabled = hasattr(self, '_was_disabled') and self._was_disabled
            is_disabled = entity_entry and entity_entry.disabled
            
            if was_disabled != is_disabled:
                _LOGGER.info(
                    "Entity %s registry status changed: disabled=%s->%s",
                    self.entity_id, was_disabled, is_disabled
                )
                
                # Update our tracking
                self._was_disabled = is_disabled
                
                # Trigger a refresh of the coordinator to adjust fetching
                if hasattr(self.coordinator, 'async_refresh_entity_registry_status'):
                    await self.coordinator.async_refresh_entity_registry_status()
            
        except Exception as ex:
            _LOGGER.error(
                "Error handling entity registry update for %s: %s",
                self.entity_id, ex
            )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SVK Heatpump sensors based on a config entry."""
    try:
        # Get the coordinator from the config entry
        coordinator: SVKDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        
        if not coordinator:
            _LOGGER.error(
                "Coordinator not found for entry %s",
                entry.entry_id
            )
            return
        
        # Get all entities from the catalog (not just enabled ones)
        all_entities = coordinator.catalog.get_all_entities()
        
        if not all_entities:
            _LOGGER.warning(
                "No entities found in catalog for entry %s",
                entry.entry_id
            )
            return
        
        # Create sensor entities for ALL entities with platform "sensor" regardless of enabled status
        sensors: List[SVKSensor] = []
        for entity in all_entities:
            try:
                # Create sensors for ALL entities with platform "sensor"
                if entity.platform == "sensor":
                    sensor = SVKSensor(coordinator, entry.entry_id, entity)
                    
                    # Initialize the disabled status tracking
                    registry = er.async_get(hass)
                    entity_entry = registry.async_get(sensor.entity_id)
                    sensor._was_disabled = entity_entry and entity_entry.disabled
                    
                    sensors.append(sensor)
                    _LOGGER.debug(
                        "Created sensor for entity %s (%s) - catalog_enabled: %s, user_disabled: %s",
                        entity.key, entity.id, entity.enabled, sensor._was_disabled
                    )
            except Exception as ex:
                _LOGGER.error(
                    "Error creating sensor for entity %s: %s",
                    entity.id, ex
                )
        
        # Add all sensors to Home Assistant
        if sensors:
            enabled_count = sum(1 for s in sensors if s._attr_entity_registry_enabled_default)
            disabled_count = len(sensors) - enabled_count
            _LOGGER.info(
                "Adding %d sensors for entry %s (%d enabled by default, %d disabled by default)",
                len(sensors), entry.entry_id, enabled_count, disabled_count
            )
            async_add_entities(sensors, True)
        else:
            _LOGGER.warning(
                "No sensors to add for entry %s",
                entry.entry_id
            )
    except Exception as ex:
        _LOGGER.error(
            "Error setting up sensors for entry %s: %s",
            entry.entry_id, ex, exc_info=True
        )