# Project Coding Rules (Non-Obvious Only)

## HTTP Communication Patterns
- Always use `httpx.AsyncClient` with `httpx.DigestAuth(username, password)` for authentication
- Write operations use GET requests with `itemno` parameter (not POST with `id`)
- All I/O must be 100% non-blocking async using `DataUpdateCoordinator`

## Catalog-Driven Implementation
- All entities MUST be created from `custom_components/svk_heatpump/catalog.yaml`
- Only entities with `enabled: true` are polled from the heat pump
- Entity unique IDs must follow exact pattern: `svk_heatpump-<host>-<id>`
- Each catalog entry must declare ALL properties (id, key, platform, name, device_class, etc.)

## Home Assistant Integration Requirements
- Domain must be exactly `svk_heatpump` (no variations allowed)
- All entities must inherit from `CoordinatorEntity`
- Service must be named `svk_heatpump.set_value` (exact naming required)
- Must implement reauth flow on 401 errors
- Use `ConfigEntryNotReady` for connection issues during setup

## Code Style Requirements
- Python 3.12 compatibility required (no newer features)
- Type hints mandatory throughout (strict typing enforced)
- Use dataclasses or TypedDicts for catalog items (no regular dicts)
- All functions must have docstrings (no exceptions)

## Service Implementation Patterns
- Service schema must accept either `{"entity_id": str | list[str], "value": Any}` or `{"id": str, "value": Any}`
- Must resolve `id` from `entity_id` via catalog mapping
- Must enforce write access setting and raise `HomeAssistantError` with friendly text when disabled

## Value Transformation
- Catalog entries support `value_map` for transforming raw values (e.g., "0" -> "off")
- Catalog entries support `precision` for numeric values
- Can use `translation_key` for entity names requiring proper translation files

## File Structure Constraints
- Exact structure required - no additional files allowed
- Must include both `en.json` and `da.json` translations
- `manifest.json` must require `httpx>=0.27.0` (exact version requirement)