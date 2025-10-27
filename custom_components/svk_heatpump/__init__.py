"""SVK Heatpump custom component for Home Assistant."""

import asyncio
import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .client import LOMJsonClient, SVKAuthenticationError, SVKConnectionError
from .const import (
    DOMAIN,
)
from .coordinator import SVKHeatpumpDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SVK Heatpump from a config entry."""
    _LOGGER.info("Setting up SVK Heatpump integration for entry %s", entry.entry_id)
    _LOGGER.debug(
        "Entry data: %s",
        {k: "***" if k in ["password"] else v for k, v in entry.data.items()},
    )
    _LOGGER.debug("Entry options: %s", entry.options)

    host = entry.data["host"]
    username = entry.data.get("username", "")
    password = entry.data.get("password", "")

    _LOGGER.info(
        "Connecting to SVK Heatpump at %s (username: %s)",
        host,
        username if username else "none",
    )

    # Create JSON client with Digest authentication
    # Use DEFAULT_TIMEOUT from const.py to ensure consistent timeout behavior
    from .const import DEFAULT_TIMEOUT

    client = LOMJsonClient(
        host,
        username,
        password,
        DEFAULT_TIMEOUT,
    )
    _LOGGER.debug(
        "Created LOMJsonClient for %s with timeout %d seconds", host, DEFAULT_TIMEOUT
    )

    # Test connection
    try:
        _LOGGER.info(
            "Starting client session and testing connection - this may block Home Assistant startup"
        )
        await client.start()
        _LOGGER.info("Client session started successfully")

        # Skip redundant test request to avoid duplicate data fetching during setup
        _LOGGER.info(
            "Skipping redundant test request to avoid duplicate data fetching during setup"
        )
        _LOGGER.debug("Connection will be validated during first data refresh instead")
    except SVKAuthenticationError as err:
        _LOGGER.error("Authentication failed for SVK Heatpump at %s: %s", host, err)
        _LOGGER.error("Please check your credentials and authentication settings")
        raise ConfigEntryNotReady from err
    except SVKConnectionError as err:
        _LOGGER.error("Unable to connect to SVK Heatpump at %s: %s", host, err)
        _LOGGER.error("Please check if the device is reachable and the URL is correct")
        raise ConfigEntryNotReady from err
    except Exception as err:
        _LOGGER.error(
            "Unexpected error connecting to SVK Heatpump at %s: %s", host, err
        )
        _LOGGER.exception("Full exception details:")
        raise ConfigEntryNotReady from err

    # Create coordinator
    scan_interval = entry.options.get("scan_interval", 30)
    _LOGGER.debug("Creating coordinator with scan interval: %d seconds", scan_interval)
    coordinator = SVKHeatpumpDataCoordinator(
        hass, client, scan_interval, config_entry=entry
    )
    _LOGGER.info("Created SVKHeatpumpDataCoordinator for %s", host)

    # Store coordinator and client
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
    }
    _LOGGER.debug("Stored coordinator and client in hass.data")

    # Perform first data refresh with timeout to prevent blocking
    _LOGGER.info("Performing first data refresh with 30 second timeout protection")
    try:
        # Use asyncio.wait_for to prevent blocking during startup
        # Use 30 seconds for first refresh to match coordinator timeout
        await asyncio.wait_for(
            coordinator.async_config_entry_first_refresh(), timeout=30
        )
        _LOGGER.info("First data refresh completed successfully")
    except asyncio.TimeoutError:
        _LOGGER.error(
            "First data refresh timed out during startup - this may be blocking Home Assistant"
        )
        _LOGGER.error(
            "Consider increasing scan interval or checking heat pump responsiveness"
        )
        # Continue with setup even if refresh times out to allow entities to be created
    except Exception as err:
        _LOGGER.error("First data refresh failed with error: %s", err)
        _LOGGER.error(
            "This failure may be causing entities to be present but not updating"
        )
        _LOGGER.debug("First refresh failure details:", exc_info=True)
        # Continue with setup even if refresh fails to allow entities to be created

    # Setup platforms
    _LOGGER.info("Setting up platforms: %s", [p.value for p in PLATFORMS])
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.info("Platform setup completed successfully")
    except Exception as err:
        _LOGGER.error("Failed to setup platforms: %s", err)
        _LOGGER.exception("Platform setup exception details:")
        raise

    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    _LOGGER.debug("Added update listener")

    _LOGGER.info("SVK Heatpump integration setup completed successfully for %s", host)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading SVK Heatpump integration for entry %s", entry.entry_id)

    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        _LOGGER.debug("Platform unload result: %s", unload_ok)

        if unload_ok:
            # Close client session
            data = hass.data[DOMAIN].get(entry.entry_id, {})
            client = data.get("client")
            if client:
                _LOGGER.debug("Closing client session...")
                await client.close()
                _LOGGER.debug("Client session closed")

            hass.data[DOMAIN].pop(entry.entry_id)
            _LOGGER.debug("Removed entry data from hass.data")
        else:
            _LOGGER.warning("Platform unload failed for entry %s", entry.entry_id)

        _LOGGER.info(
            "SVK Heatpump integration unload completed for entry %s", entry.entry_id
        )
        return unload_ok
    except Exception as err:
        _LOGGER.error("Error during unload of entry %s: %s", entry.entry_id, err)
        _LOGGER.exception("Unload exception details:")
        return False


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.info("Updating options for SVK Heatpump entry %s", entry.entry_id)
    _LOGGER.debug("New options: %s", entry.options)

    try:
        data = hass.data[DOMAIN][entry.entry_id]
        coordinator = data["coordinator"]
        data["client"]

        # Update scan interval if changed
        new_scan_interval = entry.options.get("scan_interval", 30)
        old_scan_interval = coordinator.update_interval.total_seconds()
        if old_scan_interval != new_scan_interval:
            coordinator.update_interval = datetime.timedelta(seconds=new_scan_interval)
            _LOGGER.info(
                "Updated scan interval from %d to %d seconds for SVK Heatpump",
                old_scan_interval,
                new_scan_interval,
            )
        else:
            _LOGGER.debug("Scan interval unchanged at %d seconds", new_scan_interval)

        # Trigger refresh to apply new settings
        _LOGGER.debug("Triggering coordinator refresh to apply new settings...")
        await coordinator.async_request_refresh()
        _LOGGER.info("Options update completed successfully")
    except Exception as err:
        _LOGGER.error("Error updating options for entry %s: %s", entry.entry_id, err)
        _LOGGER.exception("Options update exception details:")
