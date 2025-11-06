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
        
        # Control and settings
        if "setpoint" in key or "mode" in key or "curve" in key:
            return EntityCategory.CONFIG
        
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
        
        # Get enabled entities from the catalog
        enabled_entities = coordinator.enabled_entities
        
        if not enabled_entities:
            _LOGGER.warning(
                "No enabled entities found for entry %s",
                entry.entry_id
            )
            return
        
        # Create sensor entities for each enabled entity
        sensors: List[SVKSensor] = []
        for entity in enabled_entities:
            try:
                # Only create sensors for entities with platform "sensor"
                if entity.platform == "sensor":
                    sensor = SVKSensor(coordinator, entry.entry_id, entity)
                    sensors.append(sensor)
                    _LOGGER.debug(
                        "Created sensor for entity %s (%s)",
                        entity.key, entity.id
                    )
            except Exception as ex:
                _LOGGER.error(
                    "Error creating sensor for entity %s: %s",
                    entity.id, ex
                )
        
        # Add all sensors to Home Assistant
        if sensors:
            _LOGGER.info(
                "Adding %d sensors for entry %s",
                len(sensors), entry.entry_id
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