"""Binary sensor platform for SVK Heatpump integration."""
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN, ID_MAP
from ..coordinator import SVKHeatpumpDataCoordinator


class SVKHeatpumpBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a SVK Heatpump binary sensor."""
    
    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        entity_id: int,
        config_entry_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id
        self._entity_key = entity_key
        self._entity_id = entity_id
        
        # Get entity info from ID_MAP (5-element structure)
        entity_info = ID_MAP.get(entity_id, ("", "", None, None, ""))
        self._entity_key, self._unit, self._device_class, self._state_class, self._original_name = entity_info
        
        # Create entity description
        device_class = None
        if self._entity_key == "alarm_active":
            device_class = BinarySensorDeviceClass.PROBLEM
        elif entity_id in [222, 223, 224, 225]:  # Digital outputs
            device_class = BinarySensorDeviceClass.RUNNING
        
        # Use original_name for friendly display name if available
        friendly_name = self._original_name.replace("_", " ").title() if self._original_name else self._entity_key.replace("_", " ").title()
        
        self.entity_description = BinarySensorEntityDescription(
            key=self._entity_key,
            name=friendly_name,
            device_class=device_class,
        )
    
    @property
    def unique_id(self) -> str:
        """Return unique ID for binary sensor."""
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
        return self.coordinator.last_update_success and self.coordinator.is_entity_available(self._entity_key)


class SVKHeatpumpAlarmBinarySensor(SVKHeatpumpBinarySensor):
    """Binary sensor for alarm status with additional attributes."""
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
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
    
    # Get enabled entities from coordinator
    enabled_entities = coordinator.get_enabled_entities(config_entry)
    
    binary_sensors = []
    
    # Create binary sensors based on ID_MAP for JSON API
    if coordinator.is_json_client:
        for entity_id, (entity_key, unit, device_class, state_class, original_name) in ID_MAP.items():
            # Include alarm_active entity
            if entity_key == "alarm_active":
                # Check if this entity should be enabled
                if entity_key in enabled_entities:
                    # Use the alarm binary sensor class for additional attributes
                    binary_sensor = SVKHeatpumpAlarmBinarySensor(
                        coordinator,
                        entity_key,
                        entity_id,
                        config_entry.entry_id
                    )
                    binary_sensors.append(binary_sensor)
            
            # Include digital outputs (IDs 222-225)
            elif entity_id in [222, 223, 224, 225]:
                # Check if this entity should be enabled
                if entity_key in enabled_entities:
                    binary_sensor = SVKHeatpumpBinarySensor(
                        coordinator,
                        entity_key,
                        entity_id,
                        config_entry.entry_id
                    )
                    binary_sensors.append(binary_sensor)
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
    
    class SystemActiveBinarySensor(SVKHeatpumpBinarySensor):
        """Binary sensor for system active state."""
        
        def __init__(self, coordinator, config_entry_id):
            super().__init__(coordinator, "system_active", 0, config_entry_id)
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
                    "heating", "hot_water", "el_heating", "defrost",
                    "start_up", "forced_running"
                ]
            return False
    
    if "system_active" in enabled_entities:
        system_sensor = SystemActiveBinarySensor(coordinator, config_entry.entry_id)
        binary_sensors.append(system_sensor)
    
    # Add online status binary sensor
    online_desc = BinarySensorEntityDescription(
        key="online_status",
        name="Online Status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    )
    
    class OnlineStatusBinarySensor(SVKHeatpumpBinarySensor):
        """Binary sensor for online status."""
        
        def __init__(self, coordinator, config_entry_id):
            super().__init__(coordinator, "online_status", 0, config_entry_id)
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
    
    if "online_status" in enabled_entities:
        online_sensor = OnlineStatusBinarySensor(coordinator, config_entry.entry_id)
        binary_sensors.append(online_sensor)
    
    if binary_sensors:
        async_add_entities(binary_sensors, True)