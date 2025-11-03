"""Base entity class for SVK Heatpump integration."""

import re
from typing import Any

from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

from .const import (
    DEVICE_GROUPS,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SW_VERSION,
)


class SVKBaseEntity(Entity):
    """Base entity class for SVK Heatpump entities."""

    _attr_has_entity_name = True

    def __init__(self, group_key, entity_key, unique_suffix):
        """Initialize the SVK base entity."""
        self._group_key = group_key
        self._entity_key = entity_key
        self._attr_unique_id = f"{DOMAIN}_{group_key}_{unique_suffix}"
        self._attr_translation_key = self._entity_key

        # --- Suggested object_id to avoid duplicated prefixes in entity_id ---
        # Start from the catalog key but strip redundant prefixes like "svk_heatpump_"
        # and duplicated group markers like "service_service_".
        key = self._entity_key
        key = re.sub(r"^svk[_-]?heatpump[_-]?", "", key)            # drop integration prefix
        key = re.sub(r"^(service_)+", "service_", key)              # collapse repeated "service_"
        key = re.sub(r"^(display_)+", "display_", key)              # collapse repeated "display_"
        key = re.sub(r"__", "_", key)                               # collapse accidental doubles
        key = key.strip("_")

        # Optional: if your group_key is meaningful, you can prepend it only when not duplicated
        if group_key and not key.startswith(f"{group_key}_"):
            candidate = f"{group_key}_{key}"
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
