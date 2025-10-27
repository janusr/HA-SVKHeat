"""Diagnostics support for SVK Heatpump integration."""

from typing import Any

import aiohttp
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from . import const

TO_REDACT = {
    "password",
    "username",
    "token",
    "key",
    "secret",
    "auth",
    "login",
    "_auth",
    "_username",
    "_password",
}
# Note: We don't redact "host" anymore as it's needed for debugging JSON API connectivity
# Note: We keep auth_scheme, last_status_code, and digest_auth_info for troubleshooting


def _redact_auth_data(data: Any) -> Any:
    """Redact authentication data including aiohttp.BasicAuth objects."""
    if isinstance(data, aiohttp.BasicAuth):
        return "**REDACTED**"

    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            # Redact auth-related keys
            if key.lower() in {
                "password",
                "username",
                "auth",
                "login",
                "_auth",
                "_username",
                "_password",
            }:
                redacted[key] = "**REDACTED**"
            # Recursively process nested dictionaries
            elif isinstance(value, dict):
                redacted[key] = _redact_auth_data(value)
            # Check for BasicAuth objects in values
            elif isinstance(value, aiohttp.BasicAuth):
                redacted[key] = "**REDACTED**"
            else:
                redacted[key] = value
        return redacted

    return data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]

    diagnostics_data = {
        "config_entry_data": _redact_auth_data(
            async_redact_data(config_entry.data, TO_REDACT)
        ),
        "config_entry_options": config_entry.options,
        "coordinator_data": {
            "last_update_success": coordinator.last_update_success,
            "last_update": coordinator.last_update_success,
            "update_interval": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
        },
    }

    # Add JSON API diagnostics
    json_diagnostics = coordinator.get_json_diagnostics()
    diagnostics_data["json_api_diagnostics"] = json_diagnostics

    # Add formatted table of raw JSON data
    if coordinator.last_raw_json:
        diagnostics_data["raw_json_table"] = coordinator.format_json_as_table()

    # Add entity availability summary
    if coordinator.data:
        diagnostics_data["entity_availability"] = json_diagnostics.get(
            "entity_availability", {}
        )

    # Add parsing statistics and errors
    if coordinator.data and "parsing_stats" in coordinator.data:
        diagnostics_data["parsing_statistics"] = coordinator.data["parsing_stats"]
        diagnostics_data["parsing_details"] = coordinator.data.get(
            "parsing_details", {}
        )

        # Enhanced parsing diagnostics from const.py parse_items function

        if hasattr(const.parse_items, "_last_parsing_stats"):
            diagnostics_data["enhanced_parsing_statistics"] = (
                const.parse_items._last_parsing_stats
            )
        if hasattr(const.parse_items, "_last_parsing_errors"):
            diagnostics_data["parsing_errors"] = const.parse_items._last_parsing_errors
        if hasattr(const.parse_items, "_last_parsing_warnings"):
            diagnostics_data["parsing_warnings"] = (
                const.parse_items._last_parsing_warnings
            )

    # Add unavailable entities list
    unavailable_entities = coordinator.get_unavailable_entities()
    if unavailable_entities:
        diagnostics_data["unavailable_entities"] = unavailable_entities

    # Add entity type counting
    entity_type_counts = count_entities_by_type(coordinator)
    diagnostics_data["entity_type_counts"] = entity_type_counts

    # Add detailed unavailable entity analysis
    unavailable_analysis = identify_unavailable_entities(coordinator)
    diagnostics_data["unavailable_entity_analysis"] = unavailable_analysis

    # Add current data if available
    if coordinator.data:
        # Create a copy of data and redact sensitive information
        data_copy = dict(coordinator.data)

        # Redact any HTML content that might contain sensitive info
        if "raw_html" in data_copy:
            data_copy["raw_html"] = "[REDACTED]"

        # Add parsed data (already cleaned by parser)
        diagnostics_data["parsed_data"] = _redact_auth_data(
            async_redact_data(data_copy, TO_REDACT)
        )

        # Add alarm summary
        alarm_summary = coordinator.get_alarm_summary()
        diagnostics_data["alarm_summary"] = alarm_summary

        # Add system status
        system_status = coordinator.get_system_status()
        diagnostics_data["system_status"] = system_status

    # Add client information
    client_info = {
        "host": client.host,
        "timeout": client._timeout.total if client._timeout else None,
        "session_closed": client._session.closed if client._session else None,
    }

    # Add base_url for LOMJsonClient
    if hasattr(client, "_base"):
        client_info["base_url"] = str(client._base)

    # Add authentication status for LOMJsonClient
    if hasattr(client, "_username") and hasattr(client, "_password"):
        client_info["auth_configured"] = bool(client._username and client._password)
        client_info["auth_type"] = "digest"
    else:
        client_info["auth_configured"] = False

    # Add auth scheme detection for LOMJsonClient
    if hasattr(client, "_username") and hasattr(client, "_password"):
        # This is LOMJsonClient with Digest auth
        client_info["auth_scheme"] = "digest"
        client_info["auth_configured"] = bool(client._username and client._password)

        # Add last status code if available
        if hasattr(client, "_last_status_code"):
            client_info["last_status_code"] = client._last_status_code

        # Add digest auth parameters (without credentials)
        if hasattr(client, "_digest_realm") and client._digest_realm:
            digest_info = {
                "realm": client._digest_realm,
                "qop": getattr(client, "_digest_qop", None),
                "algorithm": getattr(client, "_digest_algorithm", None),
                "nonce_count": getattr(client, "_digest_nc", None),
            }
            client_info["digest_auth_info"] = digest_info

    # Redact sensitive information for privacy (only credentials, keep host/base_url for debugging)
    diagnostics_data["client_info"] = _redact_auth_data(
        async_redact_data(client_info, {"_auth", "auth", "_username", "_password"})
    )

    return diagnostics_data


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    # For now, device diagnostics are the same as config entry diagnostics
    return await async_get_config_entry_diagnostics(hass, config_entry)


def get_html_debug_info(coordinator) -> dict[str, Any]:
    """Get debug information about HTML parsing."""
    debug_info = {}

    if not coordinator.data:
        return debug_info

    # Add pages fetched
    pages_fetched = coordinator.data.get("pages_fetched", [])
    debug_info["pages_fetched"] = pages_fetched

    # Add entity availability status
    enabled_entities = coordinator.get_enabled_entities(coordinator.config_entry)
    entity_status = {}

    for entity_key in enabled_entities:
        entity_status[entity_key] = {
            "available": coordinator.is_entity_available(entity_key),
            "has_value": coordinator.get_entity_value(entity_key) is not None,
        }

    debug_info["entity_status"] = entity_status

    # Add parsing statistics
    debug_info["parsing_stats"] = {
        "total_data_items": len(coordinator.data) if coordinator.data else 0,
        "temperature_sensors": (
            len([k for k in coordinator.data.keys() if "temp" in k.lower()])
            if coordinator.data
            else 0
        ),
        "performance_metrics": (
            len(
                [
                    k
                    for k in coordinator.data.keys()
                    if any(
                        metric in k.lower()
                        for metric in ["speed", "capacity", "runtime"]
                    )
                ]
            )
            if coordinator.data
            else 0
        ),
        "system_info": (
            len(
                [
                    k
                    for k in coordinator.data.keys()
                    if any(info in k.lower() for info in ["ip", "version", "log"])
                ]
            )
            if coordinator.data
            else 0
        ),
    }

    return debug_info


def get_connection_debug_info(client) -> dict[str, Any]:
    """Get debug information about the connection."""
    debug_info = {
        "client_initialized": client is not None,
        "host_configured": bool(client.host if client else None),
        "timeout_set": client._timeout is not None if client else None,
        "timeout_value": client._timeout.total if client and client._timeout else None,
        "session_exists": client._session is not None if client else None,
        "session_closed": (
            client._session.closed if client and client._session else None
        ),
    }

    # Add base_url for LOMJsonClient
    if client and hasattr(client, "_base"):
        debug_info["base_url"] = str(client._base)

    # Add authentication status for LOMJsonClient
    if client and hasattr(client, "_username") and hasattr(client, "_password"):
        debug_info["auth_configured"] = bool(client._username and client._password)
        debug_info["auth_type"] = "digest"
    else:
        debug_info["auth_configured"] = False

    # Add auth scheme detection for LOMJsonClient
    if client and hasattr(client, "_username") and hasattr(client, "_password"):
        # This is LOMJsonClient with Digest auth
        debug_info["auth_scheme"] = "digest"
        debug_info["auth_configured"] = bool(client._username and client._password)

        # Add last status code if available
        if hasattr(client, "_last_status_code"):
            debug_info["last_status_code"] = client._last_status_code

    # Redact only credentials, keep host/base_url for debugging
    return async_redact_data(debug_info, {"_auth", "auth"})


def create_diagnostics_report(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Create a comprehensive diagnostics report."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]

    report = {
        "integration": DOMAIN,
        "version": "0.0.1",
        "timestamp": hass.util.dt.utcnow().isoformat(),
        "homeassistant_version": hass.config.version,
    }

    # Add configuration information
    report["configuration"] = {
        "scan_interval": config_entry.options.get("scan_interval", 30),
        "enable_writes": config_entry.options.get("enable_writes", False),
        "enable_solar": config_entry.options.get("enable_solar", True),
        "enable_counters": config_entry.options.get("enable_counters", True),
    }

    # Add connection debug info
    report["connection_debug"] = _redact_auth_data(get_connection_debug_info(client))

    # Add JSON API diagnostics
    json_diagnostics = coordinator.get_json_diagnostics()
    report["json_api_diagnostics"] = json_diagnostics

    # Add formatted table of raw JSON data
    if coordinator.last_raw_json:
        report["raw_json_table"] = coordinator.format_json_as_table()

    # Add entity availability summary
    if coordinator.data:
        report["entity_availability"] = json_diagnostics.get("entity_availability", {})

    # Add parsing statistics and errors
    if coordinator.data and "parsing_stats" in coordinator.data:
        report["parsing_statistics"] = coordinator.data["parsing_stats"]
        report["parsing_details"] = coordinator.data.get("parsing_details", {})

        # Enhanced parsing diagnostics from const.py parse_items function

        if hasattr(const.parse_items, "_last_parsing_stats"):
            report["enhanced_parsing_statistics"] = (
                const.parse_items._last_parsing_stats
            )
        if hasattr(const.parse_items, "_last_parsing_errors"):
            report["parsing_errors"] = const.parse_items._last_parsing_errors
        if hasattr(const.parse_items, "_last_parsing_warnings"):
            report["parsing_warnings"] = const.parse_items._last_parsing_warnings

    # Add unavailable entities list
    unavailable_entities = coordinator.get_unavailable_entities()
    if unavailable_entities:
        report["unavailable_entities"] = unavailable_entities

    # Add entity type counting
    entity_type_counts = count_entities_by_type(coordinator)
    report["entity_type_counts"] = entity_type_counts

    # Add detailed unavailable entity analysis
    unavailable_analysis = identify_unavailable_entities(coordinator)
    report["unavailable_entity_analysis"] = unavailable_analysis

    # Add HTML parsing debug info
    report["parsing_debug"] = get_html_debug_info(coordinator)

    # Add current data summary
    if coordinator.data:
        report["data_summary"] = {
            "last_update": coordinator.data.get("last_update"),
            "total_items": len(coordinator.data),
            "data_keys": list(coordinator.data.keys()),
        }

        # Add sample values (excluding potentially sensitive data)
        sample_data = {}
        for key, value in coordinator.data.items():
            if key in ["last_update", "pages_fetched"]:
                sample_data[key] = value
            elif isinstance(value, int | float | bool):
                sample_data[key] = value
            elif isinstance(value, str) and len(value) < 100:
                sample_data[key] = value
            elif isinstance(value, list):
                sample_data[key] = f"List with {len(value)} items"
            else:
                sample_data[key] = type(value).__name__

        report["sample_data"] = sample_data

    return report


def count_entities_by_type(coordinator) -> dict[str, Any]:
    """Count entities by type (temperature, percentage, binary, etc.)."""
    if not hasattr(coordinator, "id_to_entity_map"):
        return {"error": "No entity mapping available"}

    entity_counts = {
        "temperature": 0,
        "percentage": 0,
        "binary": 0,
        "power": 0,
        "energy": 0,
        "other": 0,
        "total": 0,
    }

    available_counts = entity_counts.copy()

    for _entity_id, entity_info in coordinator.id_to_entity_map.items():
        entity_key = entity_info["key"]
        entity_counts["total"] += 1

        # Count entity types
        device_class = entity_info.get("device_class", "")
        unit = entity_info.get("unit", "")

        if device_class == "temperature":
            entity_type = "temperature"
        elif unit == "%":
            entity_type = "percentage"
        elif device_class in ["binary_sensor", "switch"]:
            entity_type = "binary"
        elif unit in ["W", "kW", "VA", "kVA"]:
            entity_type = "power"
        elif unit in ["kWh", "Wh"]:
            entity_type = "energy"
        else:
            entity_type = "other"

        entity_counts[entity_type] += 1

        # Count available entities
        if coordinator.is_entity_available(entity_key):
            available_counts[entity_type] += 1
            available_counts["total"] += 1

    return {
        "total_entities": entity_counts,
        "available_entities": available_counts,
        "availability_percentage": {
            entity_type: round(
                (
                    (available_counts[entity_type] / entity_counts[entity_type] * 100)
                    if entity_counts[entity_type] > 0
                    else 0
                ),
                1,
            )
            for entity_type in entity_counts.keys()
        },
    }


def identify_unavailable_entities(coordinator) -> dict[str, Any]:
    """Identify unavailable entities with detailed information."""
    if not hasattr(coordinator, "id_to_entity_map"):
        return {"error": "No entity mapping available"}

    unavailable_entities = []

    for entity_id, entity_info in coordinator.id_to_entity_map.items():
        entity_key = entity_info["key"]

        if not coordinator.is_entity_available(entity_key):
            # Determine reason for unavailability
            reason = "Unknown"

            if not coordinator.last_update_success:
                reason = "Last update failed"
            elif not coordinator.data:
                reason = "No data available"
            else:
                # Check if ID was in the last response
                ids_fetched = coordinator.data.get("ids_fetched", [])
                if entity_id not in ids_fetched:
                    reason = "ID not in last JSON response"
                else:
                    # Check if value is None
                    value = coordinator.get_entity_value(entity_key)
                    if value is None:
                        reason = "Value is None (possibly sentinel temperature)"

            unavailable_entities.append(
                {
                    "entity_key": entity_key,
                    "entity_id": entity_id,
                    "name": entity_info["original_name"],
                    "unit": entity_info["unit"],
                    "device_class": entity_info["device_class"],
                    "reason": reason,
                }
            )

    return {
        "unavailable_count": len(unavailable_entities),
        "unavailable_entities": unavailable_entities,
    }
