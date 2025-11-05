# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project Overview
This is a Home Assistant custom component (HACS integration) for SVK Heatpump monitoring and control.

## Critical Non-Obvious Requirements

### Catalog-Driven Architecture
- All entities are defined in `custom_components/svk_heatpump/catalog.yaml`
- Only entries with `enabled: true` are polled from the heat pump
- Each catalog entry must declare ALL properties (id, key, platform, name, device_class, etc.)
- Entity unique IDs must follow pattern: `svk_heatpump-<host>-<id>`

### HTTP Communication Patterns
- Must use `httpx.AsyncClient` with `httpx.DigestAuth(username, password)` for authentication
- Write operations use GET requests (not POST) with `itemno` parameter equal to entity's `id`
- All I/O must be 100% non-blocking async using `DataUpdateCoordinator`

### Home Assistant Integration Patterns
- Domain must be exactly `svk_heatpump`
- Service must be named `svk_heatpump.set_value`
- All entities must be `CoordinatorEntity` sensors
- Must implement reauth flow on 401 errors
- Use `ConfigEntryNotReady` for connection issues during setup

### File Structure Requirements
- Exact structure required - no additional files allowed
- Must include both `en.json` and `da.json` translations
- `manifest.json` must require `httpx>=0.27.0`

### Code Style Requirements
- Python 3.12 compatibility required
- Type hints mandatory throughout
- Use dataclasses or TypedDicts for catalog items
- All functions must have docstrings

### Service Implementation
- Service schema accepts either `{"entity_id": str | list[str], "value": Any}` or `{"id": str, "value": Any}`
- Must resolve `id` from `entity_id` via catalog mapping
- Must enforce write access setting and raise `HomeAssistantError` with friendly text when disabled

### Configuration Flow
- Two-step process: user step (host/ip, username, password), then options step (write access, fetch interval)
- Must perform one read call to confirm connection during validation
- Default values: write access=false, fetch interval=30 seconds

### Value Transformation
- Catalog entries support `value_map` for transforming raw values (e.g., "0" -> "off")
- Catalog entries support `precision` for numeric values
- Can use `translation_key` for entity names requiring proper translation files