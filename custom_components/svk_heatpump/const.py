"""Constants for SVK Heatpump integration."""

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

DOMAIN = "svk_heatpump"
DEFAULT_TIMEOUT = 10
DEFAULT_SCAN_INTERVAL = 30

# Device information
MANUFACTURER = "SVK"
MODEL = "Heatpump"
SW_VERSION = "0.0.1"

# Home Assistant platforms to load
PLATFORMS = ["sensor", "number", "select", "switch"]

# Device groups for entity organization
DEVICE_GROUPS = {
    "display": {"name": "Display"},
    "extended_display": {"name": "Extended Display", "via": "display"},
    "heating": {"name": "Heating"},
    "heatpump": {"name": "Heatpump"},
    "hotwater": {"name": "Hot Water"},
    "service": {"name": "Service"},
    "solar_panel": {"name": "Solar Panel"},
    "user": {"name": "User"},
    "firmwareupgrade": {"name": "Firmwareupgrade"},
    "groups": {"name": "Groups"},
    "systemview": {"name": "Systemview"},
    "defrost": {"name": "Defrost"},
}

# Configuration keys
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLE_WRITES = "enable_writes"
CONF_ID_LIST = "id_list"

# HTML Interface Grouping Structure
# Based on the HTML interface navigation structure
HTML_GROUPS = {
    "Operation": {
        "Display": {
            "description": "Main operational view entities (temperatures, states)",
            "pages": ["display"],
        },
        "User": {"description": "User-configurable parameters", "pages": ["user"]},
    },
    "Settings": {
        "Heatpump": {
            "description": "Heat pump settings",
            "pages": ["heatpump", "settings_heatpump"],
        },
        "Extended Display": {
            "description": "Extended display settings",
            "pages": ["extended_display"],
        },
        "Heating": {
            "description": "Heating system settings",
            "pages": ["heating", "settings_heating"],
        },
        "Defrost": {"description": "Defrost parameters", "pages": ["settings_defrost"]},
        "Service": {"description": "Service parameters", "pages": ["settings_service"]},
        "Solar panel": {
            "description": "Solar panel settings",
            "pages": ["solar", "settings_solar"],
        },
        "Hot water": {
            "description": "Hot water settings",
            "pages": ["hotwater", "settings_hotwater"],
        },
    },
    "Configuration": {
        "System": {
            "description": "System configuration",
            "pages": [],  # Configuration entities may not have specific pages
        }
    },
}

# Heat pump state mappings
HEATPUMP_STATES = {
    "Off": "off",
    "Ready": "ready",
    "Start up": "start_up",
    "Heating": "heating",
    "Hot water": "hot_water",
    "El heating": "el_heating",
    "Defrost": "defrost",
    "Drip delay": "drip_delay",
    "Total stop": "total_stop",
    "Pump exercise": "pump_exercise",
    "Forced running": "forced_running",
    "Manual": "manual",
}

# Reverse mapping for writes
HEATPUMP_STATES_REVERSE = {v: k for k, v in HEATPUMP_STATES.items()}

# Season mode mappings
SEASON_MODES = {"Summer": "summer", "Winter": "winter", "Auto": "auto"}

# Reverse mapping for writes
SEASON_MODES_REVERSE = {v: k for k, v in SEASON_MODES.items()}

# Solar panel state mappings
SOLAR_STATES = {"Off": "off", "Running": "running", "Forced Stop": "forced_stop"}

# Reverse mapping for writes
SOLAR_STATES_REVERSE = {v: k for k, v in SOLAR_STATES.items()}

# Alarm severity levels
ALARM_SEVERITIES = {"Warning": "warning", "Critical": "critical"}

# Default alarm codes and descriptions
ALARM_CODES = {
    # Sensor faults (100-121)
    "100": "Temperature sensor fault",
    "101": "Temperature sensor fault",
    "102": "Temperature sensor fault",
    "103": "Temperature sensor fault",
    "104": "Temperature sensor fault",
    "105": "Temperature sensor fault",
    "106": "Temperature sensor fault",
    "107": "Temperature sensor fault",
    "108": "Temperature sensor fault",
    "109": "Temperature sensor fault",
    "110": "Temperature sensor fault",
    "111": "Temperature sensor fault",
    "112": "Temperature sensor fault",
    "113": "Temperature sensor fault",
    "114": "Temperature sensor fault",
    "115": "Temperature sensor fault",
    "116": "Temperature sensor fault",
    "117": "Temperature sensor fault",
    "118": "Temperature sensor fault",
    "119": "Temperature sensor fault",
    "120": "Temperature sensor fault",
    "121": "Temperature sensor fault",
    # Pressostat & FC alarms (600-609)
    "600": "Low pressure",
    "601": "Low pressure",
    "602": "High pressure",
    "603": "High pressure",
    "604": "Pressostat fault",
    "605": "Pressostat fault",
    "606": "Flow switch fault",
    "607": "Flow switch fault",
    "608": "FC alarm",
    "609": "FC alarm",
}

# JSON API Constants

# JSON API Helper Functions
def parse_id_list(id_list_str: str) -> list[int]:
    """Parse a semicolon or comma-separated ID list string into a list of integers.

    Args:
        id_list_str (str): Semicolon or comma-separated ID list string

    Returns:
        list[int]: List of integer IDs

    Raises:
        ValueError: If the ID list format is invalid
    """
    if not id_list_str:
        return []

    try:
        # Support both semicolon and comma separators
        separator = ";" if ";" in id_list_str else ","
        return [
            int(id_str.strip())
            for id_str in id_list_str.split(separator)
            if id_str.strip()
        ]
    except (ValueError, AttributeError) as err:
        raise ValueError(f"Invalid ID list format: {id_list_str}") from err


def validate_id_list(id_list_str: str) -> bool:
    """Validate that all IDs in the list are valid integers and exist in ID_MAP.

    Args:
        id_list_str (str): Semicolon-separated ID list string

    Returns:
        bool: True if all IDs are valid, False otherwise
    """
    if not id_list_str:
        return True

    try:
        ids = parse_id_list(id_list_str)
        # Import ID_MAP from catalog to validate
        from .catalog import ID_MAP
        return all(entity_id in ID_MAP for entity_id in ids)
    except ValueError:
        return False


def get_all_groups() -> dict[str, Any]:
    """Get all available categories and groups.

    Returns:
        dict: Dictionary with categories as keys and lists of groups as values
    """
    return HTML_GROUPS


def get_group_description(category: str, group: str) -> str | None:
    """Get the description for a specific group.

    Args:
        category (str): The category
        group (str): The group within the category

    Returns:
        str: The group description, or None if not found
    """
    if category in HTML_GROUPS and group in HTML_GROUPS[category]:
        return HTML_GROUPS[category][group].get("description")
    return None


def parse_items(items_list: list) -> dict[int, tuple[str, Any]]:
    """Parse a list of JSON items with id, name, and value fields.

    Enhanced with per-entity error tracking to identify parsing patterns.

    Args:
        items_list (list): List of dictionaries with 'id', 'name', and 'value' fields

    Returns:
        dict[int]: Dictionary mapping integer IDs to (name, parsed_value) tuples

    Note:
        This function is more resilient to missing fields and will not raise exceptions
        for invalid items. It will log warnings for problematic items but continue processing.
    """
    result: dict[int, tuple[str, Any]] = {}

    # Per-entity error tracking
    parsing_errors = []
    parsing_warnings = []
    successful_parses = []

    if not items_list:
        _LOGGER.debug("Empty items list provided to parse_items")
        return result

    _LOGGER.info(
        "PARSING PIPELINE: Starting to parse %d items from JSON response",
        len(items_list),
    )

    for item in items_list:
        try:
            # Validate item structure
            if not isinstance(item, dict):
                error_detail = {
                    "entity_id": "unknown",
                    "reason": "not_a_dict",
                    "item": str(item)[:100],
                    "raw_data": item,
                }
                parsing_errors.append(error_detail)
                _LOGGER.warning(
                    "PARSING ERROR: Skipping invalid item (not a dict): %s", item
                )
                continue

            # More flexible field validation - allow missing 'name' field
            if "id" not in item or "value" not in item:
                error_detail = {
                    "entity_id": item.get("id", "unknown"),
                    "reason": "missing_required_fields",
                    "missing_fields": [f for f in ["id", "value"] if f not in item],
                    "item": str(item)[:100],
                    "raw_data": item,
                }
                parsing_errors.append(error_detail)
                _LOGGER.warning(
                    "PARSING ERROR: Skipping item missing required fields (id/value): %s",
                    item,
                )
                continue

            # Extract and validate ID
            try:
                entity_id = int(item["id"])
            except (ValueError, TypeError):
                error_detail = {
                    "entity_id": item.get("id", "unknown"),
                    "reason": "invalid_id_format",
                    "raw_id": item.get("id"),
                    "item": str(item)[:100],
                    "raw_data": item,
                }
                parsing_errors.append(error_detail)
                _LOGGER.warning(
                    "PARSING ERROR: Invalid ID '%s' in item: %s", item.get("id"), item
                )
                continue

            # Extract name or create default if missing
            if "name" in item and item["name"]:
                name = str(item["name"])
            else:
                name = f"entity_{entity_id}"
                warning_detail = {
                    "entity_id": entity_id,
                    "reason": "missing_name_field",
                    "generated_name": name,
                    "item": str(item)[:100],
                }
                parsing_warnings.append(warning_detail)
                _LOGGER.debug(
                    "PARSING WARNING: Generated default name '%s' for item ID %s",
                    name,
                    entity_id,
                )

            # Parse value with proper type conversion
            raw_value = item["value"]

            # Parse value with proper error handling - don't fall back to raw values
            # This prevents type mismatches in the data pipeline
            try:
                parsed_value = _parse_value(raw_value)
                if parsed_value is None:
                    error_detail = {
                        "entity_id": entity_id,
                        "name": name,
                        "reason": "value_parsing_returned_null",
                        "raw_value": str(raw_value)[:100],
                        "value_type": type(raw_value).__name__,
                    }
                    parsing_errors.append(error_detail)
                    _LOGGER.warning(
                        "PARSING ERROR: VALUE PARSING RETURNED NULL: id=%s, name=%s, raw_value=%s - entity will be excluded from results",
                        entity_id,
                        name,
                        raw_value,
                    )
                    # Skip adding this entity to results when parsing returns None
                    continue
            except Exception as err:
                error_detail = {
                    "entity_id": entity_id,
                    "name": name,
                    "reason": "value_parsing_failed",
                    "raw_value": str(raw_value)[:100],
                    "value_type": type(raw_value).__name__,
                    "error": str(err),
                }
                parsing_errors.append(error_detail)
                _LOGGER.error(
                    "PARSING ERROR: VALUE PARSING FAILED: id=%s, name=%s, raw_value=%s, error=%s - entity will be excluded from results",
                    entity_id,
                    name,
                    raw_value,
                    err,
                )
                # Skip adding this entity to results when parsing fails
                continue

            # Only add entities with successfully parsed values to results
            result[entity_id] = (name, parsed_value)

            # Track successful parsing
            success_detail = {
                "entity_id": entity_id,
                "name": name,
                "raw_value": str(raw_value)[:100],
                "parsed_value": str(parsed_value)[:100],
                "parsed_type": type(parsed_value).__name__,
            }
            successful_parses.append(success_detail)

            _LOGGER.debug(
                "Successfully parsed item ID %s: %s = %s", entity_id, name, parsed_value
            )

            # Add enhanced logging for debugging parsing successes
            _LOGGER.info(
                "PARSING SUCCESS: ID=%s, Name=%s, RawValue=%s -> ParsedValue=%s (type: %s)",
                entity_id,
                name,
                raw_value,
                parsed_value,
                type(parsed_value).__name__,
            )

        except Exception as err:
            # Catch-all error for unexpected issues
            error_detail = {
                "entity_id": (
                    item.get("id", "unknown") if isinstance(item, dict) else "unknown"
                ),
                "reason": "unexpected_parsing_error",
                "error": str(err),
                "item": str(item)[:100],
            }
            parsing_errors.append(error_detail)
            _LOGGER.warning(
                "PARSING ERROR: Unexpected error parsing item %s: %s", item, err
            )
            # Continue processing other items instead of failing completely
            continue

    # Enhanced summary logging with error patterns
    _LOGGER.info(
        "PARSING SUMMARY: Successfully parsed %d items with valid values out of %d total items",
        len(result),
        len(items_list),
    )

    if parsing_errors:
        _LOGGER.error(
            "PARSING ERRORS SUMMARY: %d parsing errors occurred", len(parsing_errors)
        )
        # Group errors by reason for pattern analysis
        error_reasons: dict[str, int] = {}
        for error in parsing_errors:
            reason = error.get("reason", "unknown")
            error_reasons[reason] = error_reasons.get(reason, 0) + 1
        _LOGGER.error("PARSING ERROR PATTERNS: %s", error_reasons)

        # Log first few errors for debugging
        for i, error in enumerate(parsing_errors[:5]):
            _LOGGER.error(
                "PARSING ERROR #%d: ID=%s, Reason=%s, Details=%s",
                i + 1,
                error.get("entity_id"),
                error.get("reason"),
                error,
            )

    if parsing_warnings:
        _LOGGER.warning(
            "PARSING WARNINGS SUMMARY: %d parsing warnings occurred",
            len(parsing_warnings),
        )
        # Group warnings by reason for pattern analysis
        warning_reasons: dict[str, int] = {}
        for warning in parsing_warnings:
            reason = warning.get("reason", "unknown")
            warning_reasons[reason] = warning_reasons.get(reason, 0) + 1
        _LOGGER.warning("PARSING WARNING PATTERNS: %s", warning_reasons)

    _LOGGER.debug("Final parsed entities: %s", list(result.keys()))

    # Add parsing statistics to the result for diagnostics
    parsing_stats = {
        "total_items": len(items_list),
        "successful_parses": len(successful_parses),
        "parsing_errors": len(parsing_errors),
        "parsing_warnings": len(parsing_warnings),
        "success_rate": (
            round(len(result) / len(items_list) * 100, 1) if items_list else 0
        ),
        "error_patterns": {
            error.get("reason"): error.get("error") for error in parsing_errors[:10]
        },
        "warning_patterns": {
            warning.get("reason"): warning.get("generated_name")
            for warning in parsing_warnings[:10]
        },
    }

    # Store detailed parsing information for diagnostics
    # We'll attach this to the result in a way that doesn't break existing code
    if hasattr(parse_items, "_last_parsing_stats"):
        parse_items._last_parsing_stats = parsing_stats
    else:
        parse_items._last_parsing_stats = parsing_stats

    if hasattr(parse_items, "_last_parsing_errors"):
        parse_items._last_parsing_errors = parsing_errors
    else:
        parse_items._last_parsing_errors = parsing_errors

    if hasattr(parse_items, "_last_parsing_warnings"):
        parse_items._last_parsing_warnings = parsing_warnings
    else:
        parse_items._last_parsing_warnings = parsing_warnings

    _LOGGER.info("PARSING STATISTICS: %s", parsing_stats)

    return result


def _parse_value(value):
    """Parse a value string to the appropriate type.

    Args:
        value: The value to parse (typically a string)

    Returns:
        The parsed value (float, int, or string, or None for empty values)
    """
    if value is None or value == "":
        return None

    # Handle boolean values directly
    if isinstance(value, bool):
        return value

    # Convert to string for processing
    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    if not value:
        return None

    # Check if it's a float (contains decimal point)
    if "." in value:
        try:
            return float(value)
        except ValueError:
            pass

    # Check if it's a boolean-like value (0/1)
    if value == "0":
        return False
    elif value == "1":
        return True

    # Check if it's an integer (all digits, possibly with sign)
    if value.lstrip("-+").isdigit():
        try:
            return int(value)
        except ValueError:
            pass

    # Return as string if no conversion worked
    return value

# Import entity-related functions from catalog.py to maintain compatibility
# These imports allow existing code that imports from const.py to continue working
try:
    from .catalog import (
        # Entity definitions
        ENTITIES,
        TEMP_SENSORS,
        SETPOINT_SENSORS,
        PERFORMANCE_SENSORS,
        COUNTER_SENSORS,
        SYSTEM_SENSORS,
        SYSTEM_COUNTER_SENSORS,
        BINARY_SENSORS,
        SELECT_ENTITIES_LEGACY,
        NUMBER_ENTITIES_LEGACY,
        
        # Entity mappings and lists
        ID_MAP,
        BINARY_OUTPUT_IDS,
        DEFAULT_IDS,
        DEFAULT_ENABLED_ENTITIES,
        
        # Entity helper functions
        get_entity_info,
        is_binary_output,
        get_original_name,
        get_binary_output_name,
        get_entity_group_info,
        get_entity_ids_by_group,
        get_entity_by_id,
        
        # Platform-specific entity lists
        SENSOR_ENTITIES,
        BINARY_SENSOR_ENTITIES,
        NUMBER_ENTITIES,
        SELECT_ENTITIES,
        SWITCH_ENTITIES,
        
        # Additional catalog functions
        get_all_entities,
        get_entities_by_platform,
        get_entities_by_category,
        get_entities_by_group,
    )
except ImportError:
    # If catalog.py is not available, define placeholders to prevent errors
    _LOGGER.warning("Could not import entity definitions from catalog.py")
    ENTITIES = {}
    TEMP_SENSORS = {}
    SETPOINT_SENSORS = {}
    PERFORMANCE_SENSORS = {}
    COUNTER_SENSORS = {}
    SYSTEM_SENSORS = {}
    SYSTEM_COUNTER_SENSORS = {}
    BINARY_SENSORS = {}
    SELECT_ENTITIES_LEGACY = {}
    NUMBER_ENTITIES_LEGACY = {}
    ID_MAP = {}
    BINARY_OUTPUT_IDS = {}
    DEFAULT_IDS = ""
    DEFAULT_ENABLED_ENTITIES = []
    SENSOR_ENTITIES = []
    BINARY_SENSOR_ENTITIES = []
    NUMBER_ENTITIES = []
    SELECT_ENTITIES = []
    SWITCH_ENTITIES = []
    
    def get_entity_info(entity_id: int):
        return None
    
    def is_binary_output(entity_id) -> bool:
        return False
    
    def get_original_name(entity_id: int) -> str | None:
        return None
    
    def get_binary_output_name(entity_id: int) -> str | None:
        return None
    
    def get_entity_group_info(entity_id: int) -> dict[str, Any] | None:
        return None
    
    def get_entity_ids_by_group(category, group):
        return []
    
    def get_entity_by_id(entity_id: int):
        return None
    
    def get_all_entities():
        return {}
    
    def get_entities_by_platform(platform: str):
        return []
    
    def get_entities_by_category(category: str):
        return []
    
    def get_entities_by_group(category: str, group: str):
        return []
