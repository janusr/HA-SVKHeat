"""Base entity class for SVK Heatpump integration."""

from homeassistant.helpers.entity import Entity

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

    def __init__(self, group_key, name, unique_suffix):
        """Initialize the SVK base entity."""
        self._group_key = group_key
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{group_key}_{unique_suffix}"

    @property
    def device_info(self):
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
