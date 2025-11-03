"""Number platform for SVK Heatpump integration."""

import logging
from typing import Any

try:
    from homeassistant.components.number import (
        NumberDeviceClass,
        NumberEntity,
        NumberEntityDescription,
        NumberMode,
    )
except ImportError:
    # Fallback for older Home Assistant versions
    from homeassistant.components.number import (
        NumberDeviceClass,
        NumberEntity,
        NumberMode,
    )
    # For older versions, create a fallback EntityDescription
    from dataclasses import dataclass
    
    @dataclass
    class NumberEntityDescription:
        """Fallback NumberEntityDescription for older HA versions."""
        key: str
        name: str | None = None
        translation_key: str | None = None
        device_class: str | None = None
        native_unit_of_measurement: str | None = None
        native_min_value: float | None = None
        native_max_value: float | None = None
        native_step: float | None = None
        entity_category: str | None = None
        icon: str | None = None
        enabled_default: bool = True
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant

from .catalog import ENTITIES, get_number_entities
from .entity_base import SVKBaseEntity

# Import specific items from modules
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator


def _get_constants() -> tuple[dict[str, dict[str, Any]], list[int]]:
    """Lazy import of constants to prevent blocking during async setup."""
    from .catalog import DEFAULT_ENABLED_ENTITIES, ENTITIES

    return ENTITIES, DEFAULT_ENABLED_ENTITIES


_LOGGER = logging.getLogger(__name__)


class SVKNumber(SVKBaseEntity, NumberEntity):
    """Representation of a SVK Heatpump number entity."""

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        entity_key: str,
        config_entry_id: str,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the number entity."""
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
        unit = entity_info.get("unit", "")
        category = entity_info.get("category", "")
        min_value = entity_info.get("min_value", 0)
        max_value = entity_info.get("max_value", 100)
        step = entity_info.get("step", 1)

        _LOGGER.debug(
            "Creating number entity: %s (group: %s, min: %s, max: %s, step: %s, unit: %s)",
            entity_key,
            self._group_key,
            min_value,
            max_value,
            step,
            unit,
        )

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
            key=self._entity_key,
            translation_key=self._entity_key,
            name=None,
            device_class=device_class,
            native_min_value=min_value,
            native_max_value=max_value,
            native_step=step,
            native_unit_of_measurement=unit,
            entity_category=entity_category,
        )

        # Set mode to slider for better UX
        self._attr_mode = NumberMode.SLIDER


    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        value = self._get_entity_value()
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Could not convert %s value '%s' to float", self._entity_key, value
                )
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set a new value."""
        # Validate value is within bounds
        if value < self.native_min_value or value > self.native_max_value:
            raise ValueError(
                f"Value {value} is outside the valid range "
                f"({self.native_min_value} - {self.native_max_value})"
            )

        # Set the new value
        success = await self._async_set_parameter(value)

        if not success:
            _LOGGER.error("Failed to set %s to %s", self._entity_key, value)
            raise ValueError(f"Failed to set {self._entity_key} to {value}")

        _LOGGER.info("Successfully set %s to %s", self._entity_key, value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return self._get_write_enabled_attribute()


class SVKHeatpumpNumber(SVKBaseEntity, NumberEntity):
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
        super().__init__(
            coordinator,
            config_entry_id,
            entity_key,
            entity_key,
            entity_id=entity_id,
            enabled_by_default=enabled_by_default
        )
        self._min_value = min_value
        self._max_value = max_value
        self._step = step

        _LOGGER.debug(
            "Creating number entity: %s (ID: %s, range: %s-%s, step: %s, enabled_by_default: %s)",
            entity_key,
            entity_id,
            min_value,
            max_value,
            step,
            enabled_by_default,
        )

        # Get entity info from catalog
        entity_info = self._get_entity_info()
        self._unit = entity_info.get("unit", "")
        self._device_class = entity_info.get("device_class")
        self._state_class = entity_info.get("state_class")
        self._original_name = entity_info.get("original_name", "")

        # Create entity description
        device_class = None
        if self._device_class == "temperature":
            device_class = NumberDeviceClass.TEMPERATURE

        # Set entity category based on entity definition
        entity_info = self._get_entity_info()
        entity_category = None

        if entity_info.get("category"):
            entity_category = getattr(
                EntityCategory,
                entity_info["category"].upper(),
            )

        self.entity_description = NumberEntityDescription(
            key=self._entity_key,
            translation_key=self._entity_key,
            name=None,
            device_class=device_class,
            native_min_value=self._min_value,
            native_max_value=self._max_value,
            native_step=self._step,
            native_unit_of_measurement=self._unit,
            entity_category=entity_category,
        )

        # Set mode to slider for better UX
        self._attr_mode = NumberMode.SLIDER


    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        value = self._get_entity_value()
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Could not convert %s value '%s' to float", self._entity_key, value
                )
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set a new value."""
        # Validate value is within bounds
        if value < self.native_min_value or value > self.native_max_value:
            raise ValueError(
                f"Value {value} is outside the valid range "
                f"({self.native_min_value} - {self.native_max_value})"
            )

        # Set the new value
        success = await self._async_set_parameter(value)

        if not success:
            _LOGGER.error("Failed to set %s to %s", self._entity_key, value)
            raise ValueError(f"Failed to set {self._entity_key} to {value}")

        _LOGGER.info("Successfully set %s to %s", self._entity_key, value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return self._get_write_enabled_attribute()


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
            tank_temp = self.coordinator.get_entity_value("display_input_twatertank")
            if tank_temp is not None:
                attributes["current_tank_temperature"] = tank_temp

            # Add heating status
            heatpump_state = self.coordinator.get_entity_value("display_heatpump_state")
            if heatpump_state is not None:
                attributes["heatpump_state"] = heatpump_state

            # Add heating setpoint for comparison
            heating_setpoint = self.coordinator.get_entity_value("user_heatspctrl_troomset")
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
            room_temp = self.coordinator.get_entity_value("display_input_troom")
            if room_temp is not None:
                attributes["current_room_temperature"] = room_temp

            # Add ambient temperature
            ambient_temp = self.coordinator.get_entity_value("display_input_tamb")
            if ambient_temp is not None:
                attributes["ambient_temperature"] = ambient_temp

            # Add heating status
            heatpump_state = self.coordinator.get_entity_value("display_heatpump_state")
            if heatpump_state is not None:
                attributes["heatpump_state"] = heatpump_state

        return attributes


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up SVK Heatpump number entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    _LOGGER.info(
        "Setting up SVK Heatpump number entities for entry %s", config_entry.entry_id
    )

    # Use the entity factory to create all number entities
    from .entity_factory import create_entities_for_platform
    number_entities = create_entities_for_platform(
        coordinator,
        config_entry.entry_id,
        "number"
    )

    # Add additional number entities for monitoring (read-only)
    heating_setpoint_desc = NumberEntityDescription(
        key="heating_setpoint_monitor",
        translation_key="heating_setpoint_monitor",
        name=None,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=10,
        native_max_value=35,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    )

    class HeatingSetpointMonitor(SVKBaseEntity, NumberEntity):
        """Read-only monitor for heating setpoint."""

        _attr_entity_registry_enabled_default = False

        def __init__(self, coordinator, config_entry_id):
            # Initialize SVKBaseEntity
            super().__init__(
                coordinator,
                config_entry_id,
                "heating_setpoint_monitor",
                "system_heating_setpoint_monitor",
                enabled_by_default=False
            )
            self.entity_description = heating_setpoint_desc

        @property
        def native_value(self) -> float | None:
            """Return current heating setpoint value."""
            value = self.coordinator.get_entity_value("user_heatspctrl_troomset")
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
                and self.coordinator.is_entity_available("user_heatspctrl_troomset")
            )

        async def async_set_native_value(self, value: float) -> None:
            """Prevent setting value on monitor."""
            raise ValueError("This is a read-only monitor entity")

    # Heating setpoint monitor is disabled by default
    heating_monitor = HeatingSetpointMonitor(coordinator, config_entry.entry_id)
    number_entities.append(heating_monitor)


    _LOGGER.info("Created %d number entities", len(number_entities))
    if number_entities:
        async_add_entities(number_entities, True)
