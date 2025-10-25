"""Number platform for SVK Heatpump integration."""
import logging
from typing import Any, Optional

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .compat import DISABLED_INTEGRATION

from . import const
from . import coordinator

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator


def _get_constants():
    """Lazy import of constants to prevent blocking during async setup."""
    from .const import ID_MAP, DEFAULT_ENABLED_ENTITIES
    return ID_MAP, DEFAULT_ENABLED_ENTITIES

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


class SVKHeatpumpNumber(SVKHeatpumpBaseEntity, NumberEntity):
    """Representation of a SVK Heatpump number entity."""
    
    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        entity_id: int,
        config_entry_id: str,
        min_value: float,
        max_value: float,
        step: float,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, config_entry_id)
        self._entity_key = entity_key
        self._entity_id = entity_id
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._attr_entity_registry_enabled_default = enabled_by_default
        
        _LOGGER.debug("Creating number entity: %s (ID: %s, range: %s-%s, step: %s, enabled_by_default: %s)",
                     entity_key, entity_id, min_value, max_value, step, enabled_by_default)
        
        # Get entity info from ID_MAP (5-element structure)
        ID_MAP, _ = _get_constants()
        entity_info = ID_MAP.get(entity_id, ("", "", None, None, ""))
        self._entity_key, self._unit, self._device_class, self._state_class, self._original_name = entity_info
        
        # Create entity description
        device_class = None
        if self._device_class == "temperature":
            device_class = NumberDeviceClass.TEMPERATURE
        
        # Use original_name for friendly display name if available
        friendly_name = self._original_name.replace("_", " ").title() if self._original_name else self._entity_key.replace("_", " ").title()
        
        # Set entity category based on entity definition
        entity_category = None
        from .const import NUMBER_ENTITIES
        if self._entity_key in NUMBER_ENTITIES and NUMBER_ENTITIES[self._entity_key].get("entity_category"):
            entity_category = getattr(EntityCategory, NUMBER_ENTITIES[self._entity_key]["entity_category"].upper())
        
        self.entity_description = NumberEntityDescription(
            key=self._entity_key,
            name=friendly_name,
            native_min_value=self._min_value,
            native_max_value=self._max_value,
            native_step=self._step,
            native_unit_of_measurement=self._unit,
            device_class=device_class,
            entity_category=entity_category,
        )
        
        # Set mode to slider for better UX
        self._attr_mode = NumberMode.SLIDER
    
    @property
    def unique_id(self) -> str:
        """Return unique ID for number entity."""
        return f"{self._config_entry_id}_{self._entity_id}"
    
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the current value."""
        value = self.coordinator.get_entity_value(self._entity_key)
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning("Could not convert %s value '%s' to float", self._entity_key, value)
        return None
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        last_update_success = self.coordinator.last_update_success
        writes_enabled = self.coordinator.config_entry.options.get("enable_writes", False)
        entity_available = self.coordinator.is_entity_available(self._entity_key)
        is_available = last_update_success and writes_enabled and entity_available
        
        _LOGGER.debug("Number %s availability: %s (last_update_success: %s, writes_enabled: %s, entity_available: %s)",
                     self._entity_key, is_available, last_update_success, writes_enabled, entity_available)
        return is_available
    
    async def async_set_native_value(self, value: float) -> None:
        """Set a new value."""
        if not self.coordinator.config_entry.options.get("enable_writes", False):
            _LOGGER.warning("Write controls are disabled for %s", self._entity_key)
            raise ValueError("Write controls are disabled in options")
        
        # Validate value is within bounds
        if value < self.native_min_value or value > self.native_max_value:
            raise ValueError(
                f"Value {value} is outside the valid range "
                f"({self.native_min_value} - {self.native_max_value})"
            )
        
        # Set the new value
        success = await self.coordinator.async_set_parameter(self._entity_key, value)
        
        if not success:
            _LOGGER.error("Failed to set %s to %s", self._entity_key, value)
            raise ValueError(f"Failed to set {self._entity_key} to {value}")
        
        _LOGGER.info("Successfully set %s to %s", self._entity_key, value)


class SVKHeatpumpHotWaterSetpoint(SVKHeatpumpNumber):
    """Number entity for hot water setpoint with additional validation."""
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes for hot water setpoint."""
        attributes = {}
        
        if self.coordinator.data:
            # Add current tank temperature
            tank_temp = self.coordinator.data.get("water_tank_temp")
            if tank_temp is not None:
                attributes["current_tank_temperature"] = tank_temp
            
            # Add heating status
            heatpump_state = self.coordinator.data.get("heatpump_state")
            if heatpump_state:
                attributes["heatpump_state"] = heatpump_state
            
            # Add heating setpoint for comparison
            heating_setpoint = self.coordinator.data.get("heating_setpoint")
            if heating_setpoint is not None:
                attributes["heating_setpoint"] = heating_setpoint
        
        return attributes


class SVKHeatpumpRoomSetpoint(SVKHeatpumpNumber):
    """Number entity for room setpoint with additional validation."""
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes for room setpoint."""
        attributes = {}
        
        if self.coordinator.data:
            # Add current room temperature
            room_temp = self.coordinator.data.get("room_temp")
            if room_temp is not None:
                attributes["current_room_temperature"] = room_temp
            
            # Add ambient temperature
            ambient_temp = self.coordinator.data.get("ambient_temp")
            if ambient_temp is not None:
                attributes["ambient_temperature"] = ambient_temp
            
            # Add heating status
            heatpump_state = self.coordinator.data.get("heatpump_state")
            if heatpump_state:
                attributes["heatpump_state"] = heatpump_state
        
        return attributes


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up SVK Heatpump number entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    _LOGGER.info("Setting up SVK Heatpump number entities for entry %s", config_entry.entry_id)
    _LOGGER.info("Coordinator is_json_client: %s", coordinator.is_json_client)
    
    number_entities = []
    
    # Create number entities based on ID_MAP for JSON API
    if coordinator.is_json_client:
        # Get constants using lazy import
        ID_MAP, DEFAULT_ENABLED_ENTITIES = _get_constants()
        
        # Create all possible entities from ID_MAP
        for entity_id, (entity_key, unit, device_class, state_class, original_name) in ID_MAP.items():
            # Only include writable setpoint entities
            if entity_key in ["heating_setpoint", "hot_water_setpoint", "room_setpoint"]:
                # Check if this entity should be enabled by default
                enabled_by_default = entity_id in DEFAULT_ENABLED_ENTITIES
                
                # Set min/max values based on entity type
                if entity_key == "hot_water_setpoint":
                    min_value, max_value, step = 40, 65, 1
                    sensor_class = SVKHeatpumpHotWaterSetpoint
                elif entity_key == "room_setpoint":
                    min_value, max_value, step = 10, 30, 1
                    sensor_class = SVKHeatpumpRoomSetpoint
                elif entity_key == "heating_setpoint":
                    min_value, max_value, step = 10, 35, 1
                    sensor_class = SVKHeatpumpNumber
                else:
                    min_value, max_value, step = 0, 100, 1
                    sensor_class = SVKHeatpumpNumber
                
                number_entity = sensor_class(
                    coordinator,
                    entity_key,
                    entity_id,
                    config_entry.entry_id,
                    min_value,
                    max_value,
                    step,
                    enabled_by_default=enabled_by_default
                )
                
                number_entities.append(number_entity)
                _LOGGER.debug("Added number entity: %s (ID: %s, enabled_by_default: %s)",
                             entity_key, entity_id, enabled_by_default)
    else:
        # Fall back to HTML scraping entities for backward compatibility
        # This would need to be implemented based on the old structure
        pass
    
    # Add additional number entities for monitoring (read-only)
    heating_setpoint_desc = NumberEntityDescription(
        key="heating_setpoint_monitor",
        name="Heating Set Point",
        native_min_value=10,
        native_max_value=35,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
    )
    
    class HeatingSetpointMonitor(SVKHeatpumpBaseEntity, NumberEntity):
        """Read-only monitor for heating setpoint."""
        _attr_entity_registry_enabled_default = False
        
        def __init__(self, coordinator, config_entry_id):
            super().__init__(coordinator, config_entry_id)
            self.entity_description = heating_setpoint_desc
        
        @property
        def unique_id(self) -> str:
            """Return unique ID for number entity."""
            return f"{self._config_entry_id}_heating_setpoint_monitor"
        
        @property
        def available(self) -> bool:
            """This monitor should be available when data is present."""
            return (
                self.coordinator.last_update_success
                and self.coordinator.is_entity_available("heating_setpoint")
            )
        
        async def async_set_native_value(self, value: float) -> None:
            """Prevent setting value on monitor."""
            raise ValueError("This is a read-only monitor entity")
    
    # Heating setpoint monitor is disabled by default
    heating_monitor = HeatingSetpointMonitor(coordinator, config_entry.entry_id)
    number_entities.append(heating_monitor)
    
    # Add compressor speed monitor (if available)
    compressor_speed_desc = NumberEntityDescription(
        key="compressor_speed_monitor",
        name="Compressor Speed Monitor",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        device_class=None,
    )
    
    class CompressorSpeedMonitor(SVKHeatpumpBaseEntity, NumberEntity):
        """Read-only monitor for compressor speed."""
        _attr_entity_registry_enabled_default = False
        
        def __init__(self, coordinator, config_entry_id):
            super().__init__(coordinator, config_entry_id)
            self.entity_description = compressor_speed_desc
        
        @property
        def unique_id(self) -> str:
            """Return unique ID for number entity."""
            return f"{self._config_entry_id}_compressor_speed_monitor"
        
        @property
        def native_value(self) -> Optional[float]:
            """Return the current compressor speed percentage."""
            value = self.coordinator.get_entity_value("compressor_speed_pct")
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    pass
            return None
        
        @property
        def available(self) -> bool:
            """This monitor should be available when data is present."""
            return (
                self.coordinator.last_update_success
                and self.coordinator.is_entity_available("compressor_speed_pct")
            )
        
        async def async_set_native_value(self, value: float) -> None:
            """Prevent setting value on monitor."""
            raise ValueError("This is a read-only monitor entity")
    
    # Compressor speed monitor is disabled by default
    compressor_monitor = CompressorSpeedMonitor(coordinator, config_entry.entry_id)
    number_entities.append(compressor_monitor)
    
    _LOGGER.info("Created %d number entities", len(number_entities))
    if number_entities:
        async_add_entities(number_entities, True)