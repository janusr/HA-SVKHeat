"""Binary sensor platform for SVK Heatpump integration."""

import logging
from typing import Any, Dict

try:
    from homeassistant.components.binary_sensor import (
        BinarySensorDeviceClass,
        BinarySensorEntity,
        BinarySensorEntityDescription,
    )
except ImportError:
    # Fallback for older Home Assistant versions
    from homeassistant.components.binary_sensor import (
        BinarySensorDeviceClass,
        BinarySensorEntity,
    )
    # For older versions, create a fallback EntityDescription
    from dataclasses import dataclass
    
    @dataclass
    class BinarySensorEntityDescription:
        """Fallback BinarySensorEntityDescription for older HA versions."""
        key: str
        name: str | None = None
        device_class: str | None = None
        entity_category: str | None = None
        icon: str | None = None
        enabled_default: bool = True

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# Import specific items from modules
from .const import DOMAIN, BINARY_SENSORS
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_constants():
    """Lazy import of constants to prevent blocking during async setup."""
    from .const import DEFAULT_ENABLED_ENTITIES, ID_MAP

    return ID_MAP, DEFAULT_ENABLED_ENTITIES


class SVKHeatpumpBaseEntity(CoordinatorEntity):
    """Base entity for SVK Heatpump integration."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        config_entry_id: str,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id

    @property
    def device_info(self):
        """Return device information from coordinator."""
        return self.coordinator.device_info


class SVKHeatpumpBinarySensor(SVKHeatpumpBaseEntity, BinarySensorEntity):
    """Representation of a SVK Heatpump binary sensor."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        entity_id: int,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, config_entry_id)
        self._entity_key = entity_key
        self._entity_id = entity_id
        self._attr_entity_registry_enabled_default = enabled_by_default

        _LOGGER.debug(
            "Creating binary sensor entity: %s (ID: %s, enabled_by_default: %s)",
            entity_key,
            entity_id,
            enabled_by_default,
        )

        # Get entity info from ID_MAP (5-element structure)
        ID_MAP, _ = _get_constants()
        entity_info = ID_MAP.get(entity_id, ("", "", None, None, ""))
        (
            self._entity_key,
            self._unit,
            self._device_class,
            self._state_class,
            self._original_name,
        ) = entity_info

        # Create entity description
        device_class = None
        entity_category = None

        if self._entity_key == "alarm_active":
            device_class = BinarySensorDeviceClass.PROBLEM
        elif entity_id in [222, 223, 224, 225]:  # Digital outputs
            device_class = BinarySensorDeviceClass.RUNNING

        # Set entity category based on entity definition

        if self._entity_key in BINARY_SENSORS and BINARY_SENSORS[self._entity_key].get(
            "entity_category"
        ):
            entity_category = getattr(
                EntityCategory,
                BINARY_SENSORS[self._entity_key]["entity_category"].upper(),
            )

        # Use original_name for friendly display name if available
        friendly_name = (
            self._original_name.replace("_", " ").title()
            if self._original_name
            else self._entity_key.replace("_", " ").title()
        )

        self.entity_description = BinarySensorEntityDescription(
            key=self._entity_key,
            name=friendly_name,
            device_class=device_class,
            entity_category=entity_category,
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for binary sensor."""
        return f"{self._config_entry_id}_{self._entity_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        value = self.coordinator.get_entity_value(self._entity_key)
        if value is not None:
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() in ["yes", "true", "on", "active", "1"]
            elif isinstance(value, (int, float)):
                # For digital outputs (IDs 222-225), is_on = (value == 1)
                if self._entity_id in [222, 223, 224, 225]:
                    return value == 1
                return value != 0
        return False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        is_available = (
            self.coordinator.last_update_success
            and self.coordinator.is_entity_available(self._entity_key)
        )
        _LOGGER.debug(
            "Binary sensor %s availability: %s (last_update_success: %s)",
            self._entity_key,
            is_available,
            self.coordinator.last_update_success,
        )
        return is_available


class SVKHeatpumpAlarmBinarySensor(SVKHeatpumpBinarySensor):
    """Binary sensor for alarm status with additional attributes."""

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes for alarm status."""
        attributes = {}

        if self.coordinator.data:
            alarm_summary = self.coordinator.get_alarm_summary()
            attributes.update(alarm_summary)

            # Add individual alarm details if available
            alarm_list = self.coordinator.data.get("alarm_list", [])
            if alarm_list:
                attributes["alarms"] = alarm_list

        return attributes


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up SVK Heatpump binary sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    _LOGGER.info(
        "Setting up SVK Heatpump binary sensors for entry %s", config_entry.entry_id
    )
    _LOGGER.info("Coordinator is_json_client: %s", coordinator.is_json_client)

    binary_sensors = []

    # Create binary sensors based on ID_MAP for JSON API
    if coordinator.is_json_client:
        # Get constants using lazy import
        ID_MAP, DEFAULT_ENABLED_ENTITIES = _get_constants()

        # Create all possible entities from ID_MAP
        for entity_id, (
            entity_key,
            _unit,
            _device_class,
            _state_class,
            _original_name,
        ) in ID_MAP.items():
            # Include alarm_active entity
            if entity_key == "alarm_active":
                # Check if this entity should be enabled by default
                enabled_by_default = entity_id in DEFAULT_ENABLED_ENTITIES

                # Use the alarm binary sensor class for additional attributes
                binary_sensor = SVKHeatpumpAlarmBinarySensor(
                    coordinator,
                    entity_key,
                    entity_id,
                    config_entry.entry_id,
                    enabled_by_default=enabled_by_default,
                )

                binary_sensors.append(binary_sensor)

            # Include digital outputs (IDs 222-225)
            elif entity_id in [222, 223, 224, 225]:
                # Check if this entity should be enabled by default
                enabled_by_default = entity_id in DEFAULT_ENABLED_ENTITIES

                binary_sensor = SVKHeatpumpBinarySensor(
                    coordinator,
                    entity_key,
                    entity_id,
                    config_entry.entry_id,
                    enabled_by_default=enabled_by_default,
                )

                binary_sensors.append(binary_sensor)
                _LOGGER.debug(
                    "Added binary sensor entity: %s (ID: %s, enabled_by_default: %s)",
                    entity_key,
                    entity_id,
                    enabled_by_default,
                )
    else:
        # Fall back to HTML scraping entities for backward compatibility
        # This would need to be implemented based on the old structure
        pass

    # Add additional binary sensors for system states
    system_state_desc = BinarySensorEntityDescription(
        key="system_active",
        name="System Active",
        device_class=BinarySensorDeviceClass.RUNNING,
    )

    class SystemActiveBinarySensor(SVKHeatpumpBaseEntity, BinarySensorEntity):
        """Binary sensor for system active state."""

        _attr_entity_registry_enabled_default = True

        def __init__(self, coordinator, config_entry_id):
            super().__init__(coordinator, config_entry_id)
            self.entity_description = system_state_desc

        @property
        def unique_id(self) -> str:
            """Return unique ID for binary sensor."""
            return f"{self._config_entry_id}_system_active"

        @property
        def is_on(self) -> bool:
            """Return true if the system is active."""
            if self.coordinator.data:
                heatpump_state = self.coordinator.data.get("heatpump_state", "")
                return heatpump_state in [
                    "heating",
                    "hot_water",
                    "el_heating",
                    "defrost",
                    "start_up",
                    "forced_running",
                ]
            return False

    # System active sensor is enabled by default
    system_sensor = SystemActiveBinarySensor(coordinator, config_entry.entry_id)
    binary_sensors.append(system_sensor)

    # Add online status binary sensor
    online_desc = BinarySensorEntityDescription(
        key="online_status",
        name="Online Status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    )

    class OnlineStatusBinarySensor(SVKHeatpumpBaseEntity, BinarySensorEntity):
        """Binary sensor for online status."""

        _attr_entity_registry_enabled_default = True

        def __init__(self, coordinator, config_entry_id):
            super().__init__(coordinator, config_entry_id)
            self.entity_description = online_desc

        @property
        def unique_id(self) -> str:
            """Return unique ID for binary sensor."""
            return f"{self._config_entry_id}_online_status"

        @property
        def is_on(self) -> bool:
            """Return true if the device is online."""
            return self.coordinator.last_update_success

        @property
        def available(self) -> bool:
            """This sensor should always be available."""
            return True

    # Online status sensor is enabled by default
    online_sensor = OnlineStatusBinarySensor(coordinator, config_entry.entry_id)
    binary_sensors.append(online_sensor)

    _LOGGER.info("Created %d binary sensor entities", len(binary_sensors))
    if binary_sensors:
        async_add_entities(binary_sensors, True)
