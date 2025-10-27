"""Switch platform for SVK Heatpump integration."""

import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .catalog import ENTITIES, SWITCH_ENTITIES

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)


class SVKSwitch(SVKHeatpumpBaseEntity, SwitchEntity):
    """Representation of a SVK Heatpump switch entity."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize switch entity."""
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
            "Creating switch entity: %s (group: %s, enabled_by_default: %s)",
            entity_key,
            group_key,
            enabled_by_default,
        )

        # Map data types to Home Assistant device classes
        device_class = None
        icon = None
        if data_type == "boolean":
            device_class = SwitchDeviceClass.SWITCH

        # Set icon based on entity name or group
        if "manual" in entity_key.lower():
            icon = "mdi:play-circle-outline"  # For manual controls
        elif "mainswitch" in entity_key.lower():
            icon = "mdi:power"  # For main power switch
        elif "season" in entity_key.lower():
            icon = "mdi:snowflake-melt"  # For season mode
        elif "neutralzone" in entity_key.lower():
            icon = "mdi:thermometer-auto"  # For neutral zone
        elif "toffset" in entity_key.lower():
            icon = "mdi:thermometer-plus"  # For temperature offset
        elif "concrete" in entity_key.lower():
            icon = "mdi:floor-plan"  # For concrete mode

        # Set entity category based on category
        entity_category = None
        if category == "Configuration":
            entity_category = EntityCategory.CONFIG
        elif category == "Settings":
            entity_category = EntityCategory.CONFIG

        # Create entity description
        self.entity_description = SwitchEntityDescription(
            key=entity_key,
            name=name,
            device_class=device_class,
            icon=icon,
            entity_category=entity_category,
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for switch."""
        return f"{DOMAIN}_{self._group_key}_{self._entity_key}"

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        value = self.coordinator.get_entity_value(self._entity_key)

        # Log value retrieval for debugging
        if value is None:
            _LOGGER.debug("Switch %s returned None value", self._entity_key)
        else:
            _LOGGER.debug("Switch %s returned value: %s", self._entity_key, value)

        # Convert value to boolean
        if value is None:
            return None
        elif isinstance(value, bool):
            return value
        elif isinstance(value, int | float):
            return bool(value)
        elif isinstance(value, str):
            return value.lower() in ("true", "1", "on", "enabled")

        return False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # For JSON API, entities should be available even if data fetching fails initially
        if self.coordinator.is_json_client:
            is_available = self.coordinator.is_entity_available(self._entity_key)
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.info(
                "JSON API Switch %s availability: %s (entity exists in mapping, current value: %s)",
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
                "HTML API Switch %s availability: %s (last_update_success: %s, writes_enabled: %s, entity_available: %s)",
                self._entity_key,
                is_available,
                last_update_success,
                writes_enabled,
                entity_available,
            )
            return is_available

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if not self.coordinator.config_entry.options.get("enable_writes", False):
            _LOGGER.warning("Write controls are disabled for %s", self._entity_key)
            raise ValueError("Write controls are disabled in options")

        # Set the switch to True
        success = await self.coordinator.async_set_parameter(self._entity_key, True)

        if not success:
            _LOGGER.error("Failed to turn on %s", self._entity_key)
            raise ValueError(f"Failed to turn on {self._entity_key}")

        _LOGGER.info("Successfully turned on %s", self._entity_key)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if not self.coordinator.config_entry.options.get("enable_writes", False):
            _LOGGER.warning("Write controls are disabled for %s", self._entity_key)
            raise ValueError("Write controls are disabled in options")

        # Set the switch to False
        success = await self.coordinator.async_set_parameter(self._entity_key, False)

        if not success:
            _LOGGER.error("Failed to turn off %s", self._entity_key)
            raise ValueError(f"Failed to turn off {self._entity_key}")

        _LOGGER.info("Successfully turned off %s", self._entity_key)


class SVKHeatpumpBaseEntity(CoordinatorEntity):
    """Base entity for SVK Heatpump integration."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        config_entry_id: str,
    ) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id

    @property
    def device_info(self):
        """Return device information from coordinator."""
        return self.coordinator.device_info


class SVKHeatpumpSwitch(SVKHeatpumpBaseEntity, SwitchEntity):
    """Representation of a SVK Heatpump switch entity."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        entity_id: int,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize switch entity."""
        super().__init__(coordinator, config_entry_id)
        self._entity_key = entity_key
        self._entity_id = entity_id
        self._attr_entity_registry_enabled_default = enabled_by_default

        _LOGGER.debug(
            "Creating switch entity: %s (ID: %s, enabled_by_default: %s)",
            entity_key,
            entity_id,
            enabled_by_default,
        )

        # Create entity description
        device_class = SwitchDeviceClass.SWITCH
        icon = None

        # Set icon based on entity name
        if "manual" in self._entity_key.lower():
            icon = "mdi:play-circle-outline"  # For manual controls
        elif "mainswitch" in self._entity_key.lower():
            icon = "mdi:power"  # For main power switch
        elif "season" in self._entity_key.lower():
            icon = "mdi:snowflake-melt"  # For season mode
        elif "neutralzone" in self._entity_key.lower():
            icon = "mdi:thermometer-auto"  # For neutral zone
        elif "toffset" in self._entity_key.lower():
            icon = "mdi:thermometer-plus"  # For temperature offset
        elif "concrete" in self._entity_key.lower():
            icon = "mdi:floor-plan"  # For concrete mode

        # Use entity_key for friendly display name
        friendly_name = self._entity_key.replace("_", " ").title()

        # Set entity category based on entity definition
        entity_category = EntityCategory.CONFIG

        self.entity_description = SwitchEntityDescription(
            key=self._entity_key,
            name=friendly_name,
            device_class=device_class,
            icon=icon,
            entity_category=entity_category,
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for switch."""
        return f"{self._config_entry_id}_{self._entity_id}"

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        value = self.coordinator.get_entity_value(self._entity_key)

        # Log value retrieval for debugging
        if value is None:
            _LOGGER.debug(
                "Switch %s (ID: %s) returned None value",
                self._entity_key,
                self._entity_id,
            )
        else:
            _LOGGER.debug(
                "Switch %s (ID: %s) returned value: %s",
                self._entity_key,
                self._entity_id,
                value,
            )

        # Convert value to boolean
        if value is None:
            return None
        elif isinstance(value, bool):
            return value
        elif isinstance(value, int | float):
            return bool(value)
        elif isinstance(value, str):
            return value.lower() in ("true", "1", "on", "enabled")

        return False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # For JSON API, entities should be available even if data fetching fails initially
        if self.coordinator.is_json_client:
            is_available = self.coordinator.is_entity_available(self._entity_key)
            value = self.coordinator.get_entity_value(self._entity_key)
            _LOGGER.info(
                "JSON API Switch %s availability: %s (entity exists in mapping, current value: %s)",
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
                "HTML API Switch %s availability: %s (last_update_success: %s, writes_enabled: %s, entity_available: %s)",
                self._entity_key,
                is_available,
                last_update_success,
                writes_enabled,
                entity_available,
            )
            return is_available

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if not self.coordinator.config_entry.options.get("enable_writes", False):
            _LOGGER.warning("Write controls are disabled for %s", self._entity_key)
            raise ValueError("Write controls are disabled in options")

        # Set the switch to True
        success = await self.coordinator.async_set_parameter(self._entity_key, True)

        if not success:
            _LOGGER.error("Failed to turn on %s", self._entity_key)
            raise ValueError(f"Failed to turn on {self._entity_key}")

        _LOGGER.info("Successfully turned on %s", self._entity_key)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if not self.coordinator.config_entry.options.get("enable_writes", False):
            _LOGGER.warning("Write controls are disabled for %s", self._entity_key)
            raise ValueError("Write controls are disabled in options")

        # Set the switch to False
        success = await self.coordinator.async_set_parameter(self._entity_key, False)

        if not success:
            _LOGGER.error("Failed to turn off %s", self._entity_key)
            raise ValueError(f"Failed to turn off {self._entity_key}")

        _LOGGER.info("Successfully turned off %s", self._entity_key)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up SVK Heatpump switch entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    _LOGGER.info(
        "Setting up SVK Heatpump switch entities for entry %s", config_entry.entry_id
    )
    _LOGGER.info("Coordinator is_json_client: %s", coordinator.is_json_client)

    switch_entities = []

    # Create switch entities based on SWITCH_ENTITIES from catalog
    if coordinator.is_json_client:
        # Create all switch entities from catalog
        for entity_key in SWITCH_ENTITIES:
            try:
                # Get entity info from catalog
                entity_info = ENTITIES.get(entity_key, {})
                name = entity_info.get("name", entity_key.replace("_", " ").title())
                entity_info.get("category", "")
                access_type = entity_info.get("access_type", "")

                # Only include writable entities
                if access_type != "readwrite":
                    _LOGGER.debug("Skipping read-only entity %s", entity_key)
                    continue

                # Determine if this entity should be enabled by default
                # For now, enable all switch entities from catalog
                enabled_by_default = True

                # Create switch using new SVKSwitch class
                switch = SVKSwitch(
                    coordinator,
                    entity_key,
                    config_entry.entry_id,
                    enabled_by_default=enabled_by_default,
                )

                switch_entities.append(switch)
                _LOGGER.debug(
                    "Added switch entity: %s (name: %s, enabled_by_default: %s)",
                    entity_key,
                    name,
                    enabled_by_default,
                )
            except Exception as err:
                _LOGGER.error("Failed to create switch entity %s: %s", entity_key, err)
                # Continue with other entities even if one fails
                continue
    else:
        # Fall back to HTML scraping entities for backward compatibility
        # Create basic entities even if JSON client is not available
        _LOGGER.warning(
            "JSON client not available, creating essential fallback entities"
        )

        # For switch entities, we don't have a predefined list of essential entities
        # So we'll create a minimal set based on manual controls
        essential_entities = [
            ("main_switch", 277),
        ]

        for entity_key, entity_id in essential_entities:
            try:
                switch = SVKHeatpumpSwitch(
                    coordinator,
                    entity_key,
                    entity_id,
                    config_entry.entry_id,
                    enabled_by_default=True,
                )
                switch_entities.append(switch)
                _LOGGER.info(
                    "Added fallback switch entity: %s (ID: %s)", entity_key, entity_id
                )
            except Exception as err:
                _LOGGER.error(
                    "Failed to create fallback switch entity %s (ID: %s): %s",
                    entity_key,
                    entity_id,
                    err,
                )
                # Continue with other entities even if one fails
                continue

    _LOGGER.info("Created %d switch entities", len(switch_entities))
    if switch_entities:
        async_add_entities(switch_entities, True)
