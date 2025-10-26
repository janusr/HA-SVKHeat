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
from .entity_base import SVKBaseEntity
from .catalog import NUMBER_ENTITIES, ENTITIES


def _get_constants():
    """Lazy import of constants to prevent blocking during async setup."""
    from .const import ID_MAP, DEFAULT_ENABLED_ENTITIES
    return ID_MAP, DEFAULT_ENABLED_ENTITIES

_LOGGER = logging.getLogger(__name__)


class SVKNumber(SVKHeatpumpBaseEntity, NumberEntity):
    """Representation of a SVK Heatpump number entity."""
    
    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the number entity."""
        # Extract group key from entity key (first part before underscore)
        group_key = entity_key.split("_")[0]
        
        # Get entity info from catalog
        entity_info = ENTITIES.get(entity_key, {})
        name = entity_info.get("name", entity_key.replace("_", " ").title())
        data_type = entity_info.get("data_type", "")
        unit = entity_info.get("unit", "")
        category = entity_info.get("category", "")
        min_value = entity_info.get("min_value", 0)
        max_value = entity_info.get("max_value", 100)
        step = entity_info.get("step", 1)
        
        # Initialize SVKHeatpumpBaseEntity (which inherits from CoordinatorEntity)
        super().__init__(coordinator, config_entry_id)
        
        # Initialize additional attributes
        self._entity_key = entity_key
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._group_key = group_key  # For unique_id property
        
        _LOGGER.debug("Creating number entity: %s (group: %s, min: %s, max: %s, step: %s, unit: %s)",
                     entity_key, group_key, min_value, max_value, step, unit)
        
        # Map data types to Home Assistant device classes
        device_class = None
        if data_type == "temperature":
            device_class = NumberDeviceClass.TEMPERATURE
        
        # Set entity category based on category
        entity_category = None
        if category == "Configuration":
            entity_category = EntityCategory.CONFIG
        elif category == "Settings":
            entity_category = EntityCategory.CONFIG
        
        # Create entity description
        self.entity_description = NumberEntityDescription(
            key=entity_key,
            name=name,
            native_min_value=min_value,
            native_max_value=max_value,
            native_step=step,
            native_unit_of_measurement=unit,
            device_class=device_class,
            entity_category=entity_category,
        )
        
        # Set mode to slider for better UX
        self._attr_mode = NumberMode.SLIDER
    
    @property
    def unique_id(self) -> str:
        """Return unique ID for number entity."""
        return f"{DOMAIN}_{self._group_key}_{self._entity_key}"
    
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


class SVKHeatpumpHotWaterSetpoint(SVKNumber):
    """Number entity for hot water setpoint with additional validation."""
    
    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the hot water setpoint number entity."""
        super().__init__(coordinator, entity_key, config_entry_id, enabled_by_default)
    
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


class SVKHeatpumpRoomSetpoint(SVKNumber):
    """Number entity for room setpoint with additional validation."""
    
    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the room setpoint number entity."""
        super().__init__(coordinator, entity_key, config_entry_id, enabled_by_default)
    
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
    
    # Create number entities based on NUMBER_ENTITIES from catalog
    if coordinator.is_json_client:
        # Create all number entities from catalog
        for entity_key in NUMBER_ENTITIES:
            try:
                # Get entity info from catalog
                entity_info = ENTITIES.get(entity_key, {})
                name = entity_info.get("name", entity_key.replace("_", " ").title())
                category = entity_info.get("category", "")
                access_type = entity_info.get("access_type", "")
                
                # Only include writable entities
                if access_type != "readwrite":
                    _LOGGER.debug("Skipping read-only entity %s", entity_key)
                    continue
                
                # Determine if this entity should be enabled by default
                # For now, enable all number entities from catalog
                enabled_by_default = True
                
                # Create number using new SVKNumber class
                number = SVKNumber(
                    coordinator,
                    entity_key,
                    config_entry.entry_id,
                    enabled_by_default=enabled_by_default
                )
                
                number_entities.append(number)
                _LOGGER.debug("Added number entity: %s (name: %s, enabled_by_default: %s)",
                             entity_key, name, enabled_by_default)
            except Exception as err:
                _LOGGER.error("Failed to create number entity %s: %s", entity_key, err)
                # Continue with other entities even if one fails
                continue
    else:
        # Fall back to HTML scraping entities for backward compatibility
        # Create basic entities even if JSON client is not available
        _LOGGER.warning("JSON client not available, creating essential fallback entities")
        
        # Get constants using lazy import
        ID_MAP, DEFAULT_ENABLED_ENTITIES = _get_constants()
        
        # Create all possible entities from ID_MAP
        for entity_id, (entity_key, unit, device_class, state_class, original_name) in ID_MAP.items():
            # Only include writable setpoint entities
            if entity_key in ["heating_setpoint", "hot_water_setpoint", "room_setpoint"]:
                # Check if this entity should be enabled by default
                enabled_by_default = entity_id in DEFAULT_ENABLED_ENTITIES
                
                # Create specialized classes for specific entities
                if entity_key == "hot_water_setpoint":
                    number_entity = SVKHeatpumpHotWaterSetpoint(
                        coordinator,
                        entity_key,
                        config_entry.entry_id,
                        enabled_by_default=enabled_by_default
                    )
                elif entity_key == "room_setpoint":
                    number_entity = SVKHeatpumpRoomSetpoint(
                        coordinator,
                        entity_key,
                        config_entry.entry_id,
                        enabled_by_default=enabled_by_default
                    )
                else:
                    # Use the new SVKNumber class for all other entities
                    number_entity = SVKNumber(
                        coordinator,
                        entity_key,
                        config_entry.entry_id,
                        enabled_by_default=enabled_by_default
                    )
                
                number_entities.append(number_entity)
                _LOGGER.debug("Added number entity: %s (ID: %s, enabled_by_default: %s)",
                             entity_key, entity_id, enabled_by_default)
    
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
            # Initialize SVKHeatpumpBaseEntity (which inherits from CoordinatorEntity)
            super().__init__(coordinator, config_entry_id)
            self._attr_name = "Heating Set Point Monitor"
            self._attr_unique_id = f"{DOMAIN}_system_heating_setpoint_monitor"
            self.entity_description = heating_setpoint_desc
        
        @property
        def native_value(self) -> Optional[float]:
            """Return current heating setpoint value."""
            value = self.coordinator.get_entity_value("heating_setpoint")
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
            # Initialize SVKHeatpumpBaseEntity (which inherits from CoordinatorEntity)
            super().__init__(coordinator, config_entry_id)
            self._attr_name = "Compressor Speed Monitor"
            self._attr_unique_id = f"{DOMAIN}_system_compressor_speed_monitor"
            self.entity_description = compressor_speed_desc
        
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