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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .catalog import ENTITIES, SELECT_ENTITIES

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator


def _get_constants() -> tuple[dict[int, tuple[str, str, str, str, str]], dict[str, str], list[int]]:
    """Lazy import of constants to prevent blocking during async setup."""
    from .const import DEFAULT_ENABLED_ENTITIES, ID_MAP, SEASON_MODES_REVERSE

    return ID_MAP, SEASON_MODES_REVERSE, DEFAULT_ENABLED_ENTITIES


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
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize select entity."""
        # Extract group key from entity key (first part before underscore)
        group_key = entity_key.split("_")[0]

        # Get entity info from catalog
        entity_info = ENTITIES.get(entity_key, {})
        name = entity_info.get("name", entity_key.replace("_", " ").title())
        data_type = entity_info.get("data_type", "")
        category = entity_info.get("category", "")

        # Initialize SVKHeatpumpBaseEntity (which inherits from CoordinatorEntity)
        super().__init__(coordinator, config_entry_id)

        # Initialize additional attributes
        self._entity_key = entity_key
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._group_key = group_key  # For unique_id property

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
            elif entity_key == "heating_heating_source":
                options = ["Heat pump", "Electric", "Manual"]
            elif entity_key == "heating_heatspctrl_type":
                options = ["Off", "Curve", "Room", "Outdoor"]
            elif entity_key == "heatpump_heating_ctrlmode":
                options = ["Off", "Room", "Outdoor", "Curve"]
            elif entity_key == "heatpump_cprcontrol_cprmode":
                options = ["Off", "Standard", "Eco", "Comfort"]
            elif entity_key == "heatpump_coldpump_mode":
                options = ["Off", "Auto", "Manual"]
            elif entity_key == "hotwater_hotwater_source":
                options = ["Heat pump", "Electric", "Solar"]
            elif entity_key == "service_parameters_displaymode":
                options = ["Basic", "Advanced", "Service"]
            elif entity_key == "solar_solarpanel_sensorselect":
                options = ["Internal", "External"]
            elif entity_key == "user_user_language":
                options = ["English", "Danish", "German", "Swedish"]
            else:
                # Default options for unknown enum
                options = ["Option 1", "Option 2", "Option 3"]

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
            name=name,
            options=options,
            icon=icon,
            entity_category=entity_category,
        )

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
            # Map the internal value to the display option
            for option, mapped_value in self._mappings.items():
                if mapped_value == value:
                    return option
            # If no mapping found, return the raw value as string
            return str(value)
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # For JSON API, entities should be available even if data fetching fails initially
        if self.coordinator.is_json_client:
            is_available = self.coordinator.is_entity_available(self._entity_key)
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.info(
                "JSON API Select %s availability: %s (entity exists in mapping, current value: %s)",
                self._entity_key,
                is_available,
                value,
            )
            # Add additional diagnostic info
            if not is_available:
                _LOGGER.warning(
                    "Entity %s is not available - this may indicate a data fetching or parsing issue",
                    self._entity_key,
                )
            elif value is None:
                _LOGGER.warning(
                    "Entity %s is available but has no value - likely a parsing or data issue",
                    self._entity_key,
                )
            return is_available
        else:
            # For HTML scraping, require successful update
            last_update_success = self.coordinator.last_update_success
            writes_enabled = self.coordinator.config_entry.options.get(
                "enable_writes", False
            )
            entity_available = self.coordinator.is_entity_available(self._entity_key)
            is_available = last_update_success and writes_enabled and entity_available

            _LOGGER.debug(
                "HTML API Select %s availability: %s (last_update_success: %s, writes_enabled: %s, entity_available: %s)",
                self._entity_key,
                is_available,
                last_update_success,
                writes_enabled,
                entity_available,
            )
            return is_available

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if not self.coordinator.config_entry.options.get("enable_writes", False):
            _LOGGER.warning("Write controls are disabled for %s", self._entity_key)
            raise ValueError("Write controls are disabled in options")

        # Map the option to the internal value
        internal_value = self._mappings.get(option, option)

        # Set the new value
        success = await self.coordinator.async_set_parameter(
            self._entity_key, internal_value
        )

        if not success:
            _LOGGER.error("Failed to set %s to %s", self._entity_key, internal_value)
            raise ValueError(f"Failed to set {self._entity_key} to {option}")

        _LOGGER.info("Successfully set %s to %s", self._entity_key, internal_value)


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

        # Get entity info from ID_MAP (5-element structure)
        ID_MAP, _, _ = _get_constants()
        if entity_id not in ID_MAP:
            _LOGGER.error("Entity ID %s not found in ID_MAP", entity_id)
            entity_info = ("", "", None, None, "")
        else:
            entity_info = ID_MAP[entity_id]
        (
            self._entity_key,
            self._unit,
            self._device_class,
            self._state_class,
            self._original_name,
        ) = entity_info

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

        # Use original_name for friendly display name if available
        friendly_name = (
            self._original_name.replace("_", " ").title()
            if self._original_name
            else self._entity_key.replace("_", " ").title()
        )

        # Set entity category based on entity definition
        entity_category = None

        # Get entity info from ENTITIES dictionary instead of SELECT_ENTITIES list
        if self._entity_key in ENTITIES and ENTITIES.get(
            self._entity_key, {}
        ).get("entity_category"):
            entity_category = getattr(
                EntityCategory,
                ENTITIES[self._entity_key]["entity_category"].upper(),
            )

        self.entity_description = SelectEntityDescription(
            key=self._entity_key,
            name=friendly_name,
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
            _LOGGER.debug(
                "Select %s availability: False (last_update_success: False)",
                self._entity_key,
            )
            return False

        # Check if writes are enabled for writable entities
        if self._writable:
            writes_enabled = self.coordinator.config_entry.options.get(
                "enable_writes", False
            )
            entity_available = self.coordinator.is_entity_available(self._entity_key)
            is_available = writes_enabled and entity_available
            _LOGGER.debug(
                "Select %s availability: %s (writable: %s, writes_enabled: %s, entity_available: %s)",
                self._entity_key,
                is_available,
                self._writable,
                writes_enabled,
                entity_available,
            )
            return is_available

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

        # Map the option to the internal value
        internal_value = self._mappings.get(option, option)

        # Set the new value
        success = await self.coordinator.async_set_parameter(
            self._entity_key, internal_value
        )

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
                name = entity_info.get("name", entity_key.replace("_", " ").title())
                access_type = entity_info.get("access_type", "")

                # Only include writable entities
                if access_type != "readwrite":
                    _LOGGER.debug("Skipping read-only entity %s", entity_key)
                    continue

                # Determine if this entity should be enabled by default
                # For now, enable all select entities from catalog
                enabled_by_default = True

                # Create select using new SVKSelect class
                select = SVKSelect(
                    coordinator,
                    entity_key,
                    config_entry.entry_id,
                    enabled_by_default=enabled_by_default,
                )

                select_entities.append(select)
                _LOGGER.debug(
                    "Added select entity: %s (name: %s, enabled_by_default: %s)",
                    entity_key,
                    name,
                    enabled_by_default,
                )
            except Exception as err:
                _LOGGER.error("Failed to create select entity %s: %s", entity_key, err)
                # Continue with other entities even if one fails
                continue
    else:
        # Fall back to HTML scraping entities for backward compatibility
        # Get constants using lazy import
        ID_MAP, _, DEFAULT_ENABLED_ENTITIES = _get_constants()

        # Create all possible entities from ID_MAP
        for entity_id, (
            entity_key,
            _unit,
            _device_class,
            _state_class,
            _original_name,
        ) in ID_MAP.items():
            # Only include select entities
            if entity_key in ["season_mode", "heatpump_state"]:
                # Check if this entity should be enabled by default
                enabled_by_default = entity_id in DEFAULT_ENABLED_ENTITIES

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
                    entity_id,
                    config_entry.entry_id,
                    writable,
                    enabled_by_default=enabled_by_default,
                )

                select_entities.append(select_entity)
                _LOGGER.debug(
                    "Added select entity: %s (ID: %s, enabled_by_default: %s)",
                    entity_key,
                    entity_id,
                    enabled_by_default,
                )

    # Add additional select entities for system status
    system_status_desc = SelectEntityDescription(
        key="system_status",
        name="System Status",
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
