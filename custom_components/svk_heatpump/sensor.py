"""Sensor platform for SVK Heatpump integration."""
import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .compat import DISABLED_INTEGRATION

from . import const
from . import coordinator

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator
from .entity_base import SVKBaseEntity
from .catalog import SENSOR_ENTITIES, ENTITIES

_LOGGER = logging.getLogger(__name__)


def _get_constants():
    """Lazy import of constants to prevent blocking during async setup."""
    from .const import ID_MAP, DEFAULT_ENABLED_ENTITIES
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
        name = entity_info.get("name", entity_key.replace("_", " ").title())
        data_type = entity_info.get("data_type", "")
        unit = entity_info.get("unit", "")
        category = entity_info.get("category", "")
        
        # Initialize SVKHeatpumpBaseEntity (which inherits from CoordinatorEntity)
        super().__init__(coordinator, config_entry_id)
        
        # Initialize additional attributes
        self._entity_key = entity_key
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._group_key = group_key  # For unique_id property
        
        _LOGGER.debug("Creating sensor entity: %s (group: %s, enabled_by_default: %s)",
                     entity_key, group_key, enabled_by_default)
        
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
        
        # Set entity category based on category
        entity_category = None
        if category == "Configuration":
            entity_category = EntityCategory.CONFIG
        elif category == "Settings":
            entity_category = EntityCategory.CONFIG
        elif "runtime" in entity_key or "gain" in entity_key or "count" in entity_key:
            entity_category = EntityCategory.DIAGNOSTIC
        
        # Create entity description
        self.entity_description = SensorEntityDescription(
            key=entity_key,
            name=name,
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
        
        # Log value retrieval for debugging
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
                _LOGGER.debug("Sensor %s temperature %s°C is below sentinel threshold, marking unavailable", self._entity_key, value)
                return None
        
        # Apply percentage clamping for percentage values
        if unit == "%" and value is not None:
            try:
                if isinstance(value, (int, float)):
                    clamped_value = max(0, min(100, float(value)))
                    if clamped_value != float(value):
                        _LOGGER.debug("Sensor %s percentage value clamped from %s to %s", self._entity_key, value, clamped_value)
                    return clamped_value
            except (ValueError, TypeError):
                _LOGGER.debug("Sensor %s failed to clamp percentage value %s", self._entity_key, value)
                pass
        
        return value
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Debug logging to understand the error
        _LOGGER.debug("DEBUG: Checking availability for %s, type: %s", self._entity_key, type(self))
        _LOGGER.debug("DEBUG: hasattr coordinator: %s", hasattr(self, 'coordinator'))
        _LOGGER.debug("DEBUG: hasattr _coordinator: %s", hasattr(self, '_coordinator'))
        
        # Try to access coordinator and see what happens
        try:
            _LOGGER.debug("DEBUG: coordinator type: %s", type(self.coordinator))
            _LOGGER.debug("DEBUG: coordinator is_json_client: %s", self.coordinator.is_json_client)
        except AttributeError as err:
            _LOGGER.error("DEBUG: AttributeError accessing coordinator: %s", err)
            # Try alternative access methods
            if hasattr(self, '_coordinator'):
                _LOGGER.debug("DEBUG: Trying _coordinator instead")
                return self._coordinator.is_json_client
            raise
        
        # For JSON API, entities should be available even if data fetching fails initially
        if self.coordinator.is_json_client:
            is_available = self.coordinator.is_entity_available(self._entity_key)
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.info("JSON API Sensor %s availability: %s (entity exists in mapping, current value: %s)",
                         self._entity_key, is_available, value)
            # Add additional diagnostic info
            if not is_available:
                _LOGGER.warning("DIAGNOSTIC: Entity %s is not available - this may indicate a data fetching or parsing issue", self._entity_key)
                # Log detailed availability reasons
                if hasattr(self.coordinator, 'data') and self.coordinator.data:
                    _LOGGER.warning("DIAGNOSTIC: Coordinator data exists, last_update: %s",
                                 self.coordinator.data.get('last_update', 'None'))
                    _LOGGER.warning("DIAGNOSTIC: Parsing stats: %s",
                                 self.coordinator.data.get('parsing_stats', 'None'))
                else:
                    _LOGGER.warning("DIAGNOSTIC: No coordinator data available - this indicates a fundamental connection issue")
            elif value is None:
                _LOGGER.warning("DIAGNOSTIC: Entity %s is available but has no value - likely a parsing or data issue", self._entity_key)
            return is_available
        else:
            # For HTML scraping, require successful update
            is_available = self.coordinator.last_update_success and self.coordinator.is_entity_available(self._entity_key)
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.info("HTML API Sensor %s availability: %s (last_update_success: %s, current value: %s)",
                         self._entity_key, is_available, self.coordinator.last_update_success, value)
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
        
        _LOGGER.debug("Creating sensor entity: %s (ID: %s, enabled_by_default: %s)",
                     entity_key, entity_id, enabled_by_default)
        
        # Get entity info from ID_MAP (5-element structure)
        ID_MAP, _ = _get_constants()
        entity_info = ID_MAP.get(entity_id, ("", "", None, None, ""))
        self._entity_key, self._unit, self._device_class, self._state_class, self._original_name = entity_info
        
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
        # Get entity category from entity definition dictionaries
        from .const import COUNTER_SENSORS, SYSTEM_SENSORS, SYSTEM_COUNTER_SENSORS
        
        if self._entity_key in COUNTER_SENSORS:
            entity_category = EntityCategory.DIAGNOSTIC
        elif self._entity_key in SYSTEM_SENSORS:
            entity_category = EntityCategory.DIAGNOSTIC
        elif self._entity_key in SYSTEM_COUNTER_SENSORS:
            entity_category = EntityCategory.DIAGNOSTIC
        elif "runtime" in self._entity_key or "gain" in self._entity_key or "count" in self._entity_key:
            entity_category = EntityCategory.DIAGNOSTIC
        
        # Use original_name for friendly display name if available
        friendly_name = self._original_name.replace("_", " ").title() if self._original_name else self._entity_key.replace("_", " ").title()
        
        self.entity_description = SensorEntityDescription(
            key=self._entity_key,
            name=friendly_name,
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
            _LOGGER.debug("Sensor %s (ID: %s) returned None value", self._entity_key, self._entity_id)
        else:
            _LOGGER.debug("Sensor %s (ID: %s) returned value: %s", self._entity_key, self._entity_id, value)
        
        # Apply special handling for temperature sentinel rule
        if self._device_class == "temperature" and value is not None:
            if isinstance(value, (int, float)) and value <= -80.0:
                # Temperature sentinel rule: ≤ -80.0°C marks entity unavailable
                _LOGGER.debug("Sensor %s temperature %s°C is below sentinel threshold, marking unavailable", self._entity_key, value)
                return None
        
        # Apply percentage clamping for percentage values
        if self._unit == "%" and value is not None:
            try:
                if isinstance(value, (int, float)):
                    clamped_value = max(0, min(100, float(value)))
                    if clamped_value != float(value):
                        _LOGGER.debug("Sensor %s percentage value clamped from %s to %s", self._entity_key, value, clamped_value)
                    return clamped_value
            except (ValueError, TypeError):
                _LOGGER.debug("Sensor %s failed to clamp percentage value %s", self._entity_key, value)
                pass
        
        return value
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Debug logging to understand error
        _LOGGER.debug("DEBUG: Checking availability for %s, type: %s", self._entity_key, type(self))
        _LOGGER.debug("DEBUG: hasattr coordinator: %s", hasattr(self, 'coordinator'))
        _LOGGER.debug("DEBUG: hasattr _coordinator: %s", hasattr(self, '_coordinator'))
        
        # Try to access coordinator and see what happens
        try:
            _LOGGER.debug("DEBUG: coordinator type: %s", type(self.coordinator))
            _LOGGER.debug("DEBUG: coordinator is_json_client: %s", self.coordinator.is_json_client)
        except AttributeError as err:
            _LOGGER.error("DEBUG: AttributeError accessing coordinator: %s", err)
            # Try alternative access methods
            if hasattr(self, '_coordinator'):
                _LOGGER.debug("DEBUG: Trying _coordinator instead")
                return self._coordinator.is_json_client
            raise
        
        # For JSON API, entities should be available even if data fetching fails initially
        if self.coordinator.is_json_client:
            is_available = self.coordinator.is_entity_available(self._entity_key)
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.info("JSON API Sensor %s availability: %s (entity exists in mapping, current value: %s)",
                         self._entity_key, is_available, value)
            # Add additional diagnostic info
            if not is_available:
                _LOGGER.warning("Entity %s is not available - this may indicate a data fetching or parsing issue", self._entity_key)
            elif value is None:
                _LOGGER.warning("Entity %s is available but has no value - likely a parsing or data issue", self._entity_key)
            return is_available
        else:
            # For HTML scraping, require successful update
            is_available = self.coordinator.last_update_success and self.coordinator.is_entity_available(self._entity_key)
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.info("HTML API Sensor %s availability: %s (last_update_success: %s, current value: %s)",
                         self._entity_key, is_available, self.coordinator.last_update_success, value)
            return is_available


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up SVK Heatpump sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    _LOGGER.info("Setting up SVK Heatpump sensors for entry %s", config_entry.entry_id)
    _LOGGER.info("Coordinator is_json_client: %s", coordinator.is_json_client)
    
    sensors = []
    
    # Create sensors based on SENSOR_ENTITIES from catalog
    if coordinator.is_json_client:
        # Create all sensor entities from the catalog
        for entity_key in SENSOR_ENTITIES:
            try:
                # Get entity info from catalog
                entity_info = ENTITIES.get(entity_key, {})
                name = entity_info.get("name", entity_key.replace("_", " ").title())
                category = entity_info.get("category", "")
                
                # Determine if this entity should be enabled by default
                # For now, enable all sensor entities from the catalog
                enabled_by_default = True
                
                # Create the sensor using the new SVKSensor class
                sensor = SVKSensor(
                    coordinator,
                    entity_key,
                    config_entry.entry_id,
                    enabled_by_default=enabled_by_default
                )
                
                sensors.append(sensor)
                _LOGGER.debug("Added sensor entity: %s (name: %s, enabled_by_default: %s)",
                             entity_key, name, enabled_by_default)
            except Exception as err:
                _LOGGER.error("Failed to create sensor entity %s: %s", entity_key, err)
                # Continue with other entities even if one fails
                continue
    else:
        # Fall back to HTML scraping entities for backward compatibility
        # Create basic entities even if JSON client is not available
        _LOGGER.warning("JSON client not available, creating essential fallback entities")
        
        # Create essential entities as fallback to ensure basic functionality
        essential_entities = [
            ("heating_supply_temp", 253),
            ("heating_return_temp", 254),
            ("water_tank_temp", 255),
            ("ambient_temp", 256),
            ("room_temp", 257),
            ("heatpump_state", 297),
            ("capacity_actual", 299),
            ("capacity_requested", 300),
            ("season_mode", 278),
            ("hot_water_setpoint", 383),
            ("heating_setpoint_actual", 420),
            ("compressor_runtime", 447),
            ("alarm_output", 228),
        ]
        
        for entity_key, entity_id in essential_entities:
            try:
                sensor = SVKHeatpumpSensor(
                    coordinator,
                    entity_key,
                    entity_id,
                    config_entry.entry_id,
                    enabled_by_default=True
                )
                sensors.append(sensor)
                _LOGGER.info("Added fallback sensor entity: %s (ID: %s)", entity_key, entity_id)
            except Exception as err:
                _LOGGER.error("Failed to create fallback sensor entity %s (ID: %s): %s",
                             entity_key, entity_id, err)
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
        
        def __init__(self, coordinator, config_entry_id):
            # Initialize SVKHeatpumpBaseEntity (which inherits from CoordinatorEntity)
            super().__init__(coordinator, config_entry_id)
            self._attr_name = "Alarm Count"
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
            self._attr_name = "Last Update"
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