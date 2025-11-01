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
        options: list | None = None
        icon: str | None = None
        entity_category: str | None = None
        enabled_default: bool = True
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .catalog import ENTITIES, get_select_entities, SELECT_ENTITIES

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator


def _get_constants() -> tuple[dict[str, dict[str, Any]], dict[str, str], list[int]]:
    """Lazy import of constants to prevent blocking during async setup."""
    from .catalog import DEFAULT_ENABLED_ENTITIES, ENTITIES
    from .const import SEASON_MODES_REVERSE

    return ENTITIES, SEASON_MODES_REVERSE, DEFAULT_ENABLED_ENTITIES


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


class SVKSelect(SVKHeatpumpBaseEntity, SelectEntity):
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
        # Extract group key from entity key (first part before underscore)
        group_key = entity_key.split("_")[0]

        # Get entity info from catalog
        entity_info = ENTITIES.get(entity_key, {})
        data_type = entity_info.get("data_type", "")
        category = entity_info.get("category", "")

        # Initialize SVKHeatpumpBaseEntity (which inherits from CoordinatorEntity)
        super().__init__(coordinator, config_entry_id)

        # Initialize additional attributes
        self._entity_key = entity_key
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._group_key = group_key  # For unique_id property
        self._hass = hass  # Store hass for translation

        _LOGGER.debug(
            "Creating select entity: %s (group: %s, enabled_by_default: %s)",
            entity_key,
            group_key,
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
            key=entity_key,
            name=None,  # Use None for translation
            options=options,
            icon=icon,
            entity_category=entity_category,
        )
        
        # Store translation key for language options
        self._translation_key = f"select.{entity_key}"

        # Store mappings for reverse lookup
        self._mappings = mappings

    @property
    def unique_id(self) -> str:
        """Return unique ID for select entity."""
        return f"{DOMAIN}_{self._group_key}_{self._entity_key}"

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        value = self.coordinator.get_entity_value(self._entity_key)
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

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # For JSON API, entities should be available even if data fetching fails initially
        if self.coordinator.is_json_client:
            is_available = self.coordinator.is_entity_available(self._entity_key)
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.debug(
                "JSON API Select %s availability: %s (entity exists in mapping, current value: %s)",
                self._entity_key,
                is_available,
                value,
            )
            # Removed excessive diagnostic logging to prevent log storms
            return is_available
        else:
            # For HTML scraping, require successful update but NOT writes_enabled
            last_update_success = self.coordinator.last_update_success
            entity_available = self.coordinator.is_entity_available(self._entity_key)
            is_available = last_update_success and entity_available

            _LOGGER.debug(
                "HTML API Select %s availability: %s (last_update_success: %s, entity_available: %s)",
                self._entity_key,
                is_available,
                last_update_success,
                entity_available,
            )
            return is_available

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if not self.coordinator.config_entry.options.get("enable_writes", False):
            _LOGGER.warning("Write controls are disabled for %s", self._entity_key)
            raise ValueError("Write controls are disabled in options")

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
        success = await self.coordinator.async_set_parameter(
            self._entity_key, internal_value
        )

        if not success:
            _LOGGER.error("Failed to set %s to %s (internal value: %s)", self._entity_key, option, internal_value)
            raise ValueError(f"Failed to set {self._entity_key} to {option}")

        _LOGGER.info("Successfully set %s to %s (internal value: %s)", self._entity_key, option, internal_value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes = {}
        
        # Add write_enabled attribute to indicate if write controls are enabled
        writes_enabled = self.coordinator.config_entry.options.get("enable_writes", False)
        attributes["write_enabled"] = writes_enabled
        
        return attributes


class SVKHeatpumpSelect(SVKHeatpumpBaseEntity, SelectEntity):
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
        super().__init__(coordinator, config_entry_id)
        self._entity_key = entity_key
        self._entity_id = entity_id
        self._writable = writable
        self._attr_entity_registry_enabled_default = enabled_by_default

        _LOGGER.debug(
            "Creating select entity: %s (ID: %s, writable: %s, enabled_by_default: %s)",
            entity_key,
            entity_id,
            writable,
            enabled_by_default,
        )

        # Get entity info from ENTITIES structure
        entities_local, _, _ = _get_constants()
        # Find entity by ID in ENTITIES
        entity_info = None
        for entity_key, entity_data in entities_local.items():
            if "id" in entity_data and entity_data["id"] == entity_id:
                entity_info = {
                    "entity_key": entity_key,
                    "unit": entity_data.get("unit", ""),
                    "device_class": entity_data.get("device_class"),
                    "state_class": entity_data.get("state_class"),
                    "original_name": entity_data.get("original_name", ""),
                }
                break
        
        if not entity_info:
            _LOGGER.error("Entity ID %s not found in ENTITIES", entity_id)
            # Fallback to empty values if not found
            entity_info = {
                "entity_key": "",
                "unit": "",
                "device_class": None,
                "state_class": None,
                "original_name": "",
            }
        
        self._entity_key = entity_info["entity_key"]
        self._unit = entity_info["unit"]
        self._device_class = entity_info["device_class"]
        self._state_class = entity_info["state_class"]
        self._original_name = entity_info["original_name"]

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
        entity_category = None

        # Get entity info from ENTITIES dictionary instead of SELECT_ENTITIES list
        if self._entity_key in entities_local:
            entity_data = entities_local.get(self._entity_key, {})
            if entity_data.get("category"):
                entity_category = getattr(
                    EntityCategory,
                    entity_data["category"].upper(),
                )

        self.entity_description = SelectEntityDescription(
            key=self._entity_key,
            name=None,  # Use None for translation
            options=options,
            entity_category=entity_category,
        )

        # Store mappings for reverse lookup
        self._mappings = mappings

    @property
    def unique_id(self) -> str:
        """Return unique ID for select entity."""
        return f"{self._config_entry_id}_{self._entity_id}"

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        value = self.coordinator.get_entity_value(self._entity_key)
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

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.last_update_success:
            _LOGGER.debug(
                "Select %s availability: False (last_update_success: False)",
                self._entity_key,
            )
            return False

        # Entity availability should not depend on writes_enabled
        entity_available = self.coordinator.is_entity_available(self._entity_key)
        _LOGGER.debug(
            "Select %s availability: %s (writable: %s, entity_available: %s)",
            self._entity_key,
            entity_available,
            self._writable,
            entity_available,
        )
        return entity_available

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if not self._writable:
            _LOGGER.warning(
                "Attempted to write to read-only select entity: %s", self._entity_key
            )
            raise ValueError("This select entity is read-only")

        if not self.coordinator.config_entry.options.get("enable_writes", False):
            _LOGGER.warning("Write controls are disabled for %s", self._entity_key)
            raise ValueError("Write controls are disabled in options")

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
        success = await self.coordinator.async_set_parameter(
            self._entity_key, internal_value
        )

        if not success:
            _LOGGER.error("Failed to set %s to %s (internal value: %s)", self._entity_key, option, internal_value)
            raise ValueError(f"Failed to set {self._entity_key} to {option}")

        _LOGGER.info("Successfully set %s to %s (internal value: %s)", self._entity_key, option, internal_value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes = {}
        
        # Add write_enabled attribute to indicate if write controls are enabled
        writes_enabled = self.coordinator.config_entry.options.get("enable_writes", False)
        attributes["write_enabled"] = writes_enabled
        
        return attributes


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
    _LOGGER.info("Coordinator is_json_client: %s", coordinator.is_json_client)

    select_entities = []

    # Create select entities based on SELECT_ENTITIES from catalog
    if coordinator.is_json_client:
        # Create all select entities from catalog
        for entity_key in SELECT_ENTITIES:
            try:
                # Get entity info from catalog
                entity_info = ENTITIES.get(entity_key, {})
                access_type = entity_info.get("access_type", "")

                # Only include writable entities
                if access_type != "readwrite":
                    _LOGGER.debug("Skipping read-only entity %s", entity_key)
                    continue

                # Get entity ID to check against DEFAULT_ENABLED_ENTITIES
                entity_id = entity_info.get("id")
                enabled_by_default = coordinator.is_entity_enabled(entity_id) if entity_id else False

                # Create select using new SVKSelect class
                select = SVKSelect(
                    coordinator,
                    entity_key,
                    config_entry.entry_id,
                    hass,  # Pass hass for translation support
                    enabled_by_default=enabled_by_default,
                )

                select_entities.append(select)
                _LOGGER.debug(
                    "Added select entity: %s (enabled_by_default: %s)",
                    entity_key,
                    enabled_by_default,
                )
            except Exception as err:
                _LOGGER.error("Failed to create select entity %s: %s", entity_key, err)
                # Continue with other entities even if one fails
                continue
    else:
        # Fall back to HTML scraping entities for backward compatibility
        # Get constants using lazy import
        entities_local, _, default_enabled_entities = _get_constants()

        # Create all possible entities from entities_local
        for entity_key, entity_data in entities_local.items():
            # Only process entities that have an ID
            if "id" not in entity_data or entity_data["id"] is None:
                continue
                
            _unit = entity_data.get("unit", "")
            _device_class = entity_data.get("device_class")
            _state_class = entity_data.get("state_class")
            _original_name = entity_data.get("original_name", "")
            # Only include select entities
            if entity_key in ["user_parameters_seasonmode", "display_heatpump_state"]:
                # Check if this entity should be enabled by default
                enabled_by_default = coordinator.is_entity_enabled(entity_data["id"]) if entity_data["id"] else False

                # Determine if writable
                writable = (
                    entity_key == "season_mode"
                    and coordinator.config_entry.options.get("enable_writes", False)
                )

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
                    entity_data["id"],
                    config_entry.entry_id,
                    writable,
                    enabled_by_default=enabled_by_default,
                )

                select_entities.append(select_entity)
                _LOGGER.debug(
                    "Added select entity: %s (ID: %s, enabled_by_default: %s)",
                    entity_key,
                    entity_data["id"],
                    enabled_by_default,
                )

    # Add additional select entities for system status
    system_status_desc = SelectEntityDescription(
        key="system_status",
        name=None,  # Use None for translation
        options=["Off", "Standby", "Active", "Alarm", "Unknown"],
    )

    class SystemStatusSelect(SVKHeatpumpBaseEntity, SelectEntity):
        """Select entity for overall system status."""

        _attr_entity_registry_enabled_default = True

        def __init__(self, coordinator, config_entry_id):
            super().__init__(coordinator, config_entry_id)
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
    system_status_entity = SystemStatusSelect(coordinator, config_entry.entry_id)
    select_entities.append(system_status_entity)

    _LOGGER.info("Created %d select entities", len(select_entities))
    if select_entities:
        async_add_entities(select_entities, True)
