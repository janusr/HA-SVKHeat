"""Select platform for SVK Heatpump integration."""

import logging
from typing import Any

try:
    from homeassistant.components.select import SelectEntity, SelectEntityDescription
except ImportError:
    # Fallback for older Home Assistant versions
    from homeassistant.components.select import SelectEntity
    # For older versions, create a fallback EntityDescription
    from dataclasses import dataclass
    
    @dataclass
    class SelectEntityDescription:
        """Fallback SelectEntityDescription for older HA versions."""
        key: str
        name: str | None = None
        translation_key: str | None = None
        options: list | None = None
        icon: str | None = None
        entity_category: str | None = None
        enabled_default: bool = True
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .entity_base import SVKBaseEntity

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)

# Lazy loading of catalog functions to avoid blocking imports
def _lazy_import_catalog():
    """Lazy import catalog functions to avoid blocking imports."""
    global ENTITIES, get_select_entities, SELECT_ENTITIES, DEFAULT_ENABLED_ENTITIES
    if 'ENTITIES' not in globals():
        from .catalog import (
            ENTITIES,
            get_select_entities,
            SELECT_ENTITIES,
            DEFAULT_ENABLED_ENTITIES,
        )

def _get_constants() -> tuple[dict[str, dict[str, Any]], dict[str, str], list[int]]:
    """Lazy import of constants to prevent blocking during async setup."""
    _lazy_import_catalog()
    from .const import SEASON_MODES_REVERSE
    return ENTITIES, SEASON_MODES_REVERSE, DEFAULT_ENABLED_ENTITIES


_LOGGER = logging.getLogger(__name__)


class SVKSelect(SVKBaseEntity, SelectEntity):
    """Representation of a SVK Heatpump select entity."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        config_entry_id: str,
        hass: HomeAssistant,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize select entity."""
        # Initialize SVKBaseEntity
        super().__init__(
            coordinator,
            config_entry_id,
            entity_key,
            entity_key,
            enabled_by_default=enabled_by_default
        )
        self._hass = hass  # Store hass for translation

        # Get entity info from catalog
        entity_info = self._get_entity_info()
        data_type = entity_info.get("data_type", "")
        category = entity_info.get("category", "")

        _LOGGER.debug(
            "Creating select entity: %s (group: %s, enabled_by_default: %s)",
            entity_key,
            self._group_key,
            enabled_by_default,
        )

        # Set options based on entity type
        options = []
        mappings = {}

        # Default options for enum type
        if data_type == "enum":
            # Try to get options from entity info or use defaults based on entity key
            if entity_key == "defrost_defrost_mode":
                options = ["Off", "Manual", "Automatic"]
                mappings = {"Off": "0", "Manual": "1", "Automatic": "2"}
            elif entity_key == "heating_heating_source":
                options = ["Heat pump", "Electric", "Manual"]
                mappings = {"Heat pump": "0", "Electric": "1", "Manual": "2"}
            elif entity_key == "heating_heatspctrl_type":
                options = ["Off", "Curve", "Room", "Outdoor"]
                mappings = {"Off": "0", "Curve": "1", "Room": "2", "Outdoor": "3"}
            elif entity_key == "heatpump_heating_ctrlmode":
                options = ["Off", "Room", "Outdoor", "Curve"]
                mappings = {"Off": "0", "Room": "1", "Outdoor": "2", "Curve": "3"}
            elif entity_key == "heatpump_cprcontrol_cprmode":
                options = ["Off", "Standard", "Eco", "Comfort"]
                mappings = {"Off": "0", "Standard": "1", "Eco": "2", "Comfort": "3"}
            elif entity_key == "heatpump_coldpump_mode":
                options = ["Off", "Auto", "Manual"]
                mappings = {"Off": "0", "Auto": "1", "Manual": "2"}
            elif entity_key == "hotwater_hotwater_source":
                options = ["Heat pump", "Electric", "Solar"]
                mappings = {"Heat pump": "0", "Electric": "1", "Solar": "2"}
            elif entity_key == "service_parameters_displaymode":
                options = ["Basic", "Advanced", "Service"]
                mappings = {"Basic": "0", "Advanced": "1", "Service": "2"}
            elif entity_key == "solar_solarpanel_sensorselect":
                options = ["Internal", "External"]
                mappings = {"Internal": "0", "External": "1"}
            elif entity_key == "user_user_language":
                # Use translation keys that will be resolved by Home Assistant
                # These keys correspond to the translations in en.json and da.json
                options = ["0", "1", "2", "3", "4", "5", "6", "7", "8"]
                mappings = {
                    "0": "0",
                    "1": "1",
                    "2": "2",
                    "3": "3",
                    "4": "4",
                    "5": "5",
                    "6": "6",
                    "7": "7",
                    "8": "8"
                }
            else:
                # Default options for unknown enum
                options = ["Option 1", "Option 2", "Option 3"]
                mappings = {"Option 1": "0", "Option 2": "1", "Option 3": "2"}

        # Set icon based on entity name or group
        icon = None
        if "mode" in entity_key.lower():
            icon = "mdi:cog"  # For mode settings
        elif "source" in entity_key.lower():
            icon = "mdi:source"  # For source selection
        elif "display" in entity_key.lower():
            icon = "mdi:monitor"  # For display settings
        elif "language" in entity_key.lower():
            icon = "mdi:translate"  # For language selection
        elif "sensor" in entity_key.lower():
            icon = "mdi:sensor"  # For sensor selection

        # Set entity category based on category
        entity_category = None
        if category == "Configuration":
            entity_category = EntityCategory.CONFIG
        elif category == "Settings":
            entity_category = EntityCategory.CONFIG

        # Create entity description
        self.entity_description = SelectEntityDescription(
            key=self._entity_key,
            translation_key=self._entity_key,
            name=None,
            options=options,
            icon=icon,
            entity_category=entity_category,
        )
        
        # Store translation key for language options
        self._translation_key = f"select.{entity_key}"

        # Store mappings for reverse lookup
        self._mappings = mappings


    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        value = self._get_entity_value()
        if value is not None:
            _LOGGER.debug(
                "Select %s: raw value from API: %s (type: %s)",
                self._entity_key,
                value,
                type(value).__name__
            )
            
            # Convert value to string for consistent comparison
            str_value = str(value)
            
            # First try to map using the mappings dictionary
            if self._mappings:
                for option, mapped_value in self._mappings.items():
                    if str(mapped_value) == str_value:
                        _LOGGER.debug(
                            "Select %s: mapped value %s to option %s",
                            self._entity_key,
                            str_value,
                            option
                        )
                        return option
            
            # If no mapping found or mappings empty, try to match directly with options
            options = self.options
            if options:
                # Try direct match with string value
                if str_value in options:
                    _LOGGER.debug(
                        "Select %s: direct match found for value %s",
                        self._entity_key,
                        str_value
                    )
                    return str_value
                
                # For numeric values, try to match by index
                if str_value.isdigit():
                    index = int(str_value)
                    if 0 <= index < len(options):
                        _LOGGER.debug(
                            "Select %s: mapped index %d to option %s",
                            self._entity_key,
                            index,
                            options[index]
                        )
                        return options[index]
            
            # If still no match, return the raw value as string
            _LOGGER.debug(
                "Select %s: no mapping found, returning raw value %s",
                self._entity_key,
                str_value
            )
            return str_value
        return None
    
    @property
    def options(self) -> list[str]:
        """Return a list of available options."""
        # For user_user_language, we need to translate the options
        if self._entity_key == "user_user_language":
            return self._get_translated_language_options()
        # Ensure we always return a list of strings
        return self.entity_description.options or []
    
    def _get_translated_language_options(self) -> list[str]:
        """Get translated language options based on current HA language."""
        # Get the current language from Home Assistant
        language = self._hass.config.language
        
        # Map of numeric values to translation keys
        translation_keys = ["0", "1", "2", "3", "4", "5", "6", "7", "8"]
        
        # Get the translated values using Home Assistant's translation system
        try:
            translations = self._hass.components.frontend.get_translations(
                language, "entity", {DOMAIN}
            )
            
            language_options = []
            for key in translation_keys:
                # Try to get the translation for this language option
                translation_path = f"component.{DOMAIN}.entity.select.{self._entity_key}.state.{key}"
                translated = translations.get(translation_path, key)
                language_options.append(translated)
            
            return language_options
        except Exception:
            # Fallback to numeric keys if translation fails
            return translation_keys


    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.debug(
            "Select %s: attempting to set option %s",
            self._entity_key,
            option
        )

        # Map the option to the internal value
        internal_value = self._mappings.get(option, option)
        
        # If no mapping found, try to find the option index
        if internal_value == option and self.options:
            try:
                index = self.options.index(option)
                internal_value = str(index)
                _LOGGER.debug(
                    "Select %s: converted option %s to index value %s",
                    self._entity_key,
                    option,
                    internal_value
                )
            except ValueError:
                _LOGGER.debug(
                    "Select %s: option %s not found in options list, using raw value",
                    self._entity_key,
                    option
                )

        # Set the new value
        success = await self._async_set_parameter(internal_value)

        if not success:
            _LOGGER.error("Failed to set %s to %s (internal value: %s)", self._entity_key, option, internal_value)
            raise ValueError(f"Failed to set {self._entity_key} to {option}")

        _LOGGER.info("Successfully set %s to %s (internal value: %s)", self._entity_key, option, internal_value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return self._get_write_enabled_attribute()


class SVKHeatpumpSelect(SVKBaseEntity, SelectEntity):
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
        super().__init__(
            coordinator,
            config_entry_id,
            entity_key,
            entity_key,
            entity_id=entity_id,
            enabled_by_default=enabled_by_default
        )
        self._writable = writable

        _LOGGER.debug(
            "Creating select entity: %s (ID: %s, writable: %s, enabled_by_default: %s)",
            entity_key,
            entity_id,
            writable,
            enabled_by_default,
        )

        # Get entity info from catalog
        entity_info = self._get_entity_info()
        self._unit = entity_info.get("unit", "")
        self._device_class = entity_info.get("device_class")
        self._state_class = entity_info.get("state_class")
        self._original_name = entity_info.get("original_name", "")

        # Set options based on entity type
        options = []
        mappings = {}

        if entity_key == "season_mode":
            options = ["Summer", "Winter", "Auto"]
            _, SEASON_MODES_REVERSE, _ = _get_constants()
            mappings = SEASON_MODES_REVERSE
        elif entity_key == "heatpump_state":
            # This is read-only, but we'll include options for completeness
            options = [
                "Off",
                "Ready",
                "Start up",
                "Heating",
                "Hot water",
                "El heating",
                "Defrost",
                "Drip delay",
                "Total stop",
                "Pump exercise",
                "Forced running",
                "Manual",
            ]

        # Set entity category based on entity definition
        entity_info = self._get_entity_info()
        entity_category = None

        if entity_info.get("category"):
            entity_category = getattr(
                EntityCategory,
                entity_info["category"].upper(),
            )

        self.entity_description = SelectEntityDescription(
            key=self._entity_key,
            translation_key=self._entity_key,
            name=None,
            options=options,
            entity_category=entity_category,
        )

        # Store mappings for reverse lookup
        self._mappings = mappings


    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        value = self._get_entity_value()
        if value is not None:
            _LOGGER.debug(
                "Legacy Select %s: raw value from API: %s (type: %s)",
                self._entity_key,
                value,
                type(value).__name__
            )
            
            # Convert value to string for consistent comparison
            str_value = str(value)
            
            # First try to map using the mappings dictionary
            if self._mappings:
                for option, mapped_value in self._mappings.items():
                    if str(mapped_value) == str_value:
                        _LOGGER.debug(
                            "Legacy Select %s: mapped value %s to option %s",
                            self._entity_key,
                            str_value,
                            option
                        )
                        return option
            
            # If no mapping found or mappings empty, try to match directly with options
            options = self.options
            if options:
                # Try direct match with string value
                if str_value in options:
                    _LOGGER.debug(
                        "Legacy Select %s: direct match found for value %s",
                        self._entity_key,
                        str_value
                    )
                    return str_value
                
                # For numeric values, try to match by index
                if str_value.isdigit():
                    index = int(str_value)
                    if 0 <= index < len(options):
                        _LOGGER.debug(
                            "Legacy Select %s: mapped index %d to option %s",
                            self._entity_key,
                            index,
                            options[index]
                        )
                        return options[index]
            
            # If still no match, return the raw value as string
            _LOGGER.debug(
                "Legacy Select %s: no mapping found, returning raw value %s",
                self._entity_key,
                str_value
            )
            return str_value
        return None


    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if not self._writable:
            _LOGGER.warning(
                "Attempted to write to read-only select entity: %s", self._entity_key
            )
            raise ValueError("This select entity is read-only")

        _LOGGER.debug(
            "Legacy Select %s: attempting to set option %s",
            self._entity_key,
            option
        )

        # Map the option to the internal value
        internal_value = self._mappings.get(option, option)
        
        # If no mapping found, try to find the option index
        if internal_value == option and self.options:
            try:
                index = self.options.index(option)
                internal_value = str(index)
                _LOGGER.debug(
                    "Legacy Select %s: converted option %s to index value %s",
                    self._entity_key,
                    option,
                    internal_value
                )
            except ValueError:
                _LOGGER.debug(
                    "Legacy Select %s: option %s not found in options list, using raw value",
                    self._entity_key,
                    option
                )

        # Set the new value
        success = await self._async_set_parameter(internal_value)

        if not success:
            _LOGGER.error("Failed to set %s to %s (internal value: %s)", self._entity_key, option, internal_value)
            raise ValueError(f"Failed to set {self._entity_key} to {option}")

        _LOGGER.info("Successfully set %s to %s (internal value: %s)", self._entity_key, option, internal_value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return self._get_write_enabled_attribute()


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

    _LOGGER.info(
        "Setting up SVK Heatpump select entities for entry %s", config_entry.entry_id
    )

    # Use the entity factory to create all select entities
    from .entity_factory import create_entities_for_platform
    
    # Lazy load catalog functions before creating entities
    _lazy_import_catalog()
    
    select_entities = create_entities_for_platform(
        coordinator,
        config_entry.entry_id,
        "select",
        hass  # Pass hass for translation support
    )

    # Add additional select entities for system status
    system_status_desc = SelectEntityDescription(
        key="system_status",
        translation_key="system_status",
        name=None,
        options=["Off", "Standby", "Active", "Alarm", "Unknown"],
    )

    class SystemStatusSelect(SVKBaseEntity, SelectEntity):
        """Select entity for overall system status."""

        _attr_entity_registry_enabled_default = True

        def __init__(self, coordinator, config_entry_id):
            super().__init__(
                coordinator,
                config_entry_id,
                "system_status",
                "system_status"
            )
            self.entity_description = system_status_desc

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
    system_status_entity = SystemStatusSelect(coordinator, config_entry.entry_id)
    select_entities.append(system_status_entity)

    _LOGGER.info("Created %d select entities", len(select_entities))
    if select_entities:
        async_add_entities(select_entities, True)
