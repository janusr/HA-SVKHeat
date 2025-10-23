"""Data coordinator for SVK Heatpump integration."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import (
    LOMJsonClient,
    SVKConnectionError,
    SVKAuthenticationError,
    SVKParseError,
    SVKHeatpumpParser,
)
from .const import (
    CONF_ENABLE_COUNTERS,
    CONF_ENABLE_SOLAR,
    CONF_ENABLE_WRITES,
    CONF_ID_LIST,
    DEFAULT_IDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PAGES,
    HEATPUMP_STATES,
    SEASON_MODES,
    parse_id_list,
    parse_items,
)


def _get_constants():
    """Lazy import of constants to prevent blocking during async setup."""
    from .const import ID_MAP, DEFAULT_ENABLED_ENTITIES
    return ID_MAP, DEFAULT_ENABLED_ENTITIES


_LOGGER = logging.getLogger(__name__)


class SVKHeatpumpDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the SVK Heatpump."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        client,  # Can be either SVKHeatpumpClient or LOMJsonClient
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        config_entry=None
    ):
        """Initialize."""
        self.client = client
        self.config_entry = config_entry
        self.is_json_client = isinstance(client, LOMJsonClient)
        
        # For backward compatibility with HTML scraping
        if not self.is_json_client:
            self.parser = SVKHeatpumpParser()
        
        # Initialize ID list for JSON API
        if self.is_json_client:
            # Always use DEFAULT_IDS for fetching all available entities
            # This ensures we have access to all entities for dynamic enabling/disabling
            self.id_list = parse_id_list(DEFAULT_IDS)
            
            # Store the user-configured ID list for backward compatibility
            self.user_configured_ids = None
            if config_entry and CONF_ID_LIST in config_entry.options:
                id_list_str = config_entry.options[CONF_ID_LIST]
                try:
                    self.user_configured_ids = parse_id_list(id_list_str)
                except ValueError as err:
                    _LOGGER.warning("Invalid ID list in config, ignoring: %s", err)
            
            # Create reverse mapping for efficient lookups
            self.id_to_entity_map = {}
            ID_MAP, _ = _get_constants()
            for entity_id, (entity_key, unit, device_class, state_class, original_name) in ID_MAP.items():
                self.id_to_entity_map[entity_id] = {
                    "key": entity_key,
                    "unit": unit,
                    "device_class": device_class,
                    "state_class": state_class,
                    "original_name": original_name
                }
            
            # Store last-good values
            self.last_good_values = {}
            
            # Store raw JSON data for diagnostics
            self.last_raw_json = None
            self.last_json_timestamp = None
            self.parsing_errors = []
            self.parsing_warnings = []
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        
        # Initialize device info for centralized device registration
        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id) if config_entry else (DOMAIN, "svk_heatpump")},
            name="SVK Heatpump",
            manufacturer="SVK",
            model="LMC320",
        )
    
    async def _async_update_data(self):
        """Update data via library."""
        try:
            _LOGGER.debug("Starting data update cycle")
            # Add overall timeout protection to prevent blocking the event loop
            # Reduced timeout to 30 seconds to prevent long blocking periods
            return await asyncio.wait_for(
                self._async_update_data_internal(),
                timeout=30.0  # 30 second timeout for full update cycle
            )
        except asyncio.TimeoutError:
            _LOGGER.error("Data update timed out after 30 seconds - this may be blocking Home Assistant")
            raise UpdateFailed("Data update timeout after 30 seconds - heat pump may be unreachable")
    
    async def _async_update_data_internal(self):
        """Internal method for data update with retry logic."""
        try:
            # Start the client session if not already started
            await self.client.start()
            
            # Use JSON API if available
            if self.is_json_client:
                return await self._update_data_json()
            else:
                # Fall back to HTML scraping for backward compatibility
                return await self._update_data_html()
                
        except SVKAuthenticationError as err:
            # Provide helpful error message for authentication issues
            error_msg = str(err)
            if "does not support Digest authentication" in error_msg:
                _LOGGER.error("Device at %s returned unexpected auth scheme (not Digest)", self.client.host)
                _LOGGER.error("Please check if your device supports Digest authentication or enable 'Allow Basic Auth (Legacy)' option")
                raise UpdateFailed(f"Unexpected auth scheme from device. Please check if your device supports Digest authentication or enable 'Allow Basic Auth (Legacy)' option.") from err
            elif "Invalid username or password" in error_msg:
                _LOGGER.error("Digest authentication failed with SVK Heatpump: %s", err)
                _LOGGER.error("Please check your username and password in the integration configuration")
                raise UpdateFailed(f"Invalid username or password. Please check your credentials.") from err
            elif "stale" in error_msg.lower():
                _LOGGER.warning("Digest authentication nonce was stale, this should be handled automatically: %s", err)
                # Stale nonce should be handled automatically by the client, but if it persists, we need to re-auth
                raise UpdateFailed(f"Authentication nonce expired. Please try reconfiguring the integration.") from err
            else:
                _LOGGER.error("Authentication failed with SVK Heatpump: %s", err)
                _LOGGER.error("Please check your username and password in the integration configuration")
                raise UpdateFailed(f"Authentication failed: {err}. Please check your credentials.") from err
        except SVKConnectionError as err:
            raise UpdateFailed(f"Error communicating with SVK Heatpump: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
    
    async def _update_data_json(self):
        """Update data using JSON API."""
        try:
            # Clear previous parsing errors and warnings
            self.parsing_errors = []
            self.parsing_warnings = []
            
            _LOGGER.info("Starting JSON data update with %d IDs", len(self.id_list))
            _LOGGER.debug("Requesting IDs: %s", self.id_list[:20])  # Log first 20 IDs
            
            # Read all available entities from DEFAULT_IDS
            _LOGGER.debug("About to call client.read_values - this is a potential blocking point")
            json_data = await self.client.read_values(self.id_list)
            _LOGGER.debug("Returned from client.read_values - got %d items", len(json_data) if json_data else 0)
            
            _LOGGER.info("Received raw JSON data with %d items", len(json_data) if json_data else 0)
            _LOGGER.debug("Raw JSON data sample: %s", json_data[:5] if json_data and len(json_data) > 0 else "None")
            
            if not json_data:
                _LOGGER.error("CRITICAL: No data received from JSON API - this indicates a communication or authentication failure")
                _LOGGER.error("This is likely the root cause of entities not updating")
                # Instead of returning empty data, raise UpdateFailed to trigger proper error handling
                raise UpdateFailed("No data received from JSON API - check authentication and network connectivity")
            
            # Store raw JSON data for diagnostics (redact only credentials)
            self.last_raw_json = json_data
            self.last_json_timestamp = datetime.now(timezone.utc)
            
            # Parse the array of items using the new parse_items function
            try:
                parsed_items = parse_items(json_data)
            except Exception as err:
                self.parsing_errors.append(f"JSON parsing failed: {err}")
                raise UpdateFailed(f"JSON parsing failed: {err}") from err
            
            if not parsed_items:
                self.parsing_errors.append("No valid items could be parsed from JSON response")
                _LOGGER.error("CRITICAL: No valid items could be parsed from JSON response. Raw data: %s", json_data[:10] if json_data else "None")
                _LOGGER.error("This indicates either a JSON parsing failure or unexpected data format from the heat pump")
                # Raise UpdateFailed instead of returning empty data to ensure proper error reporting
                raise UpdateFailed("No valid items could be parsed from JSON response - check heat pump compatibility")
            
            # Map parsed items to entity data
            data = {}
            ids_fetched = []
            
            unknown_ids = []
            sentinel_temps = []
            clamped_percentages = []
            
            _LOGGER.info("Processing %d parsed items", len(parsed_items))
            
            for entity_id, (name, value) in parsed_items.items():
                ids_fetched.append(entity_id)
                
                # Skip unknown IDs
                if entity_id not in self.id_to_entity_map:
                    unknown_ids.append({"id": entity_id, "name": name, "value": value})
                    _LOGGER.debug("Unknown entity ID %s with name %s and value %s", entity_id, name, value)
                    continue
                
                entity_info = self.id_to_entity_map[entity_id]
                entity_key = entity_info["key"]
                _LOGGER.debug("Processing entity ID %s -> %s = %s", entity_id, entity_key, value)
                
                entity_info = self.id_to_entity_map[entity_id]
                entity_key = entity_info["key"]
                
                # Handle different data types
                if value is None:
                    # Skip null values but keep last-good value if available
                    if entity_key in self.last_good_values:
                        data[entity_key] = self.last_good_values[entity_key]
                    continue
                
                # Apply temperature sentinel rule
                if entity_info.get("device_class") == "temperature":
                    if isinstance(value, (int, float)) and value <= -50.0:
                        sentinel_temps.append({"entity": entity_key, "id": entity_id, "value": value})
                        _LOGGER.debug("Entity %s: Temperature %s°C ≤ -50.0°C, marking unavailable", entity_key, value)
                        data[entity_key] = None
                        continue
                
                # Store the value
                if entity_key == "heatpump_state":
                    # Map enum value for heatpump state
                    data[entity_key] = self._map_heatpump_state(value)
                elif entity_key == "season_mode":
                    # Map enum value for season mode
                    data[entity_key] = self._map_season_mode(value)
                else:
                    # Apply value sanitation based on entity type
                    sanitized_value = self._sanitize_value(entity_key, value, entity_info)
                    
                    # Track percentage clamping
                    if entity_info.get("unit") == "%" and isinstance(value, (int, float)):
                        if isinstance(sanitized_value, (int, float)) and sanitized_value != float(value):
                            clamped_percentages.append({
                                "entity": entity_key,
                                "id": entity_id,
                                "original": value,
                                "clamped": sanitized_value
                            })
                    
                    data[entity_key] = sanitized_value
                
                # Store last-good value
                if data[entity_key] is not None:
                    self.last_good_values[entity_key] = data[entity_key]
            
            # Add metadata
            data["last_update"] = datetime.now(timezone.utc)
            data["ids_fetched"] = ids_fetched
            
            # Store parsing statistics for diagnostics
            data["parsing_stats"] = {
                "total_ids_requested": len(self.id_list),
                "total_ids_received": len(json_data) if isinstance(json_data, list) else 0,
                "total_ids_fetched": len(ids_fetched),
                "unknown_ids_count": len(unknown_ids),
                "sentinel_temps_count": len(sentinel_temps),
                "clamped_percentages_count": len(clamped_percentages),
                "successful_parses": len([k for k, v in data.items() if v is not None and not k.startswith("last_") and not k.startswith("ids_") and not k.startswith("parsing_")]),
                "enabled_entities_count": len([eid for eid in self.id_to_entity_map if self.is_entity_enabled(eid)]),
                "disabled_entities_count": len([eid for eid in self.id_to_entity_map if not self.is_entity_enabled(eid)])
            }
            
            # Store detailed parsing information for diagnostics
            data["parsing_details"] = {
                "unknown_ids": unknown_ids,
                "sentinel_temps": sentinel_temps,
                "clamped_percentages": clamped_percentages
            }
            
            if not data:
                self.parsing_errors.append("No valid data could be parsed from JSON response")
                _LOGGER.error("No valid data could be parsed from JSON response - raising UpdateFailed to ensure proper error reporting")
                # Raise UpdateFailed instead of returning empty data to ensure proper error reporting
                raise UpdateFailed("No valid data could be parsed from JSON response - all entities unavailable")
            
            _LOGGER.info("Successfully parsed %d entities from JSON data", len(data))
            _LOGGER.debug("Parsed entities: %s", list(data.keys())[:20])  # Log first 20 entity keys
            return data
            
        except Exception as err:
            _LOGGER.error("JSON API update failed: %s", err)
            _LOGGER.error("Raising UpdateFailed to ensure proper error reporting instead of returning empty data")
            self.parsing_errors.append(f"JSON API update failed: {err}")
            # Raise UpdateFailed instead of returning empty data to ensure proper error reporting
            raise UpdateFailed(f"JSON API update failed: {err}") from err
    
    async def _update_data_html(self):
        """Update data using HTML scraping (backward compatibility)."""
        # Fetch all pages using the new client implementation
        pages_html = {}
        
        # Fetch display page
        try:
            display_html = await self.client.get_display()
            if display_html:
                pages_html["display"] = display_html
        except Exception as err:
            _LOGGER.warning("Failed to fetch display page: %s", err)
        
        # Fetch user page
        try:
            user_html = await self.client.get_user()
            if user_html:
                pages_html["user"] = user_html
        except Exception as err:
            _LOGGER.warning("Failed to fetch user page: %s", err)
        
        # Fetch heating page
        try:
            heating_html = await self.client.get_heating()
            if heating_html:
                pages_html["heating"] = heating_html
        except Exception as err:
            _LOGGER.warning("Failed to fetch heating page: %s", err)
        
        # Fetch heatpump page
        try:
            heatpump_html = await self.client.get_heatpump()
            if heatpump_html:
                pages_html["heatpump"] = heatpump_html
        except Exception as err:
            _LOGGER.warning("Failed to fetch heatpump page: %s", err)
        
        # Fetch solar page (if enabled)
        if self.config_entry and self.config_entry.options.get(CONF_ENABLE_SOLAR, True):
            try:
                solar_html = await self.client.get_solar()
                if solar_html:
                    pages_html["solar"] = solar_html
            except Exception as err:
                _LOGGER.warning("Failed to fetch solar page: %s", err)
        
        # Fetch hot water page
        try:
            hotwater_html = await self.client.get_hotwater()
            if hotwater_html:
                pages_html["hotwater"] = hotwater_html
        except Exception as err:
            _LOGGER.warning("Failed to fetch hotwater page: %s", err)
        
        if not pages_html:
            raise UpdateFailed("No pages could be retrieved from the device")
        
        # Parse all pages
        data = {}
        
        # Parse display page
        if "display" in pages_html:
            try:
                display_data = self.parser.parse_display_page(pages_html["display"])
                data.update(display_data)
                _LOGGER.debug("Parsed display page: %s", display_data)
            except SVKParseError as err:
                _LOGGER.error("Failed to parse display page: %s", err)
        
        # Parse user page
        if "user" in pages_html:
            try:
                user_data = self.parser.parse_user_page(pages_html["user"])
                data.update(user_data)
                _LOGGER.debug("Parsed user page: %s", user_data)
            except SVKParseError as err:
                _LOGGER.error("Failed to parse user page: %s", err)
        
        # Parse heating page
        if "heating" in pages_html:
            try:
                heating_data = self.parser.parse_heating_page(pages_html["heating"])
                data.update(heating_data)
                _LOGGER.debug("Parsed heating page: %s", heating_data)
            except SVKParseError as err:
                _LOGGER.error("Failed to parse heating page: %s", err)
        
        # Parse heatpump page
        if "heatpump" in pages_html:
            try:
                heatpump_data = self.parser.parse_heatpump_page(pages_html["heatpump"])
                data.update(heatpump_data)
                _LOGGER.debug("Parsed heatpump page: %s", heatpump_data)
            except SVKParseError as err:
                _LOGGER.error("Failed to parse heatpump page: %s", err)
        
        # Parse solar page (if enabled)
        if "solar" in pages_html:
            try:
                solar_data = self.parser.parse_solar_page(pages_html["solar"])
                data.update(solar_data)
                _LOGGER.debug("Parsed solar page: %s", solar_data)
            except SVKParseError as err:
                _LOGGER.error("Failed to parse solar page: %s", err)
        
        # Parse hot water page
        if "hotwater" in pages_html:
            try:
                hotwater_data = self.parser.parse_hotwater_page(pages_html["hotwater"])
                data.update(hotwater_data)
                _LOGGER.debug("Parsed hot water page: %s", hotwater_data)
            except SVKParseError as err:
                _LOGGER.error("Failed to parse hot water page: %s", err)
        
        # Add metadata
        data["last_update"] = datetime.now(timezone.utc)
        data["pages_fetched"] = list(pages_html.keys())
        
        if not data:
            raise UpdateFailed("No data could be parsed from any page")
        
        _LOGGER.debug("Total data parsed: %d items", len(data))
        return data
    
    def _map_heatpump_state(self, value):
        """Map heatpump state enum value."""
        # Handle numeric enum values
        if isinstance(value, (int, float)):
            # Map numeric values to states (this would need to be based on actual device enum table)
            state_mapping = {
                0: "off",
                1: "ready",
                2: "start_up",
                3: "heating",
                4: "hot_water",
                5: "el_heating",
                6: "defrost",
                7: "drip_delay",
                8: "total_stop",
                9: "pump_exercise",
                10: "forced_running",
                11: "manual"
            }
            return state_mapping.get(int(value), "unknown")
        
        # Handle string enum values
        if isinstance(value, str):
            # Try to map using existing HEATPUMP_STATES
            for state_text, state_value in HEATPUMP_STATES.items():
                if state_text.lower() in value.lower():
                    return state_value
            return value.lower()
        
        return "unknown"
    
    def _map_season_mode(self, value):
        """Map season mode enum value."""
        # Handle numeric enum values
        if isinstance(value, (int, float)):
            # Map numeric values to modes
            mode_mapping = {
                0: "winter",
                1: "summer",
                2: "auto"
            }
            return mode_mapping.get(int(value), "unknown")
        
        # Handle string enum values
        if isinstance(value, str):
            # Try to map using existing SEASON_MODES
            for mode_text, mode_value in SEASON_MODES.items():
                if mode_text.lower() in value.lower():
                    return mode_value
            return value.lower()
        
        return "unknown"
    
    async def async_set_parameter(self, parameter: str, value) -> bool:
        """Set a parameter value."""
        try:
            if self.is_json_client:
                # For JSON API, we need to find the entity ID for this parameter
                entity_id = None
                for eid, info in self.id_to_entity_map.items():
                    if info["key"] == parameter:
                        entity_id = eid
                        break
                
                if entity_id is None:
                    _LOGGER.error("Unknown parameter for JSON API: %s", parameter)
                    return False
                
                # Write the value using the JSON API
                success = await self.client.write_value(entity_id, value)
                
                if success:
                    # Trigger a refresh to get the updated value
                    await self.async_request_refresh()
                    return True
                else:
                    return False
            else:
                # Use the HTML scraping method for backward compatibility
                success = await self.client.set_parameter(parameter, value)
                
                if success:
                    # Trigger a refresh to get the updated value
                    await self.async_request_refresh()
                    return True
                else:
                    return False
                
        except Exception as err:
            _LOGGER.error("Failed to set %s to %s: %s", parameter, value, err)
            return False
    
    def get_enabled_entities(self, config_entry):
        """Get list of enabled entities based on configuration."""
        # If using JSON API, return entities based on DEFAULT_ENABLED_ENTITIES
        if self.is_json_client:
            enabled_entities = []
            
            # Check if user has configured a custom ID list (backward compatibility)
            if self.user_configured_ids:
                # Use the user's configured ID list
                for entity_id in self.user_configured_ids:
                    if entity_id in self.id_to_entity_map:
                        entity_key = self.id_to_entity_map[entity_id]["key"]
                        enabled_entities.append(entity_key)
            else:
                # Use DEFAULT_ENABLED_ENTITIES as the default enabled entities
                _, DEFAULT_ENABLED_ENTITIES = _get_constants()
                for entity_id in DEFAULT_ENABLED_ENTITIES:
                    if entity_id in self.id_to_entity_map:
                        entity_key = self.id_to_entity_map[entity_id]["key"]
                        enabled_entities.append(entity_key)
            
            return enabled_entities
        
        # Fall back to HTML scraping entities for backward compatibility
        enabled_entities = []
        
        # Always include basic entities
        enabled_entities.extend([
            "heating_supply_temp",
            "heating_return_temp",
            "water_tank_temp",
            "ambient_temp",
            "room_temp",
            "heating_setpoint",
            "hot_water_setpoint",
            "heatpump_state",
            "alarm_active",
            "compressor_speed_v",
            "compressor_speed_percent",
            "requested_capacity",
            "actual_capacity",
            "ip_address",
            "software_version",
        ])
        
        # Add optional entities based on configuration
        options = config_entry.options
        
        if options.get(CONF_ENABLE_SOLAR, True):
            enabled_entities.extend([
                "solar_collector_temp",
                "solar_water_temp",
                "solar_panel_state",
            ])
        
        if options.get(CONF_ENABLE_COUNTERS, True):
            enabled_entities.extend([
                "compressor_runtime",
                "heater_runtime",
                "pump_runtime",
            ])
        
        # Add additional temperature sensors if available
        additional_temps = [
            "heating_tank_temp",
            "cold_side_supply_temp",
            "cold_side_return_temp",
            "evaporator_temp",
        ]
        enabled_entities.extend(additional_temps)
        
        # Add performance sensors
        performance_sensors = [
            "cold_pump_speed",
        ]
        enabled_entities.extend(performance_sensors)
        
        # Add system info
        system_info = [
            "log_interval",
        ]
        enabled_entities.extend(system_info)
        
        # Add control entities if writes are enabled
        if options.get(CONF_ENABLE_WRITES, False):
            enabled_entities.extend([
                "season_mode",
                "hot_water_setpoint_control",
                "room_setpoint_control",
            ])
        
        return enabled_entities
    
    def is_entity_enabled(self, entity_id: int, config_entry=None) -> bool:
        """Check if an entity should be enabled based on configuration.
        
        Args:
            entity_id: The entity ID to check
            config_entry: The config entry (optional)
            
        Returns:
            True if the entity should be enabled, False otherwise
        """
        # If user has configured a custom ID list, use that for backward compatibility
        if self.user_configured_ids:
            return entity_id in self.user_configured_ids
        
        # Otherwise, check if the entity is in DEFAULT_ENABLED_ENTITIES
        _, DEFAULT_ENABLED_ENTITIES = _get_constants()
        return entity_id in DEFAULT_ENABLED_ENTITIES
    
    def get_entity_value(self, entity_key: str):
        """Get the current value for an entity."""
        if not self.data:
            return None
        
        # Handle special cases
        if entity_key == "hot_water_setpoint_control":
            return self.data.get("hot_water_setpoint")
        elif entity_key == "room_setpoint_control":
            # This might not be directly available, could be derived
            return self.data.get("room_setpoint")
        
        return self.data.get(entity_key)
    
    def is_entity_available(self, entity_key: str) -> bool:
        """Check if an entity is available."""
        # For JSON API, don't require successful update to consider entities available
        # This allows entities to be created even if initial data fetch fails
        if not self.is_json_client:
            if not self.last_update_success:
                _LOGGER.debug("Entity %s not available - last update failed for non-JSON client", entity_key)
                return False
            
            if not self.data:
                _LOGGER.debug("Entity %s not available - no data for non-JSON client", entity_key)
                return False
        
        # For JSON API, check if the entity exists in the mapping
        if self.is_json_client:
            # Find the entity ID for this entity key
            entity_id = None
            for eid, info in self.id_to_entity_map.items():
                if info["key"] == entity_key:
                    entity_id = eid
                    break
            
            if entity_id is not None:
                # Entity is considered available if it exists in the mapping,
                # regardless of whether it had data in the last response
                # This ensures entities are created even if initial data fetching fails
                _LOGGER.debug("Entity %s (ID: %s) is available - exists in mapping (JSON API)", entity_key, entity_id)
                return True
            else:
                _LOGGER.debug("Entity %s is not available - not found in mapping", entity_key)
                return False
        
        # Check if the entity has a value
        value = self.get_entity_value(entity_key)
        is_available = value is not None
        _LOGGER.debug("Entity %s availability: %s (value: %s)", entity_key, is_available, value)
        return is_available
    
    def get_all_entities_data(self) -> dict:
        """Get data for all available entities, including disabled ones.
        
        Returns:
            Dictionary with all entity data, including enabled/disabled status
        """
        if not self.is_json_client or not self.data:
            return {}
        
        all_entities = {}
        
        for entity_id, entity_info in self.id_to_entity_map.items():
            entity_key = entity_info["key"]
            entity_data = {
                "key": entity_key,
                "id": entity_id,
                "name": entity_info["original_name"],
                "unit": entity_info["unit"],
                "device_class": entity_info["device_class"],
                "state_class": entity_info["state_class"],
                "enabled": self.is_entity_enabled(entity_id),
                "available": self.is_entity_available(entity_key),
                "value": self.get_entity_value(entity_key) if self.is_entity_available(entity_key) else None
            }
            all_entities[entity_key] = entity_data
        
        return all_entities
    
    def get_entity_info(self, entity_key: str):
        """Get entity information (unit, device_class, state_class, original_name) for JSON API."""
        if not self.is_json_client:
            return None
        
        # Find the entity info for this entity key
        for entity_id, info in self.id_to_entity_map.items():
            if info["key"] == entity_key:
                return {
                    "entity_id": entity_id,
                    "unit": info["unit"],
                    "device_class": info["device_class"],
                    "state_class": info["state_class"],
                    "original_name": info["original_name"]
                }
        
        return None
    
    def get_alarm_summary(self) -> dict:
        """Get a summary of active alarms."""
        if not self.data:
            return {"active": False, "count": 0, "alarms": []}
        
        alarm_active = self.data.get("alarm_active", False)
        alarm_list = self.data.get("alarm_list", [])
        
        return {
            "active": alarm_active,
            "count": len(alarm_list),
            "alarms": alarm_list,
        }
    
    def get_system_status(self) -> dict:
        """Get overall system status."""
        if not self.data:
            return {"status": "unknown", "state": "unknown"}
        
        heatpump_state = self.data.get("heatpump_state", "unknown")
        alarm_active = self.data.get("alarm_active", False)
        
        # Determine overall status
        if alarm_active:
            status = "alarm"
        elif heatpump_state == "off":
            status = "off"
        elif heatpump_state in ["heating", "hot_water", "el_heating"]:
            status = "active"
        elif heatpump_state in ["ready", "start_up"]:
            status = "standby"
        else:
            status = heatpump_state
        
        return {
            "status": status,
            "state": heatpump_state,
            "alarm_active": alarm_active,
        }
    
    def _sanitize_value(self, entity_key: str, value, entity_info: dict):
        """Sanitize values based on entity type.
        
        Args:
            entity_key: The entity key
            value: The raw value
            entity_info: Entity information dictionary
            
        Returns:
            The sanitized value
        """
        if value is None:
            return None
        
        # Temperature values - already handled sentinel rule above
        if entity_info.get("device_class") == "temperature":
            return value
        
        # Percentage values - clamp to 0-100 range
        if entity_info.get("unit") == "%":
            try:
                if isinstance(value, (int, float)):
                    return max(0, min(100, float(value)))
            except (ValueError, TypeError):
                pass
        
        # Runtime values - keep as numeric
        if entity_info.get("entity_category") == "diagnostic" and "runtime" in entity_key:
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        
        # Default: return value as-is
        return value
    
    def get_json_diagnostics(self) -> dict:
        """Get comprehensive JSON diagnostics data."""
        if not self.is_json_client:
            return {"error": "Not using JSON API"}
        
        diagnostics = {
            "json_api_enabled": True,
            "last_json_timestamp": self.last_json_timestamp,
            "id_list_configured": self.id_list,
            "id_list_count": len(self.id_list),
            "user_configured_ids": self.user_configured_ids,
            "user_configured_ids_count": len(self.user_configured_ids) if self.user_configured_ids else 0,
            "using_default_enabled_entities": self.user_configured_ids is None,
            "parsing_errors": self.parsing_errors,
            "parsing_warnings": self.parsing_warnings,
        }
        
        # Add raw JSON response if available
        if self.last_raw_json:
            diagnostics["raw_json_response"] = self.last_raw_json
            diagnostics["raw_json_size"] = len(str(self.last_raw_json))
        
        # Add parsing statistics from current data
        if self.data and "parsing_stats" in self.data:
            diagnostics["parsing_stats"] = self.data["parsing_stats"]
            diagnostics["parsing_details"] = self.data.get("parsing_details", {})
        
        # Add entity availability summary
        if self.data:
            diagnostics["entity_availability"] = self._get_entity_availability_summary()
        
        return diagnostics
    
    def _get_entity_availability_summary(self) -> dict:
        """Get summary of entity availability."""
        if not self.data:
            return {"total": 0, "available": 0, "unavailable": 0}
        
        total_entities = 0
        available_entities = 0
        unavailable_entities = 0
        enabled_entities = 0
        disabled_entities = 0
        entity_types = {
            "temperature": 0,
            "percentage": 0,
            "binary": 0,
            "power": 0,
            "energy": 0,
            "other": 0
        }
        
        for entity_id, entity_info in self.id_to_entity_map.items():
            entity_key = entity_info["key"]
            total_entities += 1
            
            # Check if entity is enabled
            is_enabled = self.is_entity_enabled(entity_id)
            if is_enabled:
                enabled_entities += 1
            else:
                disabled_entities += 1
            
            # Check if entity is available
            if self.is_entity_available(entity_key):
                available_entities += 1
                
                # Count entity types
                device_class = entity_info.get("device_class", "")
                unit = entity_info.get("unit", "")
                
                if device_class == "temperature":
                    entity_types["temperature"] += 1
                elif unit == "%":
                    entity_types["percentage"] += 1
                elif device_class in ["binary_sensor", "switch"]:
                    entity_types["binary"] += 1
                elif unit in ["W", "kW", "VA", "kVA"]:
                    entity_types["power"] += 1
                elif unit in ["kWh", "Wh"]:
                    entity_types["energy"] += 1
                else:
                    entity_types["other"] += 1
            else:
                unavailable_entities += 1
        
        return {
            "total": total_entities,
            "available": available_entities,
            "unavailable": unavailable_entities,
            "enabled": enabled_entities,
            "disabled": disabled_entities,
            "availability_percentage": round((available_entities / total_entities * 100) if total_entities > 0 else 0, 1),
            "entity_types": entity_types
        }
    
    def format_json_as_table(self) -> str:
        """Format raw JSON data as a readable table of ID → name → value."""
        if not self.last_raw_json:
            return "No raw JSON data available"
        
        if not isinstance(self.last_raw_json, list):
            return f"Raw JSON is not a list: {type(self.last_raw_json).__name__}"
        
        # Create table header
        table_lines = ["Raw JSON Data Table", "=" * 80, ""]
        table_lines.append(f"{'ID':<10} {'Name':<40} {'Value':<15} {'Unit':<10}")
        table_lines.append("-" * 80)
        
        # Sort by ID for consistent output
        sorted_items = sorted(self.last_raw_json, key=lambda x: x.get("id", ""))
        
        for item in sorted_items:
            item_id = str(item.get("id", ""))
            name = str(item.get("name", ""))[:39]  # Truncate long names
            value = str(item.get("value", ""))
            unit = str(item.get("unit", ""))[:9]  # Truncate long units
            
            table_lines.append(f"{item_id:<10} {name:<40} {value:<15} {unit:<10}")
        
        table_lines.append("")
        table_lines.append(f"Total items: {len(sorted_items)}")
        
        return "\n".join(table_lines)
    
    def get_unavailable_entities(self) -> list:
        """Get list of unavailable entities with reasons."""
        if not self.data:
            return []
        
        unavailable = []
        
        for entity_id, entity_info in self.id_to_entity_map.items():
            entity_key = entity_info["key"]
            
            if not self.is_entity_available(entity_key):
                unavailable.append({
                    "entity_key": entity_key,
                    "entity_id": entity_id,
                    "name": entity_info["original_name"],
                    "unit": entity_info["unit"],
                    "device_class": entity_info["device_class"],
                    "enabled": self.is_entity_enabled(entity_id)
                })
        
        return unavailable
    
    def get_disabled_entities(self) -> list:
        """Get list of disabled entities that are available but not enabled."""
        if not self.data:
            return []
        
        disabled = []
        
        for entity_id, entity_info in self.id_to_entity_map.items():
            entity_key = entity_info["key"]
            
            # Entity is disabled but available (we have data for it)
            if not self.is_entity_enabled(entity_id) and self.is_entity_available(entity_key):
                disabled.append({
                    "entity_key": entity_key,
                    "entity_id": entity_id,
                    "name": entity_info["original_name"],
                    "unit": entity_info["unit"],
                    "device_class": entity_info["device_class"],
                    "value": self.get_entity_value(entity_key)
                })
        
        return disabled
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return centralized device information."""
        return self._device_info