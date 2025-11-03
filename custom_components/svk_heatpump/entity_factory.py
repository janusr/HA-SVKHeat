"""Entity factory for SVK Heatpump integration using partial function application."""

import functools
import logging
from typing import Any, Dict, List, Optional, Callable, Type

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .catalog import ENTITIES, get_sensor_entities, get_binary_sensor_entities, get_number_entities, get_select_entities, get_switch_entities
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)

# System-level entities that should follow the alarm_count pattern
SYSTEM_LEVEL_ENTITIES = {
    "alarm_count",
    "last_update_sensor", 
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


class SVKEntityFactory:
    """Factory for creating SVK Heatpump entities using partial function application."""
    
    def __init__(self, coordinator: SVKHeatpumpDataCoordinator, config_entry_id: str, hass: Optional[HomeAssistant] = None):
        """Initialize the entity factory.
        
        Args:
            coordinator: The data coordinator
            config_entry_id: The config entry ID
            hass: Home Assistant instance (required for select entities)
        """
        self.coordinator = coordinator
        self.config_entry_id = config_entry_id
        self.hass = hass
        
        # Create platform-specific partial functions
        self._create_sensor = functools.partial(
            self._create_entity_for_platform,
            platform="sensor"
        )
        
        self._create_binary_sensor = functools.partial(
            self._create_entity_for_platform,
            platform="binary_sensor"
        )
        
        self._create_number = functools.partial(
            self._create_entity_for_platform,
            platform="number"
        )
        
        self._create_select = functools.partial(
            self._create_entity_for_platform,
            platform="select"
        )
        
        self._create_switch = functools.partial(
            self._create_entity_for_platform,
            platform="switch"
        )
    
    def create_entities_for_platform(self, platform: str) -> List[Any]:
        """Create all entities for a specific platform.
        
        Args:
            platform: The platform type (sensor, binary_sensor, number, select, switch)
            
        Returns:
            List of created entities
        """
        if platform == "sensor":
            return self._create_sensor_entities()
        elif platform == "binary_sensor":
            return self._create_binary_sensor_entities()
        elif platform == "number":
            return self._create_number_entities()
        elif platform == "select":
            return self._create_select_entities()
        elif platform == "switch":
            return self._create_switch_entities()
        else:
            _LOGGER.error("Unknown platform: %s", platform)
            return []
    
    def _create_sensor_entities(self) -> List[Any]:
        """Create all sensor entities."""
        entities = []
        
        # Create all sensor entities from the catalog
        for entity_key in get_sensor_entities():
            try:
                entity = self._create_sensor(entity_key=entity_key)
                if entity:
                    entities.append(entity)
            except Exception as err:
                _LOGGER.error("Failed to create sensor entity %s: %s", entity_key, err)
                continue
        
        return entities
    
    def _create_binary_sensor_entities(self) -> List[Any]:
        """Create all binary sensor entities."""
        entities = []
        
        # Create all possible entities from ENTITIES
        for entity_key, entity_data in ENTITIES.items():
            # Only process entities that have an ID
            if "id" not in entity_data or entity_data["id"] is None:
                continue
                
            # Only process binary sensor entities
            if entity_data.get("platform") != "binary_sensor":
                continue
                
            try:
                entity = self._create_binary_sensor(entity_key=entity_key)
                if entity:
                    entities.append(entity)
            except Exception as err:
                _LOGGER.error("Failed to create binary sensor entity %s: %s", entity_key, err)
                continue
        
        return entities
    
    def _create_number_entities(self) -> List[Any]:
        """Create all number entities."""
        entities = []
        
        # Create all number entities from catalog
        for entity_key in get_number_entities():
            try:
                entity_info = ENTITIES.get(entity_key, {})
                access_type = entity_info.get("access_type", "")
                
                # Only include writable entities
                if access_type != "readwrite":
                    _LOGGER.debug("Skipping read-only entity %s", entity_key)
                    continue
                
                entity = self._create_number(entity_key=entity_key)
                if entity:
                    entities.append(entity)
            except Exception as err:
                _LOGGER.error("Failed to create number entity %s: %s", entity_key, err)
                continue
        
        return entities
    
    def _create_select_entities(self) -> List[Any]:
        """Create all select entities."""
        entities = []
        
        # Create all select entities from catalog
        for entity_key in get_select_entities():
            try:
                entity_info = ENTITIES.get(entity_key, {})
                access_type = entity_info.get("access_type", "")
                
                # Only include writable entities
                if access_type != "readwrite":
                    _LOGGER.debug("Skipping read-only entity %s", entity_key)
                    continue
                
                entity = self._create_select(entity_key=entity_key)
                if entity:
                    entities.append(entity)
            except Exception as err:
                _LOGGER.error("Failed to create select entity %s: %s", entity_key, err)
                continue
        
        return entities
    
    def _create_switch_entities(self) -> List[Any]:
        """Create all switch entities."""
        entities = []
        
        # Create all switch entities from catalog
        for entity_key in get_switch_entities():
            try:
                entity_info = ENTITIES.get(entity_key, {})
                access_type = entity_info.get("access_type", "")
                
                # Only include writable entities
                if access_type != "readwrite":
                    _LOGGER.debug("Skipping read-only entity %s", entity_key)
                    continue
                
                entity = self._create_switch(entity_key=entity_key)
                if entity:
                    entities.append(entity)
            except Exception as err:
                _LOGGER.error("Failed to create switch entity %s: %s", entity_key, err)
                continue
        
        return entities
    
    def _create_entity_for_platform(
        self,
        platform: str,
        entity_key: str,
        entity_id: Optional[int] = None,
        **kwargs
    ) -> Optional[Any]:
        """Create an entity for a specific platform.
        
        Args:
            platform: The platform type
            entity_key: The entity key
            entity_id: The entity ID
            **kwargs: Additional platform-specific parameters
            
        Returns:
            The created entity or None if creation failed
        """
        try:
            # Get entity info from catalog
            entity_info = ENTITIES.get(entity_key, {})
            
            # Determine if entity should be enabled by default
            if entity_id:
                enabled_by_default = self.coordinator.is_entity_enabled(entity_id)
            else:
                entity_id_from_info = entity_info.get("id")
                enabled_by_default = self.coordinator.is_entity_enabled(entity_id_from_info) if entity_id_from_info else False
            
            # Import the appropriate entity class
            if platform == "sensor":
                from .sensor import SVKSensor, SVKHeatpumpSensor
                return self._create_sensor_entity(
                    entity_key, entity_id, enabled_by_default, SVKSensor, SVKHeatpumpSensor, **kwargs
                )
            elif platform == "binary_sensor":
                from .binary_sensor import SVKHeatpumpBinarySensor, SVKHeatpumpAlarmBinarySensor
                return self._create_binary_sensor_entity(
                    entity_key, entity_id, enabled_by_default, SVKHeatpumpBinarySensor, SVKHeatpumpAlarmBinarySensor, **kwargs
                )
            elif platform == "number":
                from .number import SVKNumber, SVKHeatpumpNumber, SVKHeatpumpHotWaterSetpoint, SVKHeatpumpRoomSetpoint
                return self._create_number_entity(
                    entity_key, entity_id, enabled_by_default, SVKNumber, SVKHeatpumpNumber, 
                    SVKHeatpumpHotWaterSetpoint, SVKHeatpumpRoomSetpoint, **kwargs
                )
            elif platform == "select":
                from .select import SVKSelect, SVKHeatpumpSelect
                return self._create_select_entity(
                    entity_key, entity_id, enabled_by_default, SVKSelect, SVKHeatpumpSelect, **kwargs
                )
            elif platform == "switch":
                from .switch import SVKSwitch, SVKHeatpumpSwitch
                return self._create_switch_entity(
                    entity_key, entity_id, enabled_by_default, SVKSwitch, SVKHeatpumpSwitch, **kwargs
                )
            else:
                _LOGGER.error("Unknown platform: %s", platform)
                return None
                
        except Exception as err:
            _LOGGER.error("Failed to create entity %s for platform %s: %s", entity_key, platform, err)
            return None
    
    def _create_sensor_entity(
        self, 
        entity_key: str, 
        entity_id: Optional[int], 
        enabled_by_default: bool,
        svk_sensor_class: Type,
        svk_heatpump_sensor_class: Type,
        **kwargs
    ) -> Any:
        """Create a sensor entity."""
        return svk_sensor_class(
            self.coordinator,
            entity_key,
            self.config_entry_id,
            enabled_by_default=enabled_by_default,
        )
    
    def _create_binary_sensor_entity(
        self, 
        entity_key: str, 
        entity_id: Optional[int], 
        enabled_by_default: bool,
        svk_binary_sensor_class: Type,
        svk_alarm_binary_sensor_class: Type,
        **kwargs
    ) -> Any:
        """Create a binary sensor entity."""
        # Use alarm binary sensor class for alarm_active entity
        if entity_key == "alarm_active":
            return svk_alarm_binary_sensor_class(
                self.coordinator,
                entity_key,
                self.config_entry_id,
                enabled_by_default=enabled_by_default,
            )
        else:
            return svk_binary_sensor_class(
                self.coordinator,
                entity_key,
                self.config_entry_id,
                enabled_by_default=enabled_by_default,
                entity_id=entity_id,
            )
    
    def _create_number_entity(
        self, 
        entity_key: str, 
        entity_id: Optional[int], 
        enabled_by_default: bool,
        svk_number_class: Type,
        svk_heatpump_number_class: Type,
        svk_hotwater_setpoint_class: Type,
        svk_room_setpoint_class: Type,
        **kwargs
    ) -> Any:
        """Create a number entity."""
        return svk_number_class(
            self.coordinator,
            entity_key,
            self.config_entry_id,
            enabled_by_default=enabled_by_default,
        )
    
    def _create_select_entity(
        self, 
        entity_key: str, 
        entity_id: Optional[int], 
        enabled_by_default: bool,
        svk_select_class: Type,
        svk_heatpump_select_class: Type,
        **kwargs
    ) -> Any:
        """Create a select entity."""
        return svk_select_class(
            self.coordinator,
            entity_key,
            self.config_entry_id,
            self.hass,  # Pass hass for translation support
            enabled_by_default=enabled_by_default,
        )
    
    def _create_switch_entity(
        self, 
        entity_key: str, 
        entity_id: Optional[int], 
        enabled_by_default: bool,
        svk_switch_class: Type,
        svk_heatpump_switch_class: Type,
        **kwargs
    ) -> Any:
        """Create a switch entity."""
        return svk_switch_class(
            self.coordinator,
            entity_key,
            self.config_entry_id,
            enabled_by_default=enabled_by_default,
        )


def create_entities_for_platform(
    coordinator: SVKHeatpumpDataCoordinator,
    config_entry_id: str,
    platform: str,
    hass: Optional[HomeAssistant] = None
) -> List[Any]:
    """Generic function to create entities for a platform.
    
    Args:
        coordinator: The data coordinator
        config_entry_id: The config entry ID
        platform: The platform type
        hass: Home Assistant instance (required for select entities)
        
    Returns:
        List of created entities
    """
    factory = SVKEntityFactory(coordinator, config_entry_id, hass)
    return factory.create_entities_for_platform(platform)