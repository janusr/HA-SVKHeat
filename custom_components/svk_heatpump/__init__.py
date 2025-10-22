"""SVK Heatpump custom component for Home Assistant."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .client import LOMJsonClient, SVKConnectionError, SVKAuthenticationError
from .const import DOMAIN
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SVK Heatpump from a config entry."""
    host = entry.data["host"]
    username = entry.data.get("username", "")
    password = entry.data.get("password", "")
    allow_basic_auth = entry.data.get("allow_basic_auth", False)
    
    # Create JSON client with Digest authentication
    client = LOMJsonClient(host, username, password, allow_basic_auth=allow_basic_auth)
    
    # Test connection
    try:
        await client.start()
        # Test with a simple read operation to validate connection
        await client.read_values([299])  # Test with a common ID
    except SVKAuthenticationError as err:
        _LOGGER.error("Authentication failed for SVK Heatpump at %s: %s", host, err)
        raise ConfigEntryNotReady from err
    except SVKConnectionError as err:
        _LOGGER.error("Unable to connect to SVK Heatpump at %s: %s", host, err)
        raise ConfigEntryNotReady from err
    except Exception as err:
        _LOGGER.error("Unexpected error connecting to SVK Heatpump at %s: %s", host, err)
        raise ConfigEntryNotReady from err
    
    # Create coordinator
    scan_interval = entry.options.get("scan_interval", 30)
    coordinator = SVKHeatpumpDataCoordinator(hass, client, scan_interval, config_entry=entry)
    
    # Store coordinator and client
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "allow_basic_auth": allow_basic_auth,
    }
    
    # Perform first data refresh
    await coordinator.async_config_entry_first_refresh()
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Close client session
        data = hass.data[DOMAIN].get(entry.entry_id, {})
        client = data.get("client")
        if client:
            await client.close()
        
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    # Update scan interval if changed
    new_scan_interval = entry.options.get("scan_interval", 30)
    if coordinator.update_interval.total_seconds() != new_scan_interval:
        coordinator.update_interval = asyncio.timedelta(seconds=new_scan_interval)
        _LOGGER.info(
            "Updated scan interval to %d seconds for SVK Heatpump",
            new_scan_interval
        )
    
    # Trigger refresh to apply new settings
    await coordinator.async_request_refresh()