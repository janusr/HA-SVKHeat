"""SVK Heatpump integration for Home Assistant."""

from typing import Dict, Any, List, Union

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, SERVICE_SET_VALUE, get_unique_id, async_load_catalog
from .coordinator import SVKDataUpdateCoordinator
from .config_flow import SVKHeatpumpOptionsFlow

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the SVK Heatpump component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SVK Heatpump from a config entry."""
    import logging
    setup_logger = logging.getLogger(__name__ + ".setup")
    
    setup_logger.info(
        "Setting up SVK Heatpump integration for entry %s",
        entry.entry_id
    )
    
    try:
        hass.data.setdefault(DOMAIN, {})
        
        # Create coordinator
        coordinator = SVKDataUpdateCoordinator(hass, entry)
        
        # Load catalog asynchronously
        try:
            setup_logger.debug("Loading catalog asynchronously")
            coordinator.catalog = await async_load_catalog()
            coordinator.enabled_entities = coordinator.catalog.get_enabled_entities()
            setup_logger.info(
                "Catalog loaded successfully with %d enabled entities",
                len(coordinator.enabled_entities)
            )
        except Exception as ex:
            setup_logger.error("Failed to load catalog: %s", ex)
            raise ConfigEntryNotReady(f"Failed to load catalog: {ex}")
        
        # Test connection
        try:
            setup_logger.debug(
                "Testing connection for entry %s",
                entry.entry_id
            )
            connection_result = await coordinator.async_test_connection()
            if not connection_result:
                setup_logger.error(
                    "Connection test failed for entry %s",
                    entry.entry_id
                )
                return False
            setup_logger.info(
                "Connection test successful for entry %s",
                entry.entry_id
            )
        except ConfigEntryNotReady:
            setup_logger.warning(
                "ConfigEntryNotReady during setup for entry %s",
                entry.entry_id
            )
            raise
        except Exception as ex:
            setup_logger.error(
                "Connection test exception for entry %s: %s",
                entry.entry_id, ex, exc_info=True
            )
            raise ConfigEntryNotReady(f"Failed to connect to SVK Heatpump: {ex}")
        
        # Store coordinator
        hass.data[DOMAIN][entry.entry_id] = coordinator
        setup_logger.debug(
            "Coordinator stored for entry %s",
            entry.entry_id
        )
        
        # Perform first data refresh
        try:
            setup_logger.debug(
                "Performing first data refresh for entry %s",
                entry.entry_id
            )
            await coordinator.async_config_entry_first_refresh()
            setup_logger.info(
                "First data refresh successful for entry %s",
                entry.entry_id
            )
        except Exception as ex:
            setup_logger.error(
                "First data refresh failed for entry %s: %s",
                entry.entry_id, ex, exc_info=True
            )
            raise ConfigEntryNotReady(f"Failed to fetch initial data: {ex}")

        # Setup platforms
        try:
            setup_logger.debug(
                "Setting up platforms for entry %s",
                entry.entry_id
            )
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
            setup_logger.info(
                "Platforms setup successful for entry %s",
                entry.entry_id
            )
        except Exception as ex:
            setup_logger.error(
                "Platform setup failed for entry %s: %s",
                entry.entry_id, ex, exc_info=True
            )
            # Don't raise here - platforms might be set up partially
        
        # Register services
        try:
            setup_logger.debug(
                "Setting up services for entry %s",
                entry.entry_id
            )
            await _async_setup_services(hass, coordinator)
            setup_logger.info(
                "Services setup successful for entry %s",
                entry.entry_id
            )
        except Exception as ex:
            setup_logger.error(
                "Service setup failed for entry %s: %s",
                entry.entry_id, ex, exc_info=True
            )
            # Don't raise here - services might be set up partially
        
        # Register update listener for configuration changes
        try:
            entry.async_on_unload(entry.add_update_listener(async_reload_entry))
            setup_logger.debug(
                "Update listener registered for entry %s",
                entry.entry_id
            )
        except Exception as ex:
            setup_logger.error(
                "Failed to register update listener for entry %s: %s",
                entry.entry_id, ex
            )
        
        # Register cleanup function
        try:
            entry.async_on_unload(coordinator.async_shutdown)
            entry.async_on_unload(lambda: _async_unload_services(hass))
            setup_logger.debug(
                "Cleanup functions registered for entry %s",
                entry.entry_id
            )
        except Exception as ex:
            setup_logger.error(
                "Failed to register cleanup functions for entry %s: %s",
                entry.entry_id, ex
            )

        setup_logger.info(
            "Setup completed successfully for entry %s",
            entry.entry_id
        )
        return True
        
    except Exception as ex:
        setup_logger.error(
            "Setup failed for entry %s: %s",
            entry.entry_id, ex, exc_info=True
        )
        return False


async def async_get_options_flow(
    config_entry: ConfigEntry,
) -> SVKHeatpumpOptionsFlow:
    """Create the options flow."""
    return SVKHeatpumpOptionsFlow(config_entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    import logging
    unload_logger = logging.getLogger(__name__ + ".unload")
    
    unload_logger.info(
        "Unloading SVK Heatpump integration for entry %s",
        entry.entry_id
    )
    
    try:
        # Unload platforms
        unload_logger.debug(
            "Unloading platforms for entry %s",
            entry.entry_id
        )
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        
        if unload_ok:
            unload_logger.info(
                "Platforms unloaded successfully for entry %s",
                entry.entry_id
            )
        else:
            unload_logger.warning(
                "Some platforms failed to unload for entry %s",
                entry.entry_id
            )
        
        # Remove coordinator
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN].pop(entry.entry_id)
            if coordinator:
                unload_logger.debug(
                    "Shutting down coordinator for entry %s",
                    entry.entry_id
                )
                await coordinator.async_shutdown()
                unload_logger.info(
                    "Coordinator shut down for entry %s",
                    entry.entry_id
                )
            else:
                unload_logger.warning(
                    "Coordinator not found for entry %s",
                    entry.entry_id
                )
        else:
            unload_logger.warning(
                "Domain data not found for entry %s",
                entry.entry_id
            )

        unload_logger.info(
            "Unload completed for entry %s",
            entry.entry_id
        )
        return unload_ok
        
    except Exception as ex:
        unload_logger.error(
            "Unload failed for entry %s: %s",
            entry.entry_id, ex, exc_info=True
        )
        return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    import logging
    reload_logger = logging.getLogger(__name__ + ".reload")
    
    reload_logger.info(
        "Reloading SVK Heatpump integration for entry %s",
        entry.entry_id
    )
    
    try:
        await async_unload_entry(hass, entry)
        await async_setup_entry(hass, entry)
        reload_logger.info(
            "Reload completed for entry %s",
            entry.entry_id
        )
    except Exception as ex:
        reload_logger.error(
            "Reload failed for entry %s: %s",
            entry.entry_id, ex, exc_info=True
        )


def get_coordinator(hass: HomeAssistant, entry_id: str) -> SVKDataUpdateCoordinator:
    """Get the coordinator for a config entry.
    
    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        
    Returns:
        The SVKDataUpdateCoordinator instance.
        
    Raises:
        KeyError: If the coordinator is not found.
    """
    return hass.data[DOMAIN][entry_id]


async def _async_setup_services(hass: HomeAssistant, coordinator: SVKDataUpdateCoordinator) -> None:
    """Set up the services for the SVK Heatpump integration.
    
    Args:
        hass: The Home Assistant instance.
        coordinator: The SVK data update coordinator.
    """
    # Register the set_value service
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VALUE,
        async_set_value_service,
        schema=_get_set_value_service_schema(),
        supports_response=True,
    )


async def _async_unload_services(hass: HomeAssistant) -> None:
    """Unload the services for the SVK Heatpump integration.
    
    Args:
        hass: The Home Assistant instance.
    """
    # Unregister the set_value service
    if hass.services.has_service(DOMAIN, SERVICE_SET_VALUE):
        hass.services.async_remove(DOMAIN, SERVICE_SET_VALUE)


def _get_set_value_service_schema():
    """Get the schema for the set_value service.
    
    Returns:
        The service schema.
    """
    import voluptuous as vol
    
    return vol.Schema({
        vol.Exclusive("entity_id", "entity"): vol.Any(str, [str]),
        vol.Exclusive("id", "entity"): str,
        vol.Required("value"): vol.Any(str, int, float, bool),
    })


async def async_set_value_service(call: ServiceCall) -> Dict[str, Any]:
    """Handle the set_value service call.
    
    Args:
        call: The service call.
        
    Returns:
        A dictionary with the service result.
        
    Raises:
        HomeAssistantError: If an error occurs during the operation.
    """
    import logging
    service_logger = logging.getLogger(__name__ + ".service")
    
    hass = call.hass
    data = call.data
    
    # Get parameters
    entity_id_param = data.get("entity_id")
    id_param = data.get("id")
    value = data["value"]
    
    service_logger.info(
        "Set value service called: entity_id=%s, id=%s, value=%s",
        entity_id_param, id_param, value
    )
    
    # Validate that either entity_id or id is provided
    if not entity_id_param and not id_param:
        error_msg = "Either 'entity_id' or 'id' must be provided"
        service_logger.error("Service call failed: %s", error_msg)
        raise HomeAssistantError(error_msg)
    
    # Check if DOMAIN is in hass.data
    if DOMAIN not in hass.data:
        error_msg = f"Domain {DOMAIN} not found in hass.data"
        service_logger.error("Service call failed: %s", error_msg)
        raise HomeAssistantError(error_msg)
    
    # Find the coordinator for the relevant config entry
    coordinators = [
        coordinator for coordinator in hass.data[DOMAIN].values()
        if isinstance(coordinator, SVKDataUpdateCoordinator)
    ]
    
    if not coordinators:
        error_msg = "No SVK Heatpump coordinators found. Is the integration configured?"
        service_logger.error("Service call failed: %s", error_msg)
        raise HomeAssistantError(error_msg)
    
    # For now, we'll use the first coordinator found
    # In a more complex setup, we might need to match entities to specific coordinators
    coordinator = coordinators[0]
    
    # Check if coordinator is in a state that allows writes
    if coordinator.is_reauth_in_progress():
        error_msg = "Cannot write values while reauthentication is in progress"
        service_logger.warning("Service call failed: %s", error_msg)
        raise HomeAssistantError(error_msg)
    
    # Prepare results
    results = {
        "success": [],
        "failed": [],
        "errors": []
    }
    
    try:
        # Handle entity_id parameter (can be a single entity or a list)
        if entity_id_param:
            entity_ids = (
                [entity_id_param]
                if isinstance(entity_id_param, str)
                else entity_id_param
            )
            
            service_logger.debug("Processing %d entity IDs: %s", len(entity_ids), entity_ids[:5])
            
            for entity_id in entity_ids:
                try:
                    # Extract the entity ID from the Home Assistant entity ID
                    # Format: svk_heatpump.<host>_<id>
                    if "." not in entity_id:
                        error_msg = f"Invalid entity ID format: {entity_id}"
                        service_logger.error("Entity ID validation failed: %s", error_msg)
                        raise HomeAssistantError(error_msg)
                    
                    # Get the unique ID part after the domain
                    unique_id_part = entity_id.split(".", 1)[1]
                    
                    # Extract the catalog ID from the unique ID
                    # Format: <host>_<id>
                    if "_" not in unique_id_part:
                        error_msg = f"Invalid unique ID format: {unique_id_part}"
                        service_logger.error("Unique ID validation failed: %s", error_msg)
                        raise HomeAssistantError(error_msg)
                    
                    catalog_id = unique_id_part.split("_", 1)[1]
                    
                    service_logger.debug(
                        "Writing value %s to entity %s (catalog ID: %s)",
                        value, entity_id, catalog_id
                    )
                    
                    # Write the value
                    success = await coordinator.async_write_value(catalog_id, value)
                    
                    if success:
                        results["success"].append(entity_id)
                        service_logger.info("Successfully wrote value to entity %s", entity_id)
                    else:
                        results["failed"].append(entity_id)
                        error_msg = f"Failed to write value to {entity_id}"
                        results["errors"].append(error_msg)
                        service_logger.warning(error_msg)
                        
                except HomeAssistantError:
                    # Re-raise HomeAssistantError as is
                    raise
                except Exception as ex:
                    error_msg = f"Error with {entity_id}: {str(ex)}"
                    results["failed"].append(entity_id)
                    results["errors"].append(error_msg)
                    service_logger.error("Entity processing error: %s", error_msg)
        
        # Handle id parameter (direct catalog ID)
        elif id_param:
            try:
                service_logger.debug(
                    "Writing value %s directly to catalog ID %s",
                    value, id_param
                )
                
                # Write the value directly using the catalog ID
                success = await coordinator.async_write_value(id_param, value)
                
                if success:
                    # Create the entity ID for the result
                    host_sanitized = coordinator.host.replace(".", "_").replace(":", "_").replace("-", "_")
                    entity_id = f"{DOMAIN}.{host_sanitized}_{id_param}"
                    results["success"].append(entity_id)
                    service_logger.info(
                        "Successfully wrote value to catalog ID %s", id_param
                    )
                else:
                    results["failed"].append(id_param)
                    error_msg = f"Failed to write value to entity with ID {id_param}"
                    results["errors"].append(error_msg)
                    service_logger.warning(error_msg)
                    
            except HomeAssistantError:
                # Re-raise HomeAssistantError as is
                raise
            except Exception as ex:
                error_msg = f"Error with ID {id_param}: {str(ex)}"
                results["failed"].append(id_param)
                results["errors"].append(error_msg)
                service_logger.error("Catalog ID processing error: %s", error_msg)
                
    except HomeAssistantError:
        # Re-raise HomeAssistantError as is
        service_logger.error("Service call failed with HomeAssistantError")
        raise
    except Exception as ex:
        # Catch any other unexpected errors
        error_msg = f"Unexpected error: {str(ex)}"
        service_logger.error("Service call failed with unexpected error: %s", error_msg, exc_info=True)
        raise HomeAssistantError(error_msg)
    
    # Log summary
    service_logger.info(
        "Service call completed: %d successful, %d failed",
        len(results["success"]),
        len(results["failed"])
    )
    
    # Return the results
    return {
        "success": results["success"],
        "failed": results["failed"],
        "errors": results["errors"],
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"])
    }