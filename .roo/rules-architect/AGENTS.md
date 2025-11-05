# Project Architecture Rules (Non-Obvious Only)

## Catalog-Driven Architecture
- All entities defined in single `catalog.yaml` file - this is the source of truth
- Catalog supports multiple platform types (sensors, binary_sensors, etc.)
- Each entry must declare ALL properties (id, key, enabled, platform, name, device_class, etc.)
- Only entities with `enabled: true` are polled from the heat pump

## HTTP Communication Layer
- Must use `httpx.AsyncClient` with `httpx.DigestAuth(username, password)`
- Write operations use GET requests with `itemno` parameter (counterintuitive)
- All I/O must be 100% non-blocking async using `DataUpdateCoordinator`
- Must handle connection timeouts, non-200 responses, and bad JSON

## Home Assistant Integration Constraints
- Domain must be exactly `svk_heatpump`
- All entities must be `CoordinatorEntity` sensors
- Service must be named `svk_heatpump.set_value`
- Must implement reauth flow on 401 errors
- Use `ConfigEntryNotReady` for connection issues during setup

## Service Architecture
- Service schema accepts either `{"entity_id": str | list[str], "value": Any}` or `{"id": str, "value": Any}`
- Must resolve `id` from `entity_id` via catalog mapping
- Must enforce write access setting at service level
- Must raise `HomeAssistantError` with friendly text when write access disabled

## Configuration Flow Architecture
- Two-step process: user step (host/ip, username, password), then options step
- Must perform one read call to confirm connection during validation
- Default values: write access=false, fetch interval=30 seconds
- Must trigger reauth flow on credential failures

## Translation Architecture
- Must include both `en.json` and `da.json` translations
- Entity names can use `translation_key` requiring proper translation files
- Must include titles/labels for config flow & options, errors, and sensor names