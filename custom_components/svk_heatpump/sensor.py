"""Sensor platform for SVK Heatpump integration."""

import logging
from datetime import datetime, timezone
from typing import Any

try:
    from homeassistant.components.sensor import (
        SensorDeviceClass,
        SensorEntity,
        SensorEntityDescription,
        SensorStateClass,
    )
except ImportError:
    # Fallback for older Home Assistant versions
    from homeassistant.components.sensor import (
        SensorDeviceClass,
        SensorEntity,
        SensorStateClass,
    )
    # For older versions, create a fallback EntityDescription
    from dataclasses import dataclass
    
    @dataclass
    class SensorEntityDescription:
        """Fallback SensorEntityDescription for older HA versions."""
        key: str
        name: str | None = None
        translation_key: str | None = None
        device_class: str | None = None
        native_unit_of_measurement: str | None = None
        state_class: str | None = None
        entity_category: str | None = None
        icon: str | None = None
        enabled_default: bool = True
from homeassistant.const import (
    EntityCategory,
)
from homeassistant.core import HomeAssistant

# Import from catalog will be done lazily to avoid blocking imports
from .entity_base import SVKBaseEntity

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)

# Lazy loading of catalog functions to avoid blocking imports
def _lazy_import_catalog():
    """Lazy import catalog functions to avoid blocking imports."""
    global ENTITIES, get_sensor_entities, COUNTER_SENSORS, SYSTEM_COUNTER_SENSORS, SYSTEM_SENSORS
    if 'ENTITIES' not in globals():
        from .catalog import (
            ENTITIES,
            get_sensor_entities,
            COUNTER_SENSORS,
            SYSTEM_COUNTER_SENSORS,
            SYSTEM_SENSORS,
        )

# System-level entities that should follow the alarm_count pattern
SYSTEM_LEVEL_ENTITIES = {
    "alarm_count",  # Existing
    "last_update_sensor",  # Existing
    "system_systemview",
    "service_com_ipadr",
    "service_com_macadr",
    "service_info_appversion",
    "service_misc_lup200swver",
    "user_time_year",
    "user_time_month",
    "user_time_day",
    "user_time_hour",
    "user_time_minute",
    "service_defrost_defrhgcount",
    "service_defrost_defraircnt",
    "service_heatpump_runtime",
    "service_compressor_compruntime",
}


class SVKSensor(SVKBaseEntity, SensorEntity):
    """Representation of a SVK Heatpump sensor."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the sensor."""
        # Initialize SVKBaseEntity
        super().__init__(
            coordinator,
            config_entry_id,
            entity_key,
            None,  # unique_suffix should be None to use entity_key for translation
            enabled_by_default=enabled_by_default
        )

        # Get entity info from catalog
        entity_info = self._get_entity_info()
        data_type = entity_info.get("data_type", "")
        unit = entity_info.get("unit", "")
        category = entity_info.get("category", "")

        _LOGGER.debug(
            "Creating sensor entity: %s (group: %s, enabled_by_default: %s)",
            entity_key,
            self._group_key,
            enabled_by_default,
        )

        # Map data types to Home Assistant device classes
        device_class = None
        if data_type == "temperature":
            device_class = SensorDeviceClass.TEMPERATURE
        elif data_type == "voltage":
            device_class = SensorDeviceClass.VOLTAGE
        elif data_type == "power":
            device_class = SensorDeviceClass.POWER
        elif data_type == "energy":
            device_class = SensorDeviceClass.ENERGY
        elif data_type == "time":
            device_class = SensorDeviceClass.DURATION

        # Map data types to Home Assistant state classes
        state_class = None
        if data_type in ["temperature", "voltage", "power", "percentage", "number"]:
            state_class = SensorStateClass.MEASUREMENT
        elif data_type == "time" and unit == "h":
            state_class = SensorStateClass.TOTAL_INCREASING

        # Add explicit handling for string data types
        if data_type == "string":
            device_class = None  # Explicitly set to None for text sensors
            state_class = None  # Explicitly set to None for text sensors

        # Set entity category based on category
        entity_category = None
        if category == "Configuration":
            entity_category = EntityCategory.DIAGNOSTIC
        elif category == "Settings":
            entity_category = EntityCategory.DIAGNOSTIC
        elif "runtime" in entity_key or "gain" in entity_key or "count" in entity_key:
            entity_category = EntityCategory.DIAGNOSTIC
        elif entity_key in SYSTEM_LEVEL_ENTITIES:
            entity_category = EntityCategory.DIAGNOSTIC

        # Create entity description
        self.entity_description = SensorEntityDescription(
            key=self._entity_key,
            translation_key=self._entity_key,  # Use entity_key for translation lookup
            name=None,  # Let translation system handle the name
            device_class=device_class,
            state_class=state_class,
            native_unit_of_measurement=unit,
            entity_category=entity_category,
        )


    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        value = self._get_entity_value()
        self._log_value_retrieval(value)

        # Get entity info from catalog for data type
        entity_info = self._get_entity_info()
        data_type = entity_info.get("data_type", "")
        unit = entity_info.get("unit", "")

        # Apply special handling for temperature sentinel rule
        if data_type == "temperature":
            value = self._apply_temperature_sentinel_rule(value)

        # Apply percentage clamping for percentage values
        value = self._apply_percentage_clamping(value, unit)

        # Always return the value, even if None, to ensure entities update properly
        # The availability property will handle None values appropriately
        return value


class SVKHeatpumpSensor(SVKBaseEntity, SensorEntity):
    """Representation of a SVK Heatpump sensor."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        entity_id: int,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            config_entry_id,
            entity_key,
            entity_key,
            entity_id=entity_id,
            enabled_by_default=enabled_by_default
        )

        _LOGGER.debug(
            "Creating sensor entity: %s (ID: %s, enabled_by_default: %s)",
            entity_key,
            entity_id,
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
        if self._device_class == "temperature":
            device_class = SensorDeviceClass.TEMPERATURE
        elif self._device_class == "power":
            device_class = SensorDeviceClass.POWER
        elif self._device_class == "energy":
            device_class = SensorDeviceClass.ENERGY

        state_class = None
        if self._state_class == "measurement":
            state_class = SensorStateClass.MEASUREMENT
        elif self._state_class == "total":
            state_class = SensorStateClass.TOTAL
        elif self._state_class == "total_increasing":
            state_class = SensorStateClass.TOTAL_INCREASING

        # Set entity category based on entity definition dictionaries
        entity_category = None
        
        # Lazy load catalog functions
        _lazy_import_catalog()

        if self._entity_key in COUNTER_SENSORS:
            entity_category = EntityCategory.DIAGNOSTIC
        elif self._entity_key in SYSTEM_SENSORS:
            entity_category = EntityCategory.DIAGNOSTIC
        elif self._entity_key in SYSTEM_COUNTER_SENSORS:
            entity_category = EntityCategory.DIAGNOSTIC
        elif (
            "runtime" in self._entity_key
            or "gain" in self._entity_key
            or "count" in self._entity_key
        ):
            entity_category = EntityCategory.DIAGNOSTIC

        # Use entity_key directly for friendly name
        self.entity_description = SensorEntityDescription(
            key=self._entity_key,
            translation_key=self._entity_key,
            name=None,  # Let translation system handle the name
            device_class=device_class,
            state_class=state_class,
            native_unit_of_measurement=self._unit,
            entity_category=entity_category,
        )


    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        value = self._get_entity_value()
        self._log_value_retrieval(value)

        # Apply special handling for temperature sentinel rule
        if self._device_class == "temperature":
            value = self._apply_temperature_sentinel_rule(value)

        # Apply percentage clamping for percentage values
        value = self._apply_percentage_clamping(value, self._unit)

        return value


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up SVK Heatpump sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    _LOGGER.info("Setting up SVK Heatpump sensors for entry %s", config_entry.entry_id)

    # Use the entity factory to create all sensor entities
    from .entity_factory import create_entities_for_platform
    
    # Lazy load catalog functions before creating entities
    _lazy_import_catalog()
    
    sensors = create_entities_for_platform(
        coordinator,
        config_entry.entry_id,
        "sensor"
    )

    # Add alarm count sensor
    alarm_count_desc = SensorEntityDescription(
        key="alarm_count",
        translation_key="alarm_count",
        name=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="alarms",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    class AlarmCountSensor(SVKBaseEntity, SensorEntity):
        """Sensor for alarm count."""

        _attr_entity_registry_enabled_default = True

        def __init__(self, coordinator: SVKHeatpumpDataCoordinator, config_entry_id: str) -> None:
            # Initialize SVKBaseEntity
            super().__init__(
                coordinator,
                config_entry_id,
                "alarm_count",
                "system_alarm_count"
            )
            self.entity_description = alarm_count_desc

        @property
        def native_value(self) -> int:
            """Return the number of active alarms."""
            if self.coordinator.data:
                alarm_summary = self.coordinator.get_alarm_summary()
                return alarm_summary.get("count", 0)
            return 0

    # Alarm count sensor is enabled by default
    alarm_sensor = AlarmCountSensor(coordinator, config_entry.entry_id)
    sensors.append(alarm_sensor)

    # Add last update sensor
    last_update_desc = SensorEntityDescription(
        key="last_update_sensor",
        translation_key="last_update_sensor",
        name=None,
        device_class=SensorDeviceClass.TIMESTAMP,
        state_class=None,
        native_unit_of_measurement=None,
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    class LastUpdateSensor(SVKBaseEntity, SensorEntity):
        """Sensor for last update timestamp."""

        _attr_entity_registry_enabled_default = True

        def __init__(self, coordinator, config_entry_id):
            # Initialize SVKBaseEntity
            super().__init__(
                coordinator,
                config_entry_id,
                "last_update_sensor",
                "system_last_update_sensor"
            )
            self.entity_description = last_update_desc

        @property
        def native_value(self) -> Any:
            """Return the last update timestamp."""
            if self.coordinator.data:
                value = self.coordinator.data.get("last_update")
                # Ensure we always return a datetime object with timezone
                if isinstance(value, (int, float)):
                    # Convert Unix timestamp to datetime with timezone
                    return datetime.fromtimestamp(value, timezone.utc)
                elif isinstance(value, datetime):
                    # Ensure datetime has timezone info
                    if value.tzinfo is None:
                        return value.replace(tzinfo=timezone.utc)
                    return value
            return None

    # Last update sensor is enabled by default
    last_update_sensor = LastUpdateSensor(coordinator, config_entry.entry_id)
    sensors.append(last_update_sensor)

    _LOGGER.info("Created %d sensor entities", len(sensors))
    if sensors:
        async_add_entities(sensors, True)
