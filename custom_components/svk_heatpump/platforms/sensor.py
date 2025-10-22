"""Sensor platform for SVK Heatpump integration."""
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
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import (
    DOMAIN,
    ID_MAP,
)
from ..coordinator import SVKHeatpumpDataCoordinator


class SVKHeatpumpSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SVK Heatpump sensor."""
    
    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        entity_id: int,
        config_entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id
        self._entity_key = entity_key
        self._entity_id = entity_id
        
        # Get entity info from ID_MAP (5-element structure)
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
        
        # Set entity category based on entity type
        entity_category = None
        if self._entity_key in ["alarm_code"] or "runtime" in self._entity_key or "gain" in self._entity_key:
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
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry_id)},
            name="SVK Heatpump",
            manufacturer="SVK",
            model="LMC320",
        )
    
    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        value = self.coordinator.get_entity_value(self._entity_key)
        
        # Apply special handling for temperature sentinel rule
        if self._device_class == "temperature" and value is not None:
            if isinstance(value, (int, float)) and value <= -50.0:
                # Temperature sentinel rule: ≤ -50.0°C marks entity unavailable
                return None
        
        # Apply percentage clamping for percentage values
        if self._unit == "%" and value is not None:
            try:
                if isinstance(value, (int, float)):
                    return max(0, min(100, float(value)))
            except (ValueError, TypeError):
                pass
        
        return value
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.is_entity_available(self._entity_key)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up SVK Heatpump sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    # Get enabled entities from coordinator
    enabled_entities = coordinator.get_enabled_entities(config_entry)
    
    sensors = []
    
    # Create sensors based on ID_MAP for JSON API
    if coordinator.is_json_client:
        for entity_id, (entity_key, unit, device_class, state_class, original_name) in ID_MAP.items():
            # Skip binary sensor entities (IDs 222-225 are digital outputs)
            if entity_id in [222, 223, 224, 225]:
                continue
            
            # Check if this entity should be enabled
            if entity_key in enabled_entities:
                sensor = SVKHeatpumpSensor(
                    coordinator,
                    entity_key,
                    entity_id,
                    config_entry.entry_id
                )
                sensors.append(sensor)
    else:
        # Fall back to HTML scraping entities for backward compatibility
        # This would need to be implemented based on the old structure
        pass
    
    # Add alarm count sensor
    alarm_count_desc = SensorEntityDescription(
        key="alarm_count",
        name="Alarm Count",
        device_class=None,
        native_unit_of_measurement="alarms",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    
    class AlarmCountSensor(SVKHeatpumpSensor):
        """Sensor for alarm count."""
        
        def __init__(self, coordinator, config_entry_id):
            super().__init__(coordinator, "alarm_count", 0, config_entry_id)
            self.entity_description = alarm_count_desc
        
        @property
        def unique_id(self) -> str:
            """Return unique ID for sensor."""
            return f"{self._config_entry_id}_alarm_count"
        
        @property
        def native_value(self) -> int:
            """Return the number of active alarms."""
            if self.coordinator.data:
                alarm_summary = self.coordinator.get_alarm_summary()
                return alarm_summary.get("count", 0)
            return 0
    
    if "alarm_count" in enabled_entities:
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
    
    class LastUpdateSensor(SVKHeatpumpSensor):
        """Sensor for last update timestamp."""
        
        def __init__(self, coordinator, config_entry_id):
            super().__init__(coordinator, "last_update_sensor", 0, config_entry_id)
            self.entity_description = last_update_desc
        
        @property
        def unique_id(self) -> str:
            """Return unique ID for sensor."""
            return f"{self._config_entry_id}_last_update_sensor"
        
        @property
        def native_value(self) -> Any:
            """Return the last update timestamp."""
            if self.coordinator.data:
                return self.coordinator.data.get("last_update")
            return None
    
    if "last_update_sensor" in enabled_entities:
        last_update_sensor = LastUpdateSensor(coordinator, config_entry.entry_id)
        sensors.append(last_update_sensor)
    
    if sensors:
        async_add_entities(sensors, True)