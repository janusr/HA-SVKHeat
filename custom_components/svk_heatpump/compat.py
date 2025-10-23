"""Compatibility module for Home Assistant version differences."""

try:
    # Try importing from the new location (Home Assistant 2023.4+)
    from homeassistant.helpers.entity_registry import DISABLED_INTEGRATION
except ImportError:
    try:
        # Fallback to the old location (older versions)
        from homeassistant.helpers.entity import DISABLED_INTEGRATION
    except ImportError:
        # Final fallback to string literal if constant doesn't exist
        DISABLED_INTEGRATION = "integration"