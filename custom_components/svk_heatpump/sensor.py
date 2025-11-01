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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .catalog import ENTITIES, get_sensor_entities, COUNTER_SENSORS, SYSTEM_COUNTER_SENSORS, SYSTEM_SENSORS

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)



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


class SVKSensor(SVKHeatpumpBaseEntity, SensorEntity):
    """Representation of a SVK Heatpump sensor."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the sensor."""
        # Extract group key from entity key (first part before underscore)
        group_key = entity_key.split("_")[0]

        # Get entity info from catalog
        entity_info = ENTITIES.get(entity_key, {})
        data_type = entity_info.get("data_type", "")
        unit = entity_info.get("unit", "")
        category = entity_info.get("category", "")

        # Initialize SVKHeatpumpBaseEntity (which inherits from CoordinatorEntity)
        super().__init__(coordinator, config_entry_id)

        # Initialize additional attributes
        self._entity_key = entity_key
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._group_key = group_key  # For unique_id property

        _LOGGER.debug(
            "Creating sensor entity: %s (group: %s, enabled_by_default: %s)",
            entity_key,
            group_key,
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

        # Create entity description
        self.entity_description = SensorEntityDescription(
            key=entity_key,
            name=None,  # Use None for translation
            device_class=device_class,
            native_unit_of_measurement=unit,
            state_class=state_class,
            entity_category=entity_category,
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for sensor."""
        return f"{DOMAIN}_{self._group_key}_{self._entity_key}"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        value = self.coordinator.get_entity_value(self._entity_key)

        # Log value retrieval for debugging (reduced frequency to prevent log storms)
        if value is None:
            _LOGGER.debug("Sensor %s returned None value", self._entity_key)
        else:
            _LOGGER.debug("Sensor %s returned value: %s", self._entity_key, value)

        # Get entity info from catalog for data type
        entity_info = ENTITIES.get(self._entity_key, {})
        data_type = entity_info.get("data_type", "")
        unit = entity_info.get("unit", "")

        # Apply special handling for temperature sentinel rule
        if data_type == "temperature" and value is not None:
            if isinstance(value, (int, float)) and value <= -80.0:
                # Temperature sentinel rule: ≤ -80.0°C marks entity unavailable
                _LOGGER.debug(
                    "Sensor %s temperature %s°C is below sentinel threshold, marking unavailable",
                    self._entity_key,
                    value,
                )
                return None

        # Apply percentage clamping for percentage values
        if unit == "%" and value is not None:
            try:
                if isinstance(value, (int, float)):
                    clamped_value = max(0, min(100, float(value)))
                    if clamped_value != float(value):
                        _LOGGER.debug(
                            "Sensor %s percentage value clamped from %s to %s",
                            self._entity_key,
                            value,
                            clamped_value,
                        )
                    return clamped_value
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "Sensor %s failed to clamp percentage value %s",
                    self._entity_key,
                    value,
                )
                pass

        # Always return the value, even if None, to ensure entities update properly
        # The availability property will handle None values appropriately
        return value

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # For JSON API, entities should be available even if data fetching fails initially
        if self.coordinator.is_json_client:
            is_available = self.coordinator.is_entity_available(self._entity_key)
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.debug(
                "JSON API Sensor %s availability: %s (entity exists in mapping, current value: %s)",
                self._entity_key,
                is_available,
                value,
            )
            # Removed excessive diagnostic logging to prevent log storms
            return is_available
        else:
            # For HTML scraping, require successful update
            is_available = (
                self.coordinator.last_update_success
                and self.coordinator.is_entity_available(self._entity_key)
            )
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.debug(
                "HTML API Sensor %s availability: %s (last_update_success: %s, current value: %s)",
                self._entity_key,
                is_available,
                self.coordinator.last_update_success,
                value,
            )
            return is_available


class SVKHeatpumpSensor(SVKHeatpumpBaseEntity, SensorEntity):
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
        super().__init__(coordinator, config_entry_id)
        self._entity_key = entity_key
        self._entity_id = entity_id
        self._attr_entity_registry_enabled_default = enabled_by_default

        _LOGGER.debug(
            "Creating sensor entity: %s (ID: %s, enabled_by_default: %s)",
            entity_key,
            entity_id,
            enabled_by_default,
        )

        # Find entity by ID in ENTITIES
        entity_info = None
        for entity_key, entity_data in ENTITIES.items():
            if "id" in entity_data and entity_data["id"] == entity_id:
                entity_info = {
                    "entity_key": entity_key,
                    "unit": entity_data.get("unit", ""),
                    "device_class": entity_data.get("device_class"),
                    "state_class": entity_data.get("state_class"),
                    "original_name": entity_data.get("original_name", ""),
                }
                break
        
        if entity_info:
            self._entity_key = entity_info["entity_key"]
            self._unit = entity_info["unit"]
            self._device_class = entity_info["device_class"]
            self._state_class = entity_info["state_class"]
            self._original_name = entity_info["original_name"]
        else:
            # Fallback to empty values if not found
            self._entity_key = ""
            self._unit = ""
            self._device_class = None
            self._state_class = None
            self._original_name = ""

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
            name=None,  # Use None for translation
            device_class=device_class,
            native_unit_of_measurement=self._unit,
            state_class=state_class,
            entity_category=entity_category,
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for sensor."""
        return f"{self._config_entry_id}_{self._entity_id}"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        value = self.coordinator.get_entity_value(self._entity_key)

        # Log value retrieval for debugging
        if value is None:
            _LOGGER.debug(
                "Sensor %s (ID: %s) returned None value",
                self._entity_key,
                self._entity_id,
            )
        else:
            _LOGGER.debug(
                "Sensor %s (ID: %s) returned value: %s",
                self._entity_key,
                self._entity_id,
                value,
            )

        # Apply special handling for temperature sentinel rule
        if self._device_class == "temperature" and value is not None:
            if isinstance(value, (int, float)) and value <= -80.0:
                # Temperature sentinel rule: ≤ -80.0°C marks entity unavailable
                _LOGGER.debug(
                    "Sensor %s temperature %s°C is below sentinel threshold, marking unavailable",
                    self._entity_key,
                    value,
                )
                return None

        # Apply percentage clamping for percentage values
        if self._unit == "%" and value is not None:
            try:
                if isinstance(value, (int, float)):
                    clamped_value = max(0, min(100, float(value)))
                    if clamped_value != float(value):
                        _LOGGER.debug(
                            "Sensor %s percentage value clamped from %s to %s",
                            self._entity_key,
                            value,
                            clamped_value,
                        )
                    return clamped_value
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "Sensor %s failed to clamp percentage value %s",
                    self._entity_key,
                    value,
                )
                pass

        return value

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # For JSON API, entities should be available even if data fetching fails initially
        if self.coordinator.is_json_client:
            is_available = self.coordinator.is_entity_available(self._entity_key)
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.debug(
                "JSON API Sensor %s availability: %s (entity exists in mapping, current value: %s)",
                self._entity_key,
                is_available,
                value,
            )
            # Removed excessive diagnostic logging to prevent log storms
            return is_available
        else:
            # For HTML scraping, require successful update
            is_available = (
                self.coordinator.last_update_success
                and self.coordinator.is_entity_available(self._entity_key)
            )
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.debug(
                "HTML API Sensor %s availability: %s (last_update_success: %s, current value: %s)",
                self._entity_key,
                is_available,
                self.coordinator.last_update_success,
                value,
            )
            return is_available


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up SVK Heatpump sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    _LOGGER.info("Setting up SVK Heatpump sensors for entry %s", config_entry.entry_id)
    _LOGGER.info("Coordinator is_json_client: %s", coordinator.is_json_client)

    sensors = []

    # Create sensors based on sensor entities from catalog
    if coordinator.is_json_client:
        # Create all sensor entities from the catalog
        for entity_key in get_sensor_entities():
            try:
                # Get entity info from catalog
                entity_info = ENTITIES.get(entity_key, {})
                entity_id = entity_info.get("id")
                enabled_by_default = coordinator.is_entity_enabled(entity_id) if entity_id else False

                # Create the sensor using the new SVKSensor class
                sensor = SVKSensor(
                    coordinator,
                    entity_key,
                    config_entry.entry_id,
                    enabled_by_default=enabled_by_default,
                )

                sensors.append(sensor)
                _LOGGER.debug(
                    "Added sensor entity: %s (enabled_by_default: %s)",
                    entity_key,
                    enabled_by_default,
                )
            except Exception as err:
                _LOGGER.error("Failed to create sensor entity %s: %s", entity_key, err)
                # Continue with other entities even if one fails
                continue
    else:
        # Fall back to HTML scraping entities for backward compatibility
        # Create basic entities even if JSON client is not available
        _LOGGER.warning(
            "JSON client not available, creating essential fallback entities"
        )

        # Create essential entities as fallback to ensure basic functionality
        essential_entities = [
            ("display_input_theatsupply", 253),
            ("display_input_theatreturn", 254),
            ("display_input_twatertank", 255),
            ("display_input_tamb", 256),
            ("display_input_troom", 257),
            ("display_heatpump_state", 297),
            ("display_heatpump_capacityact", 299),
            ("display_heatpump_capacityreq", 300),
            ("user_parameters_seasonmode", 278),
            ("user_hotwater_setpoint", 383),
            ("heating_heating_setpointact", 420),
            ("service_compressor_compruntime", 447),
            ("display_output_alarm", 228),
        ]

        for entity_key, entity_id in essential_entities:
            try:
                sensor = SVKHeatpumpSensor(
                    coordinator,
                    entity_key,
                    entity_id,
                    config_entry.entry_id,
                    enabled_by_default=True,
                )
                sensors.append(sensor)
                _LOGGER.info(
                    "Added fallback sensor entity: %s (ID: %s)", entity_key, entity_id
                )
            except Exception as err:
                _LOGGER.error(
                    "Failed to create fallback sensor entity %s (ID: %s): %s",
                    entity_key,
                    entity_id,
                    err,
                )
                # Continue with other entities even if one fails
                continue

    # Add alarm count sensor
    alarm_count_desc = SensorEntityDescription(
        key="alarm_count",
        name="Alarm Count",
        device_class=None,
        native_unit_of_measurement="alarms",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    class AlarmCountSensor(SVKHeatpumpBaseEntity, SensorEntity):
        """Sensor for alarm count."""

        _attr_entity_registry_enabled_default = True

        def __init__(self, coordinator: SVKHeatpumpDataCoordinator, config_entry_id: str) -> None:
            # Initialize SVKHeatpumpBaseEntity (which inherits from CoordinatorEntity)
            super().__init__(coordinator, config_entry_id)
            self._attr_unique_id = f"{DOMAIN}_system_alarm_count"
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
        name="Last Update",
        device_class=SensorDeviceClass.TIMESTAMP,
        native_unit_of_measurement=None,
        state_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    class LastUpdateSensor(SVKHeatpumpBaseEntity, SensorEntity):
        """Sensor for last update timestamp."""

        _attr_entity_registry_enabled_default = True

        def __init__(self, coordinator, config_entry_id):
            # Initialize SVKHeatpumpBaseEntity (which inherits from CoordinatorEntity)
            super().__init__(coordinator, config_entry_id)
            self._attr_unique_id = f"{DOMAIN}_system_last_update_sensor"
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
