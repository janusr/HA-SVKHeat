"""Select platform for SVK Heatpump integration."""
import logging
from typing import Any, List

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityRegistry
from homeassistant.helpers.entity_registry import DISABLED_INTEGRATION
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import const
from . import coordinator

# Import specific items from modules
from .const import DOMAIN, ID_MAP, SEASON_MODES_REVERSE, DEFAULT_ENABLED_ENTITIES
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)


class SVKHeatpumpSelect(CoordinatorEntity, SelectEntity):
    """Representation of a SVK Heatpump select entity."""
    
    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        entity_id: int,
        config_entry_id: str,
        writable: bool = False,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id
        self._entity_key = entity_key
        self._entity_id = entity_id
        self._writable = writable
        self._attr_enabled_by_default = enabled_by_default
        
        # Get entity info from ID_MAP (5-element structure)
        entity_info = ID_MAP.get(entity_id, ("", "", None, None, ""))
        self._entity_key, self._unit, self._device_class, self._state_class, self._original_name = entity_info
        
        # Set options based on entity type
        options = []
        mappings = {}
        
        if entity_key == "season_mode":
            options = ["Summer", "Winter", "Auto"]
            mappings = SEASON_MODES_REVERSE
        elif entity_key == "heatpump_state":
            # This is read-only, but we'll include options for completeness
            options = ["Off", "Ready", "Start up", "Heating", "Hot water",
                      "El heating", "Defrost", "Drip delay", "Total stop",
                      "Pump exercise", "Forced running", "Manual"]
        
        # Use original_name for friendly display name if available
        friendly_name = self._original_name.replace("_", " ").title() if self._original_name else self._entity_key.replace("_", " ").title()
        
        self.entity_description = SelectEntityDescription(
            key=self._entity_key,
            name=friendly_name,
            options=options,
        )
        
        # Store mappings for reverse lookup
        self._mappings = mappings
    
    @property
    def unique_id(self) -> str:
        """Return unique ID for select entity."""
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
    def current_option(self) -> str:
        """Return the current selected option."""
        value = self.coordinator.get_entity_value(self._entity_key)
        if value is not None:
            # Map the internal value to the display option
            for option, mapped_value in self._mappings.items():
                if mapped_value == value:
                    return option
            # If no mapping found, return the raw value
            return str(value)
        return None
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        
        # Check if writes are enabled for writable entities
        if self._writable:
            return (
                self.coordinator.config_entry.options.get("enable_writes", False)
                and self.coordinator.is_entity_available(self._entity_key)
            )
        
        return self.coordinator.is_entity_available(self._entity_key)
    
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if not self._writable:
            _LOGGER.warning("Attempted to write to read-only select entity: %s", self._entity_key)
            raise ValueError("This select entity is read-only")
        
        if not self.coordinator.config_entry.options.get("enable_writes", False):
            _LOGGER.warning("Write controls are disabled for %s", self._entity_key)
            raise ValueError("Write controls are disabled in options")
        
        # Map the option to the internal value
        internal_value = self._mappings.get(option, option)
        
        # Set the new value
        success = await self.coordinator.async_set_parameter(self._entity_key, internal_value)
        
        if not success:
            _LOGGER.error("Failed to set %s to %s", self._entity_key, internal_value)
            raise ValueError(f"Failed to set {self._entity_key} to {option}")
        
        _LOGGER.info("Successfully set %s to %s", self._entity_key, internal_value)


class SVKHeatpumpHeatpumpStateSelect(SVKHeatpumpSelect):
    """Select entity for heat pump state (read-only)."""
    
    @property
    def available(self) -> bool:
        """Heat pump state should always be available when data is present."""
        return self.coordinator.last_update_success and bool(self.coordinator.data)


class SVKHeatpumpSeasonModeSelect(SVKHeatpumpSelect):
    """Select entity for season mode (writable)."""
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes for season mode."""
        attributes = {}
        
        if self.coordinator.data:
            # Add current season information if available
            system_status = self.coordinator.get_system_status()
            attributes.update(system_status)
        
        return attributes


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up SVK Heatpump select entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    entity_registry = hass.helpers.entity_registry.async_get(hass)
    
    select_entities = []
    
    # Create select entities based on ID_MAP for JSON API
    if coordinator.is_json_client:
        # Create all possible entities from DEFAULT_IDS
        for entity_id, (entity_key, unit, device_class, state_class, original_name) in ID_MAP.items():
            # Only include select entities
            if entity_key in ["season_mode", "heatpump_state"]:
                # Check if this entity should be enabled by default
                enabled_by_default = entity_id in DEFAULT_ENABLED_ENTITIES
                
                # Determine if writable
                writable = (entity_key == "season_mode" and
                           coordinator.config_entry.options.get("enable_writes", False))
                
                # Choose the appropriate class based on the entity type
                if entity_key == "heatpump_state":
                    sensor_class = SVKHeatpumpHeatpumpStateSelect
                elif entity_key == "season_mode":
                    sensor_class = SVKHeatpumpSeasonModeSelect
                else:
                    sensor_class = SVKHeatpumpSelect
                
                select_entity = sensor_class(
                    coordinator,
                    entity_key,
                    entity_id,
                    config_entry.entry_id,
                    writable,
                    enabled_by_default=enabled_by_default
                )
                
                # Get the entity registry entry
                entity_id_str = f"{config_entry.entry_id}_{entity_id}"
                registry_entry = entity_registry.async_get(entity_id_str)
                
                # If entity exists in registry but should be disabled by default and isn't already disabled, disable it
                if registry_entry and not enabled_by_default and registry_entry.disabled_by is None:
                    entity_registry.async_update_entity(entity_id_str, disabled_by=DISABLED_INTEGRATION)
                
                # Only add enabled entities to the platform
                if enabled_by_default or (registry_entry and registry_entry.disabled_by is None):
                    select_entities.append(select_entity)
    else:
        # Fall back to HTML scraping entities for backward compatibility
        # This would need to be implemented based on the old structure
        pass
    
    # Add additional select entities for system status
    system_status_desc = SelectEntityDescription(
        key="system_status",
        name="System Status",
        options=[
            "Off",
            "Standby",
            "Active",
            "Alarm",
            "Unknown"
        ],
    )
    
    class SystemStatusSelect(SVKHeatpumpSelect):
        """Select entity for overall system status."""
        
        def __init__(self, coordinator, config_entry_id, enabled_by_default: bool = True):
            super().__init__(coordinator, "system_status", 0, config_entry_id, False, enabled_by_default)
            self.entity_description = system_status_desc
        
        @property
        def unique_id(self) -> str:
            """Return unique ID for select entity."""
            return f"{self._config_entry_id}_system_status"
        
        @property
        def current_option(self) -> str:
            """Return the current system status."""
            if self.coordinator.data:
                system_status = self.coordinator.get_system_status()
                return system_status.get("status", "Unknown")
            return "Unknown"
        
        @property
        def available(self) -> bool:
            """System status should always be available when data is present."""
            return self.coordinator.last_update_success and bool(self.coordinator.data)
    
    # System status entity is enabled by default
    system_status_entity = SystemStatusSelect(
        coordinator,
        config_entry.entry_id,
        enabled_by_default=True
    )
    select_entities.append(system_status_entity)
    
    if select_entities:
        async_add_entities(select_entities, True)