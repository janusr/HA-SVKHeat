"""Base entity class for SVK Heatpump integration."""

import logging
import re
from typing import Any, Union

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    DEVICE_GROUPS,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SW_VERSION,
)
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)

# Temperature sentinel threshold
TEMPERATURE_SENTINEL_THRESHOLD = -80.0


class SVKBaseEntity(CoordinatorEntity):
    """Unified base entity class for SVK Heatpump entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SVKHeatpumpDataCoordinator,
        config_entry_id: str,
        entity_key: str,
        unique_suffix: str | None = None,
        entity_id: int | None = None,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the SVK base entity."""
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id
        self._entity_key = entity_key
        self._entity_id = entity_id
        self._attr_entity_registry_enabled_default = enabled_by_default

        # Extract group key from entity key (first part before underscore)
        self._group_key = entity_key.split("_")[0] if "_" in entity_key else entity_key

        # Generate unique ID based on the pattern
        if unique_suffix is None:
            unique_suffix = entity_key
        
        # For entities with entity_id, use config_entry_id + entity_id pattern
        if entity_id is not None:
            self._attr_unique_id = f"{config_entry_id}_{entity_id}"
        else:
            self._attr_unique_id = f"{DOMAIN}_{self._group_key}_{unique_suffix}"
        
        self._attr_translation_key = entity_key

        # --- Suggested object_id to avoid duplicated prefixes in entity_id ---
        # Start from the catalog key but strip redundant prefixes like "svk_heatpump_"
        # and duplicated group markers like "service_service_".
        key = entity_key
        key = re.sub(r"^svk[_-]?heatpump[_-]?", "", key)            # drop integration prefix
        key = re.sub(r"^(service_)+", "service_", key)              # collapse repeated "service_"
        key = re.sub(r"^(display_)+", "display_", key)              # collapse repeated "display_"
        key = re.sub(r"__", "_", key)                               # collapse accidental doubles
        key = key.strip("_")

        # Optional: if your group_key is meaningful, you can prepend it only when not duplicated
        if self._group_key and not key.startswith(f"{self._group_key}_"):
            candidate = f"{self._group_key}_{key}"
        else:
            candidate = key

        # Slugify for safety
        self._attr_suggested_object_id = slugify(candidate)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information for this entity."""
        device_info = {
            "identifiers": {(DOMAIN, self._group_key)},
            "name": DEVICE_GROUPS[self._group_key]["name"],
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": SW_VERSION,
        }

        # Add via_device if the group has a "via" parameter
        if "via" in DEVICE_GROUPS[self._group_key]:
            device_info["via_device"] = (DOMAIN, DEVICE_GROUPS[self._group_key]["via"])

        return device_info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        is_available = self.coordinator.is_entity_available(self._entity_key)
        value = self.coordinator.get_entity_value(self._entity_key)
        _LOGGER.debug(
            "Entity %s availability: %s (entity exists in mapping, current value: %s)",
            self._entity_key,
            is_available,
            value,
        )
        return is_available

    def _apply_temperature_sentinel_rule(self, value: Any) -> Any:
        """Apply temperature sentinel rule: values ≤ -80.0°C mark entities unavailable."""
        if value is not None and isinstance(value, (int, float)):
            if value <= TEMPERATURE_SENTINEL_THRESHOLD:
                _LOGGER.debug(
                    "Entity %s temperature %s°C is below sentinel threshold, marking unavailable",
                    self._entity_key,
                    value,
                )
                return None
        return value

    def _apply_percentage_clamping(self, value: Any, unit: str) -> Any:
        """Apply percentage clamping for percentage values (0-100% range)."""
        if unit == "%" and value is not None:
            try:
                if isinstance(value, (int, float)):
                    clamped_value = max(0, min(100, float(value)))
                    if clamped_value != float(value):
                        _LOGGER.debug(
                            "Entity %s percentage value clamped from %s to %s",
                            self._entity_key,
                            value,
                            clamped_value,
                        )
                    return clamped_value
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "Entity %s failed to clamp percentage value %s",
                    self._entity_key,
                    value,
                )
                pass
        return value

    def _check_write_protection(self) -> None:
        """Check if write operations are enabled and raise error if not."""
        if not self.coordinator.config_entry.options.get("enable_writes", False):
            _LOGGER.warning("Write controls are disabled for %s", self._entity_key)
            raise ValueError("Write controls are disabled in options")

    def _get_entity_info(self) -> dict[str, Any]:
        """Get entity information from the catalog."""
        from .catalog import ENTITIES
        
        entity_info = ENTITIES.get(self._entity_key, {})
        
        # If we have an entity_id, try to find the entity by ID
        if self._entity_id is not None:
            for entity_key, entity_data in ENTITIES.items():
                if "id" in entity_data and entity_data["id"] == self._entity_id:
                    entity_info = {
                        "entity_key": entity_key,
                        "unit": entity_data.get("unit", ""),
                        "device_class": entity_data.get("device_class"),
                        "state_class": entity_data.get("state_class"),
                        "data_type": entity_data.get("data_type", ""),
                        "category": entity_data.get("category", ""),
                        "original_name": entity_data.get("original_name", ""),
                        "min_value": entity_data.get("min_value", 0),
                        "max_value": entity_data.get("max_value", 100),
                        "step": entity_data.get("step", 1),
                    }
                    break
        
        return entity_info

    def _get_write_enabled_attribute(self) -> dict[str, Any]:
        """Get write_enabled attribute for extra state attributes."""
        writes_enabled = self.coordinator.config_entry.options.get("enable_writes", False)
        return {"write_enabled": writes_enabled}

    async def _async_set_parameter(self, value: Any) -> bool:
        """Set a parameter value with write protection check."""
        self._check_write_protection()
        return await self.coordinator.async_set_parameter(self._entity_key, value)

    def _get_entity_value(self) -> Any:
        """Get the current entity value from coordinator."""
        return self.coordinator.get_entity_value(self._entity_key)

    def _log_value_retrieval(self, value: Any) -> None:
        """Log value retrieval for debugging."""
        if value is None:
            _LOGGER.debug("Entity %s returned None value", self._entity_key)
        else:
            _LOGGER.debug("Entity %s returned value: %s", self._entity_key, value)
