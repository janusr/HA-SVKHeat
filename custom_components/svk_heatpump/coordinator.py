"""Data coordinator for SVK Heatpump integration."""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import (
    SVKAuthenticationError,
    SVKConnectionError,
)
from .const import (
    CONF_ID_LIST,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HEATPUMP_STATES,
    SEASON_MODES,
    parse_id_list,
    parse_items,
)


def _get_constants() -> tuple[dict[int, tuple[str, str, str, str, str]], list[int]]:
    """Lazy import of constants to prevent blocking during async setup."""
    from .catalog import DEFAULT_ENABLED_ENTITIES, ID_MAP

    return ID_MAP, DEFAULT_ENABLED_ENTITIES


_LOGGER = logging.getLogger(__name__)

# Essential IDs that should be loaded first during startup
# These are the core entities needed for basic functionality
ESSENTIAL_IDS = [
    # Core temperature sensors
    253,  # heating_supply_temp
    254,  # heating_return_temp
    255,  # water_tank_temp
    256,  # ambient_temp
    257,  # room_temp
    # Heat pump state and status
    297,  # heatpump_state
    296,  # heatpump_season_state
    299,  # capacity_actual
    300,  # capacity_requested
    # Essential setpoints
    193,  # room_setpoint
    383,  # hot_water_setpoint
    386,  # hot_water_setpoint_actual
    420,  # heating_setpoint_actual
    # Operating mode
    278,  # season_mode
    # Important binary outputs
    220,  # hot_tap_water_output
    228,  # alarm_output
    # Solar panel state (if available)
    364,  # solar_panel_state
    # Hot water source
    380,  # hot_water_source
]


class SVKHeatpumpDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the SVK Heatpump."""

    def __init__(
        self,
        hass: HomeAssistant,
        client,  # LOMJsonClient
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        config_entry=None,
    ) -> None:
        """Initialize."""
        self.client = client
        self.config_entry = config_entry
        self.is_json_client = True  # Always using LOMJsonClient

        # Initialize ID list for JSON API
        if self.is_json_client:
            # Always use get_default_ids() for fetching all available entities
            # This ensures we have access to all entities for dynamic enabling/disabling
            from .catalog import get_default_ids
            self.id_list = parse_id_list(get_default_ids())

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
            for entity_id, (
                entity_key,
                unit,
                device_class,
                state_class,
                original_name,
            ) in ID_MAP.items():
                self.id_to_entity_map[entity_id] = {
                    "key": entity_key,
                    "unit": unit,
                    "device_class": device_class,
                    "state_class": state_class,
                    "original_name": original_name,
                }

            # Store last-good values
            self.last_good_values: dict[str, Any] = {}

            # Store raw JSON data for diagnostics
            self.last_raw_json = None
            self.last_json_timestamp = None
            self.parsing_errors: list[str] = []
            self.parsing_warnings: list[str] = []

            # Track if this is the first refresh for progressive loading
            self.is_first_refresh = True
            # Track if first refresh has been attempted to avoid duplicate attempts
            self.first_refresh_attempted = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

        # Initialize device info for centralized device registration
        self._device_info = DeviceInfo(
            identifiers={
                (
                    (DOMAIN, config_entry.entry_id)
                    if config_entry
                    else (DOMAIN, "svk_heatpump")
                )
            },
            name="SVK Heatpump",
            manufacturer="SVK",
            model="LMC320",
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            start_time = datetime.now()
            _LOGGER.debug("Starting data update cycle")

            # Add overall timeout protection to prevent blocking the event loop
            # Use 30 seconds for both first and subsequent refreshes for consistency
            timeout = 30.0
            _LOGGER.debug(
                "Using timeout of %.1f seconds for %s refresh",
                timeout,
                "first" if self.is_first_refresh else "subsequent",
            )

            # Add detailed timing diagnostics
            if self.is_json_client:
                id_count = (
                    len(ESSENTIAL_IDS) if self.is_first_refresh else len(self.id_list)
                )
                _LOGGER.info(
                    "PERFORMANCE: Requesting %d IDs via JSON API (%s refresh)",
                    id_count,
                    "first" if self.is_first_refresh else "subsequent",
                )

                # Log chunking configuration
                if hasattr(self.client, "_enable_chunking"):
                    chunk_size = getattr(self.client, "_chunk_size", 50)
                    chunks_needed = (id_count + chunk_size - 1) // chunk_size
                    _LOGGER.info(
                        "PERFORMANCE: Chunking enabled - size=%d, chunks_needed=%d",
                        chunk_size,
                        chunks_needed,
                    )
                else:
                    _LOGGER.info(
                        "PERFORMANCE: Chunking disabled - single request for all IDs"
                    )

            result = await asyncio.wait_for(
                self._async_update_data_internal(), timeout=timeout
            )

            # Log timing information
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            _LOGGER.info(
                "Data update completed in %.2f seconds (%s refresh)",
                duration,
                "first" if self.is_first_refresh else "subsequent",
            )

            # Performance warning if approaching timeout
            if duration > timeout * 0.8:  # 80% of timeout
                _LOGGER.warning(
                    "PERFORMANCE: Update took %.2fs (%.1f%% of timeout) - may indicate performance issue",
                    duration,
                    (duration / timeout) * 100,
                )

            # Mark first refresh as complete
            if self.is_first_refresh:
                self.is_first_refresh = False
                self.first_refresh_attempted = True
                _LOGGER.info(
                    "First refresh completed, switching to full ID list for subsequent updates"
                )

            return result
        except asyncio.TimeoutError:
            _LOGGER.error(
                "Data update timed out after %.1f seconds - this may be blocking Home Assistant",
                timeout,
            )

            # Add timeout diagnostics
            if self.is_json_client:
                _LOGGER.error(
                    "TIMEOUT: JSON API request timed out after %.1f seconds", timeout
                )
                _LOGGER.error("TIMEOUT: This may be caused by:")
                _LOGGER.error("TIMEOUT: 1) Network latency to heat pump")
                _LOGGER.error(
                    "TIMEOUT: 2) Heat pump processing too many IDs in single request"
                )
                _LOGGER.error(
                    "TIMEOUT: 3) Authentication delays (multiple round-trips)"
                )
                _LOGGER.error(
                    "TIMEOUT: 4) Chunking inefficiency (too many small requests)"
                )

                # Log current configuration for debugging
                if hasattr(self.client, "_enable_chunking"):
                    _LOGGER.error(
                        "TIMEOUT: Chunking: enabled=%s, chunk_size=%d",
                        getattr(self.client, "_enable_chunking", False),
                        getattr(self.client, "_chunk_size", 50),
                    )
                _LOGGER.error(
                    "TIMEOUT: Total IDs requested: %d",
                    len(ESSENTIAL_IDS) if self.is_first_refresh else len(self.id_list),
                )

            raise UpdateFailed(
                f"Data update timeout after {timeout:.1f} seconds - heat pump may be unreachable"
            ) from None

    async def _async_update_data_internal(self) -> dict[str, Any]:
        """Internal method for data update with retry logic."""
        try:
            # Start the client session if not already started
            await self.client.start()

            # Use JSON API
            return await self._update_data_json()

        except SVKAuthenticationError as err:
            # Provide helpful error message for authentication issues
            error_msg = str(err)
            if "does not support Digest authentication" in error_msg:
                _LOGGER.error(
                    "Device at %s returned unexpected auth scheme (not Digest)",
                    self.client.host,
                )
                _LOGGER.error(
                    "Please check if your device supports Digest authentication"
                )
                raise UpdateFailed(
                    "Unexpected auth scheme from device. Please check if your device supports Digest authentication."
                ) from err
            elif "Invalid username or password" in error_msg:
                _LOGGER.error("Digest authentication failed with SVK Heatpump: %s", err)
                _LOGGER.error(
                    "Please check your username and password in the integration configuration"
                )
                raise UpdateFailed(
                    "Invalid username or password. Please check your credentials."
                ) from err
            elif "stale" in error_msg.lower():
                _LOGGER.warning(
                    "Digest authentication nonce was stale, this should be handled automatically: %s",
                    err,
                )
                # Stale nonce should be handled automatically by the client, but if it persists, we need to re-auth
                raise UpdateFailed(
                    "Authentication nonce expired. Please try reconfiguring the integration."
                ) from err
            else:
                _LOGGER.error("Authentication failed with SVK Heatpump: %s", err)
                _LOGGER.error(
                    "Please check your username and password in the integration configuration"
                )
                raise UpdateFailed(
                    f"Authentication failed: {err}. Please check your credentials."
                ) from err
        except SVKConnectionError as err:
            raise UpdateFailed(f"Error communicating with SVK Heatpump: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _update_data_json(self) -> dict[str, Any]:
        """Update data using JSON API."""
        try:
            # Clear previous parsing errors and warnings
            self.parsing_errors = []
            self.parsing_warnings = []

            # Use progressive loading for first refresh
            if self.is_first_refresh:
                # For first refresh, request all IDs but with a smaller subset to ensure success
                # This ensures all entities are available from the start
                ids_to_request = self.id_list
                _LOGGER.info(
                    "Starting first JSON data update with %d IDs (30 second timeout)",
                    len(ids_to_request),
                )
                _LOGGER.debug(
                    "Requesting all IDs on first refresh: %s", ids_to_request[:20]
                )  # Log first 20 IDs
            else:
                ids_to_request = self.id_list
                _LOGGER.info(
                    "Starting JSON data update with %d IDs (30 second timeout)",
                    len(ids_to_request),
                )
                _LOGGER.debug(
                    "Requesting IDs: %s", ids_to_request[:20]
                )  # Log first 20 IDs

                # Add after line 271:
                _LOGGER.info("REQUESTED IDs: %s", ids_to_request[:20])  # First 20 IDs

                # DEBUG: Check if problematic entities are in the request list
                problem_entities = [
                    380,
                    384,
                ]  # IDs for hotwater_hotwater_source and hotwater_hotwater_neutralzone
                for problem_id in problem_entities:
                    if problem_id in ids_to_request:
                        _LOGGER.info(
                            "DEBUG: Problem entity ID %s is included in request list",
                            problem_id,
                        )
                    else:
                        _LOGGER.warning(
                            "DEBUG: Problem entity ID %s is NOT in request list - this explains unavailability!",
                            problem_id,
                        )

            # Read entities based on whether this is first refresh or not
            _LOGGER.debug(
                "About to call client.read_values - this is a potential blocking point"
            )
            _LOGGER.info(
                "DIAGNOSTIC: Attempting to read %d IDs from heat pump at %s",
                len(ids_to_request),
                self.client.host if hasattr(self.client, "host") else "unknown",
            )
            json_data = await self.client.read_values(ids_to_request)
            _LOGGER.debug(
                "Returned from client.read_values - got %d items",
                len(json_data) if json_data else 0,
            )
            _LOGGER.info(
                "DIAGNOSTIC: Read values returned %s",
                "SUCCESS" if json_data else "FAILURE",
            )

            # Add after line 284:
            _LOGGER.info(
                "RECEIVED IDs: %s", [item.get("id") for item in json_data[:20]]
            )

            # DEBUG: Check if problematic entities are in the response
            problem_entities = [
                380,
                384,
            ]  # IDs for hotwater_hotwater_source and hotwater_hotwater_neutralzone
            received_ids = [item.get("id") for item in json_data]
            for problem_id in problem_entities:
                if str(problem_id) in received_ids:
                    _LOGGER.info(
                        "DEBUG: Problem entity ID %s is present in JSON response",
                        problem_id,
                    )
                else:
                    _LOGGER.warning(
                        "DEBUG: Problem entity ID %s is MISSING from JSON response - this explains unavailability!",
                        problem_id,
                    )

            _LOGGER.info(
                "Received raw JSON data with %d items",
                len(json_data) if json_data else 0,
            )
            _LOGGER.debug(
                "Raw JSON data sample: %s",
                json_data[:5] if json_data and len(json_data) > 0 else "None",
            )

            if not json_data:
                _LOGGER.error(
                    "CRITICAL: No data received from JSON API - this indicates a communication or authentication failure"
                )
                _LOGGER.error("This is likely the root cause of entities not updating")
                # Instead of returning empty data, raise UpdateFailed to trigger proper error handling
                raise UpdateFailed(
                    "No data received from JSON API - check authentication and network connectivity"
                )

            # Store raw JSON data for diagnostics (redact only credentials)
            self.last_raw_json = json_data
            self.last_json_timestamp = datetime.now(timezone.utc)

            # Parse the array of items using the new parse_items function
            try:
                _LOGGER.info(
                    "DATA PIPELINE: Starting JSON parsing with %d items", len(json_data)
                )
                _LOGGER.debug(
                    "DATA PIPELINE: Raw JSON data structure: %s",
                    [
                        {
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "value": item.get("value"),
                        }
                        for item in json_data[:5]
                    ],
                )  # Log first 5 items for debugging
                parsed_items = parse_items(json_data)
                _LOGGER.info(
                    "DATA PIPELINE: Successfully parsed %d items from JSON response",
                    len(parsed_items),
                )
            except Exception as err:
                self.parsing_errors.append(f"JSON parsing failed: {err}")
                _LOGGER.error(
                    "DATA PIPELINE: JSON parsing failed with %d items: %s",
                    len(json_data),
                    err,
                )
                _LOGGER.error(
                    "DATA PIPELINE: This is likely the root cause of entities not having values"
                )
                _LOGGER.error(
                    "DATA PIPELINE: Raising UpdateFailed to trigger proper retry mechanisms"
                )
                _LOGGER.error(
                    "DATA PIPELINE: Raw data sample for debugging: %s",
                    json_data[:3] if json_data else "None",
                )
                # Raise UpdateFailed instead of returning minimal data to ensure proper error reporting
                # This prevents entities from being created without valid values
                raise UpdateFailed(f"JSON parsing failed: {err}") from err

            if not parsed_items:
                self.parsing_errors.append(
                    "No valid items could be parsed from JSON response"
                )
                _LOGGER.error(
                    "CRITICAL: No valid items could be parsed from JSON response. Raw data: %s",
                    json_data[:10] if json_data else "None",
                )
                _LOGGER.error(
                    "This indicates either a JSON parsing failure or unexpected data format from the heat pump"
                )
                # Raise UpdateFailed instead of returning empty data to ensure proper error reporting
                raise UpdateFailed(
                    "No valid items could be parsed from JSON response - check heat pump compatibility"
                )

            # Map parsed items to entity data
            data = {}
            ids_fetched = []

            unknown_ids = []
            sentinel_temps = []
            clamped_percentages = []
            parsing_failures = []

            _LOGGER.info(
                "DATA PIPELINE: Processing %d parsed items for entity mapping",
                len(parsed_items),
            )

            for entity_id, (name, value) in parsed_items.items():
                ids_fetched.append(entity_id)

                # Handle string IDs from JSON parsing by converting to integers for consistent lookup
                # This fixes the issue where HeatPump.RunTime with ID "301" shows as unknown
                lookup_id = entity_id
                if isinstance(entity_id, str):
                    try:
                        lookup_id = int(entity_id)
                        _LOGGER.debug(
                            "DATA PIPELINE: Converted string ID %s to integer %s for lookup",
                            entity_id,
                            lookup_id,
                        )
                    except (ValueError, TypeError) as err:
                        _LOGGER.warning(
                            "DATA PIPELINE: Failed to convert string ID %s to integer: %s",
                            entity_id,
                            err,
                        )
                        unknown_ids.append(
                            {"id": entity_id, "name": name, "value": value}
                        )
                        continue

                # Skip unknown IDs
                if lookup_id not in self.id_to_entity_map:
                    unknown_ids.append({"id": entity_id, "name": name, "value": value})
                    _LOGGER.debug(
                        "DATA PIPELINE: Unknown entity ID %s with name %s and value %s",
                        entity_id,
                        name,
                        value,
                    )
                    continue

                # Use the integer ID for entity info lookup
                entity_info = self.id_to_entity_map[lookup_id]

                entity_key = entity_info["key"]
                _LOGGER.debug(
                    "DATA PIPELINE: Processing entity ID %s -> %s = %s",
                    entity_id,
                    entity_key,
                    value,
                )

                # Handle different data types
                if value is None:
                    # Log null values for debugging
                    _LOGGER.warning(
                        "DATA PIPELINE: Entity %s (ID: %s) has None value - will be unavailable",
                        entity_key,
                        entity_id,
                    )
                    parsing_failures.append(
                        {
                            "entity": entity_key,
                            "id": entity_id,
                            "reason": "None value",
                            "name": name,
                        }
                    )
                    # Skip null values but keep last-good value if available
                    if entity_key in self.last_good_values:
                        data[entity_key] = self.last_good_values[entity_key]
                        _LOGGER.debug(
                            "DATA PIPELINE: Using last-good value for entity %s: %s",
                            entity_key,
                            self.last_good_values[entity_key],
                        )
                    continue

                # Apply temperature sentinel rule
                if entity_info.get("device_class") == "temperature":
                    if isinstance(value, int | float) and value <= -80.0:
                        sentinel_temps.append(
                            {"entity": entity_key, "id": entity_id, "value": value}
                        )
                        _LOGGER.warning(
                            "DATA PIPELINE: Entity %s (ID: %s): Temperature %s°C ≤ -80.0°C, marking unavailable",
                            entity_key,
                            entity_id,
                            value,
                        )
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
                    sanitized_value = self._sanitize_value(
                        entity_key, value, entity_info
                    )

                    # Track percentage clamping
                    if entity_info.get("unit") == "%" and isinstance(
                        value, int | float
                    ):
                        if isinstance(
                            sanitized_value, int | float
                        ) and sanitized_value != float(value):
                            clamped_percentages.append(
                                {
                                    "entity": entity_key,
                                    "id": entity_id,
                                    "original": value,
                                    "clamped": sanitized_value,
                                }
                            )

                    data[entity_key] = sanitized_value

                # Store last-good value
                if data[entity_key] is not None:
                    self.last_good_values[entity_key] = data[entity_key]

            # Add metadata
            data["last_update"] = datetime.now(timezone.utc)
            data["ids_fetched"] = ids_fetched

            # Store parsing statistics for diagnostics
            successful_entities = len(
                [
                    k
                    for k, v in data.items()
                    if v is not None
                    and not k.startswith("last_")
                    and not k.startswith("ids_")
                    and not k.startswith("parsing_")
                ]
            )
            data["parsing_stats"] = {
                "total_ids_requested": len(ids_to_request),
                "total_ids_received": (
                    len(json_data) if isinstance(json_data, list) else 0
                ),
                "total_ids_fetched": len(ids_fetched),
                "unknown_ids_count": len(unknown_ids),
                "sentinel_temps_count": len(sentinel_temps),
                "clamped_percentages_count": len(clamped_percentages),
                "parsing_failures_count": len(parsing_failures),
                "successful_parses": successful_entities,
                "enabled_entities_count": len(
                    [
                        eid
                        for eid in self.id_to_entity_map
                        if self.is_entity_enabled(eid)
                    ]
                ),
                "disabled_entities_count": len(
                    [
                        eid
                        for eid in self.id_to_entity_map
                        if not self.is_entity_enabled(eid)
                    ]
                ),
                "is_first_refresh": self.is_first_refresh,
                "availability_percentage": round(
                    (
                        (successful_entities / len(self.id_to_entity_map) * 100)
                        if len(self.id_to_entity_map) > 0
                        else 0
                    ),
                    1,
                ),
            }

            # Store detailed parsing information for diagnostics
            data["parsing_details"] = {
                "unknown_ids": unknown_ids,
                "sentinel_temps": sentinel_temps,
                "clamped_percentages": clamped_percentages,
                "parsing_failures": parsing_failures,
            }

            # Log comprehensive parsing summary
            _LOGGER.info(
                "DATA PIPELINE: Parsing summary - %d/%d entities available (%.1f%%)",
                successful_entities,
                len(self.id_to_entity_map),
                data["parsing_stats"]["availability_percentage"],
            )
            _LOGGER.info(
                "DATA PIPELINE: Issues found - %d unknown IDs, %d sentinel temps, %d parsing failures",
                len(unknown_ids),
                len(sentinel_temps),
                len(parsing_failures),
            )

            # Enhanced error detection for parsing failures with graceful degradation
            total_enabled_entities = len(
                [eid for eid in self.id_to_entity_map if self.is_entity_enabled(eid)]
            )

            # Always use strict parsing with 50% failure threshold
            critical_failure_threshold = 0.5  # 50% for strict mode
            mode_description = "strict"

            _LOGGER.info(
                "PARSING MODE: %s parsing enabled (threshold: %.1f%%)",
                mode_description,
                critical_failure_threshold * 100,
            )

            if total_enabled_entities > 0:
                success_rate = successful_entities / total_enabled_entities

                # Always log parsing statistics for diagnostics
                _LOGGER.info(
                    "PARSING STATISTICS: %d/%d entities successfully parsed (%.1f%% success rate)",
                    successful_entities,
                    total_enabled_entities,
                    success_rate * 100,
                )

                if success_rate < critical_failure_threshold:
                    # Strict parsing - raise UpdateFailed on critical failures
                    self.parsing_errors.append(
                        f"Critical parsing failure: Only {successful_entities}/{total_enabled_entities} ({success_rate:.1%}) entities parsed successfully"
                    )
                    _LOGGER.error(
                        "CRITICAL: Parsing failure detected - only %d/%d (%.1f%%) enabled entities parsed successfully",
                        successful_entities,
                        total_enabled_entities,
                        success_rate * 100,
                    )
                    _LOGGER.error(
                        "This indicates a serious parsing issue that should trigger retry mechanisms"
                    )
                    _LOGGER.error(
                        "Common causes: incompatible heat pump model, API changes, or network corruption"
                    )
                    # Raise UpdateFailed to trigger proper retry mechanisms instead of returning partial data
                    raise UpdateFailed(
                        f"Critical parsing failure: Only {successful_entities}/{total_enabled_entities} ({success_rate:.1%}) entities parsed successfully - check heat pump compatibility"
                    )
                else:
                    # Success - log info and continue
                    _LOGGER.info(
                        "PARSING SUCCESS: %d/%d entities successfully parsed (%.1f%% success rate) - above threshold of %.1f%%",
                        successful_entities,
                        total_enabled_entities,
                        success_rate * 100,
                        critical_failure_threshold * 100,
                    )

            # Check if we have any valid entity data (excluding metadata)
            valid_entity_data = {
                k: v
                for k, v in data.items()
                if not k.startswith("last_")
                and not k.startswith("ids_")
                and not k.startswith("parsing_")
                and v is not None
            }

            if not valid_entity_data:
                self.parsing_errors.append(
                    "No valid entity data could be parsed from JSON response"
                )
                _LOGGER.error(
                    "CRITICAL: No valid entity data could be parsed from JSON response"
                )
                _LOGGER.error(
                    "This will cause entities to be unavailable until valid data is received"
                )
                _LOGGER.error(
                    "Parsing details: %d unknown IDs, %d sentinel temps, %d parsing failures",
                    len(unknown_ids),
                    len(sentinel_temps),
                    len(parsing_failures),
                )
                # Raise UpdateFailed instead of returning minimal data to ensure proper error reporting
                # This prevents entities from being created without valid values
                raise UpdateFailed(
                    "No valid entity data could be parsed from JSON response - check heat pump compatibility and network connectivity"
                )

            _LOGGER.info("Successfully parsed %d entities from JSON data", len(data))
            _LOGGER.debug(
                "Parsed entities: %s", list(data.keys())[:20]
            )  # Log first 20 entity keys
            return data

        except Exception as err:
            _LOGGER.error("JSON API update failed: %s", err)
            _LOGGER.error(
                "Raising UpdateFailed to ensure proper error reporting instead of returning empty data"
            )
            _LOGGER.error(
                "This error will trigger Home Assistant's retry mechanism instead of masking the failure"
            )

            # Enhanced error logging for debugging
            if hasattr(err, "__traceback__"):
                import traceback

                _LOGGER.error(
                    "Full traceback for debugging: %s", traceback.format_exc()
                )

            # Store detailed error information for diagnostics
            error_details = {
                "error_type": type(err).__name__,
                "error_message": str(err),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": "JSON API data update",
            }

            self.parsing_errors.append(f"JSON API update failed: {err}")
            self.parsing_errors.append(f"Error details: {error_details}")

            # Raise UpdateFailed instead of returning empty data to ensure proper error reporting
            # This ensures Home Assistant's retry mechanisms are triggered
            raise UpdateFailed(f"JSON API update failed: {err}") from err

    def _map_heatpump_state(self, value: Any) -> str:
        """Map heatpump state enum value."""
        # Handle numeric enum values
        if isinstance(value, int | float):
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
                11: "manual",
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

    def _map_season_mode(self, value: Any) -> str:
        """Map season mode enum value."""
        # Handle numeric enum values
        if isinstance(value, int | float):
            # Map numeric values to modes
            mode_mapping = {0: "winter", 1: "summer", 2: "auto"}
            return mode_mapping.get(int(value), "unknown")

        # Handle string enum values
        if isinstance(value, str):
            # Try to map using existing SEASON_MODES
            for mode_text, mode_value in SEASON_MODES.items():
                if mode_text.lower() in value.lower():
                    return mode_value
            return value.lower()

        return "unknown"

    async def async_set_parameter(self, parameter: str, value: Any) -> bool:
        """Set a parameter value."""
        try:
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

        except Exception as err:
            _LOGGER.error("Failed to set %s to %s: %s", parameter, value, err)
            return False

    def get_enabled_entities(self, config_entry) -> list[str]:
        """Get list of enabled entities based on configuration."""
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

    def get_entity_value(self, entity_key: str) -> Any:
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
        """Check if an entity is available with valid, current data.

        This method now performs comprehensive validation to ensure entities are only
        marked as available when they have valid, recent data from the heat pump.

        Args:
            entity_key: The entity key to check availability for

        Returns:
            True if the entity has valid, current data, False otherwise
        """
        # Find the entity ID for this entity key
        entity_id = None
        for eid, info in self.id_to_entity_map.items():
            if info["key"] == entity_key:
                entity_id = eid
                break

        if entity_id is None:
            _LOGGER.debug(
                "AVAILABILITY: Entity %s not available - not found in ID mapping",
                entity_key,
            )
            return False

        _LOGGER.debug(
            "AVAILABILITY: Checking availability for %s (ID: %s)",
            entity_key,
            entity_id,
        )

        # Check if we have any data at all
        if not self.data:
            _LOGGER.debug(
                "AVAILABILITY: Entity %s (ID: %s) not available - no data loaded yet",
                entity_key,
                entity_id,
            )
            return False

        # Check data freshness - ensure data was updated recently
        last_update = self.data.get("last_update")
        if last_update is None:
            _LOGGER.warning(
                "AVAILABILITY: Entity %s (ID: %s) not available - no timestamp in data",
                entity_key,
                entity_id,
            )
            return False

        # Calculate data age
        now = datetime.now(timezone.utc)
        data_age = (now - last_update).total_seconds()
        max_data_age = 120  # Consider data stale after 2 minutes

        if data_age > max_data_age:
            _LOGGER.warning(
                "AVAILABILITY: Entity %s (ID: %s) not available - data is stale (%.1f seconds old, max: %d)",
                entity_key,
                entity_id,
                data_age,
                max_data_age,
            )
            return False

        # Check if this entity was included in the last successful fetch
        # FIX: Handle both string and integer IDs in ids_fetched list
        ids_fetched = self.data.get("ids_fetched", [])
        entity_in_fetch = False
        
        # Check for both integer and string representations of the entity ID
        if entity_id in ids_fetched:
            entity_in_fetch = True
        elif str(entity_id) in ids_fetched:
            entity_in_fetch = True
        else:
            # Also check if any ID in the list can be converted to int and matches
            for fetched_id in ids_fetched:
                try:
                    if int(fetched_id) == entity_id:
                        entity_in_fetch = True
                        break
                except (ValueError, TypeError):
                    continue
        
        if not entity_in_fetch:
            _LOGGER.warning(
                "AVAILABILITY: Entity %s (ID: %s) not available - not included in last data fetch",
                entity_key,
                entity_id,
            )
            _LOGGER.warning(
                "AVAILABILITY: DEBUG - Entity ID %s (as int: %s, as str: '%s') not found in ids_fetched",
                entity_id,
                entity_id,
                str(entity_id),
            )
            _LOGGER.warning(
                "AVAILABILITY: DEBUG - First 20 IDs fetched: %s",
                ids_fetched[:20],
            )
            _LOGGER.warning(
                "AVAILABILITY: DEBUG - Entity ID types in fetch: %s",
                [type(id).__name__ for id in ids_fetched[:10]],
            )
            return False

        # Check if the entity has a valid, non-None value
        value = self.get_entity_value(entity_key)
        if value is None:
            _LOGGER.warning(
                "AVAILABILITY: Entity %s (ID: %s) not available - value is None - this may indicate a data fetching or parsing issue",
                entity_key,
                entity_id,
            )
            _LOGGER.warning(
                "AVAILABILITY: DEBUG - Entity %s (ID: %s) value=None, data keys: %s",
                entity_key,
                entity_id,
                list(self.data.keys())[:20] if self.data else "No data",
            )
            
            # Additional debug: Check if entity key exists in data with None value
            if entity_key in self.data:
                _LOGGER.warning(
                    "AVAILABILITY: DEBUG - Entity %s exists in data but value is None: %s",
                    entity_key,
                    self.data[entity_key],
                )
            else:
                _LOGGER.warning(
                    "AVAILABILITY: DEBUG - Entity %s does not exist in data at all",
                    entity_key,
                )
            return False

        # Additional check for temperature sentinel values
        entity_info = self.id_to_entity_map.get(entity_id, {})
        if entity_info.get("device_class") == "temperature":
            if isinstance(value, int | float) and value <= -80.0:
                _LOGGER.debug(
                    "AVAILABILITY: Entity %s (ID: %s) not available - temperature sentinel value %s°C",
                    entity_key,
                    entity_id,
                    value,
                )
                return False

        # Check for parsing errors related to this entity
        parsing_details = self.data.get("parsing_details", {})
        parsing_failures = parsing_details.get("parsing_failures", [])
        for failure in parsing_failures:
            # Check both entity_key and entity_id (handling string/int conversion)
            failure_entity = failure.get("entity")
            failure_id = failure.get("id")
            
            if failure_entity == entity_key:
                _LOGGER.warning(
                    "AVAILABILITY: Entity %s (ID: %s) not available - parsing error: %s",
                    entity_key,
                    entity_id,
                    failure.get("reason", "Unknown error"),
                )
                return False
            elif failure_id == entity_id or str(failure_id) == str(entity_id):
                _LOGGER.warning(
                    "AVAILABILITY: Entity %s (ID: %s) not available - parsing error (by ID): %s",
                    entity_key,
                    entity_id,
                    failure.get("reason", "Unknown error"),
                )
                return False

        # Check for sentinel temperature values
        sentinel_temps = parsing_details.get("sentinel_temps", [])
        for sentinel in sentinel_temps:
            # Check both entity_key and entity_id (handling string/int conversion)
            sentinel_entity = sentinel.get("entity")
            sentinel_id = sentinel.get("id")
            
            if sentinel_entity == entity_key:
                _LOGGER.warning(
                    "AVAILABILITY: Entity %s (ID: %s) not available - sentinel temperature detected",
                    entity_key,
                    entity_id,
                )
                return False
            elif sentinel_id == entity_id or str(sentinel_id) == str(entity_id):
                _LOGGER.warning(
                    "AVAILABILITY: Entity %s (ID: %s) not available - sentinel temperature detected (by ID)",
                    entity_key,
                    entity_id,
                )
                return False

        # If we reach here, the entity has valid, current data
        _LOGGER.debug(
            "AVAILABILITY: Entity %s (ID: %s) is available - has valid value: %s (data age: %.1fs)",
            entity_key,
            entity_id,
            value,
            data_age,
        )
        return True

    def get_all_entities_data(self) -> dict[str, dict[str, Any]]:
        """Get data for all available entities, including disabled ones.

        Returns:
            Dictionary with all entity data, including enabled/disabled status
        """
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
                "value": (
                    self.get_entity_value(entity_key)
                    if self.is_entity_available(entity_key)
                    else None
                ),
            }
            all_entities[entity_key] = entity_data

        return all_entities

    def get_entity_info(self, entity_key: str) -> dict[str, Any] | None:
        """Get entity information (unit, device_class, state_class, original_name) for JSON API."""
        # Find the entity info for this entity key
        for entity_id, info in self.id_to_entity_map.items():
            if info["key"] == entity_key:
                return {
                    "entity_id": entity_id,
                    "unit": info["unit"],
                    "device_class": info["device_class"],
                    "state_class": info["state_class"],
                    "original_name": info["original_name"],
                }

        return None

    def get_alarm_summary(self) -> dict[str, Any]:
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

    def get_system_status(self) -> dict[str, Any]:
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

    def _sanitize_value(self, entity_key: str, value: Any, entity_info: dict[str, Any]) -> Any:
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
                if isinstance(value, int | float):
                    return max(0, min(100, float(value)))
            except (ValueError, TypeError):
                pass

        # Runtime values - keep as numeric
        if (
            entity_info.get("entity_category") == "diagnostic"
            and "runtime" in entity_key
        ):
            try:
                return float(value)
            except (ValueError, TypeError):
                pass

        # Default: return value as-is
        return value

    def get_json_diagnostics(self) -> dict[str, Any]:
        """Get comprehensive JSON diagnostics data."""
        if not self.is_json_client:
            return {"error": "Not using JSON API"}

        diagnostics = {
            "json_api_enabled": True,
            "last_json_timestamp": self.last_json_timestamp,
            "id_list_configured": self.id_list,
            "id_list_count": len(self.id_list),
            "user_configured_ids": self.user_configured_ids,
            "user_configured_ids_count": (
                len(self.user_configured_ids) if self.user_configured_ids else 0
            ),
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

    def _get_entity_availability_summary(self) -> dict[str, Any]:
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
            "other": 0,
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
            "availability_percentage": round(
                (
                    (available_entities / total_entities * 100)
                    if total_entities > 0
                    else 0
                ),
                1,
            ),
            "entity_types": entity_types,
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

    def get_unavailable_entities(self) -> list[dict[str, Any]]:
        """Get list of unavailable entities with reasons."""
        if not self.data:
            return []

        unavailable = []

        for entity_id, entity_info in self.id_to_entity_map.items():
            entity_key = entity_info["key"]

            if not self.is_entity_available(entity_key):
                unavailable.append(
                    {
                        "entity_key": entity_key,
                        "entity_id": entity_id,
                        "name": entity_info["original_name"],
                        "unit": entity_info["unit"],
                        "device_class": entity_info["device_class"],
                        "enabled": self.is_entity_enabled(entity_id),
                    }
                )

        return unavailable

    def get_disabled_entities(self) -> list[dict[str, Any]]:
        """Get list of disabled entities that are available but not enabled."""
        if not self.data:
            return []

        disabled = []

        for entity_id, entity_info in self.id_to_entity_map.items():
            entity_key = entity_info["key"]

            # Entity is disabled but available (we have data for it)
            if not self.is_entity_enabled(entity_id) and self.is_entity_available(
                entity_key
            ):
                disabled.append(
                    {
                        "entity_key": entity_key,
                        "entity_id": entity_id,
                        "name": entity_info["original_name"],
                        "unit": entity_info["unit"],
                        "device_class": entity_info["device_class"],
                        "value": self.get_entity_value(entity_key),
                    }
                )

        return disabled

    @property
    def device_info(self) -> DeviceInfo:
        """Return centralized device information."""
        return self._device_info
