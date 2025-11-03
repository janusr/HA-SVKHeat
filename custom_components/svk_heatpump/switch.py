"""Switch platform for SVK Heatpump integration."""

import logging
from typing import Any

try:
    from homeassistant.components.switch import (
        SwitchDeviceClass,
        SwitchEntity,
        SwitchEntityDescription,
    )
except ImportError:
    # Fallback for older Home Assistant versions
    from homeassistant.components.switch import (
        SwitchDeviceClass,
        SwitchEntity,
    )
    # For older versions, create a fallback EntityDescription
    from dataclasses import dataclass
    
    @dataclass
    class SwitchEntityDescription:
        """Fallback SwitchEntityDescription for older HA versions."""
        key: str
        name: str | None = None
        translation_key: str | None = None
        device_class: str | None = None
        icon: str | None = None
        entity_category: str | None = None
        enabled_default: bool = True
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .catalog import ENTITIES, get_switch_entities
from .entity_base import SVKBaseEntity

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)


class SVKSwitch(SVKBaseEntity, SwitchEntity):
    """Representation of a SVK Heatpump switch entity."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize switch entity."""
        # Initialize SVKBaseEntity
        super().__init__(
            coordinator,
            config_entry_id,
            entity_key,
            entity_key,
            enabled_by_default=enabled_by_default
        )

        # Get entity info from catalog
        entity_info = self._get_entity_info()
        data_type = entity_info.get("data_type", "")
        category = entity_info.get("category", "")

        _LOGGER.debug(
            "Creating switch entity: %s (group: %s, enabled_by_default: %s)",
            entity_key,
            self._group_key,
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
            key=self._entity_key,
            translation_key=self._entity_key,
            name=None,
            device_class=device_class,
            icon=icon,
            entity_category=entity_category,
        )


    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        value = self._get_entity_value()
        self._log_value_retrieval(value)

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        # Set the switch to True
        success = await self._async_set_parameter(True)

        if not success:
            _LOGGER.error("Failed to turn on %s", self._entity_key)
            raise ValueError(f"Failed to turn on {self._entity_key}")

        _LOGGER.info("Successfully turned on %s", self._entity_key)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        # Set the switch to False
        success = await self._async_set_parameter(False)

        if not success:
            _LOGGER.error("Failed to turn off %s", self._entity_key)
            raise ValueError(f"Failed to turn off {self._entity_key}")

        _LOGGER.info("Successfully turned off %s", self._entity_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return self._get_write_enabled_attribute()


class SVKHeatpumpSwitch(SVKBaseEntity, SwitchEntity):
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
        super().__init__(
            coordinator,
            config_entry_id,
            entity_key,
            entity_key,
            entity_id=entity_id,
            enabled_by_default=enabled_by_default
        )

        _LOGGER.debug(
            "Creating switch entity: %s (enabled_by_default: %s)",
            entity_key,
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

        # Set entity category based on entity definition
        entity_category = EntityCategory.CONFIG

        self.entity_description = SwitchEntityDescription(
            key=self._entity_key,
            translation_key=self._entity_key,
            name=None,
            device_class=device_class,
            icon=icon,
            entity_category=entity_category,
        )


    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        value = self._get_entity_value()
        self._log_value_retrieval(value)

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        # Set the switch to True
        success = await self._async_set_parameter(True)

        if not success:
            _LOGGER.error("Failed to turn on %s", self._entity_key)
            raise ValueError(f"Failed to turn on {self._entity_key}")

        _LOGGER.info("Successfully turned on %s", self._entity_key)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        # Set the switch to False
        success = await self._async_set_parameter(False)

        if not success:
            _LOGGER.error("Failed to turn off %s", self._entity_key)
            raise ValueError(f"Failed to turn off {self._entity_key}")

        _LOGGER.info("Successfully turned off %s", self._entity_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return self._get_write_enabled_attribute()


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up SVK Heatpump switch entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    _LOGGER.info(
        "Setting up SVK Heatpump switch entities for entry %s", config_entry.entry_id
    )

    # Use the entity factory to create all switch entities
    from .entity_factory import create_entities_for_platform
    switch_entities = create_entities_for_platform(
        coordinator,
        config_entry.entry_id,
        "switch"
    )

    _LOGGER.info("Created %d switch entities", len(switch_entities))
    if switch_entities:
        async_add_entities(switch_entities, True)
