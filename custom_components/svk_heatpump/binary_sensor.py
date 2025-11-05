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
        translation_key: str | None = None
        device_class: str | None = None
        entity_category: str | None = None
        icon: str | None = None
        enabled_default: bool = True

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator
from .entity_base import SVKBaseEntity

_LOGGER = logging.getLogger(__name__)

# Lazy loading of catalog functions to avoid blocking imports
def _lazy_import_catalog():
    """Lazy import catalog functions to avoid blocking imports."""
    global BINARY_SENSORS, get_binary_sensor_entities, ENTITIES, DEFAULT_ENABLED_ENTITIES
    if 'BINARY_SENSORS' not in globals():
        from .catalog import (
            BINARY_SENSORS,
            get_binary_sensor_entities,
            ENTITIES,
            DEFAULT_ENABLED_ENTITIES,
        )

def _get_constants():
    """Lazy import of constants to prevent blocking during async setup."""
    _lazy_import_catalog()
    return ENTITIES, DEFAULT_ENABLED_ENTITIES


class SVKHeatpumpBinarySensor(SVKBaseEntity, BinarySensorEntity):
    """Representation of a SVK Heatpump binary sensor."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        config_entry_id: str,
        enabled_by_default: bool = True,
        entity_id: int | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(
            coordinator,
            config_entry_id,
            entity_key,
            None,  # unique_suffix should be None to use entity_key for translation
            entity_id=entity_id,
            enabled_by_default=enabled_by_default
        )

        _LOGGER.debug(
            "Creating binary sensor entity: %s (enabled_by_default: %s)",
            entity_key,
            enabled_by_default,
        )

        # Get entity info from catalog
        entity_info = self._get_entity_info()
        self._unit = entity_info.get("unit", "")
        self._device_class = entity_info.get("device_class")
        self._state_class = entity_info.get("state_class")
        self._original_name = entity_info.get("original_name", "")

        # Create entity description
        device_class = None
        entity_category = None

        if self._entity_key == "alarm_active":
            device_class = BinarySensorDeviceClass.PROBLEM
        # Note: Digital outputs are identified by entity_key pattern in ENTITIES
        elif "output" in entity_key.lower():  # Digital outputs
            device_class = BinarySensorDeviceClass.RUNNING

        # Set entity category based on entity definition
        
        # Lazy load catalog functions
        _lazy_import_catalog()

        if self._entity_key in BINARY_SENSORS and BINARY_SENSORS[self._entity_key].get(
            "entity_category"
        ):
            entity_category = getattr(
                EntityCategory,
                BINARY_SENSORS[self._entity_key]["entity_category"].upper(),
            )

        # Use entity_key for translation
        self.entity_description = BinarySensorEntityDescription(
            key=self._entity_key,
            translation_key=self._entity_key,  # Use entity_key for translation lookup
            name=None,  # Let translation system handle the name
            device_class=device_class,
            entity_category=entity_category,
        )


    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        value = self._get_entity_value()
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

    # Use the entity factory to create all binary sensor entities
    from .entity_factory import create_entities_for_platform
    
    # Lazy load catalog functions before creating entities
    _lazy_import_catalog()
    
    binary_sensors = create_entities_for_platform(
        coordinator,
        config_entry.entry_id,
        "binary_sensor"
    )

    # Add additional binary sensors for system states
    system_state_desc = BinarySensorEntityDescription(
        key="system_active",
        translation_key="system_active",
        name=None,  # Let translation system handle the name
        device_class=BinarySensorDeviceClass.RUNNING,
    )

    class SystemActiveBinarySensor(SVKBaseEntity, BinarySensorEntity):
        """Binary sensor for system active state."""

        def __init__(self, coordinator, config_entry_id):
            super().__init__(
                coordinator,
                config_entry_id,
                "system_active",
                "system_active",
                enabled_by_default=True
            )
            self.entity_description = system_state_desc

        @property
        def is_on(self) -> bool:
            """Return true if the system is active."""
            if self.coordinator.data:
                    heatpump_state = self.coordinator.data.get("display_heatpump_state", "")
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
        translation_key="online_status",
        name=None,  # Let translation system handle the name
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    )

    class OnlineStatusBinarySensor(SVKBaseEntity, BinarySensorEntity):
        """Binary sensor for online status."""

        def __init__(self, coordinator, config_entry_id):
            super().__init__(
                coordinator,
                config_entry_id,
                "online_status",
                "online_status",
                enabled_by_default=True
            )
            self.entity_description = online_desc

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
