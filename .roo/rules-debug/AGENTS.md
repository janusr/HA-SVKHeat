# Project Debug Rules (Non-Obvious Only)

## Connection Testing
- Manual testing should target device at `192.168.50.9` (from specification)
- Must perform one read call to confirm connection during config flow validation
- Connection timeouts must be handled gracefully with proper error messages

## Authentication Debugging
- Digest authentication failures trigger reauth flow (401 responses)
- Use `ConfigEntryNotReady` for connection issues during setup
- HTTP communication uses GET requests for both read and write operations

## Service Debugging
- Write operations fail silently if write access is disabled (must raise HomeAssistantError)
- Service accepts both entity_id and id parameters - test both paths
- Value transformations via catalog `value_map` must be applied correctly

## Entity Debugging
- Only entities with `enabled: true` in catalog.yaml are polled
- Entity unique IDs follow pattern: `svk_heatpump-<host>-<id>`
- All entities must be CoordinatorEntity instances

## Configuration Flow Debugging
- Two-step process: user credentials, then options (write access, fetch interval)
- Default values: write access=false, fetch interval=30 seconds
- Must validate connection with actual read call during setup