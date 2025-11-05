# Project Documentation Rules (Non-Obvious Only)

## Architecture Documentation
- This is a Home Assistant custom component (HACS integration) for SVK Heatpump
- Uses catalog-driven architecture - all entities defined in single catalog.yaml file
- HTTP Digest Authentication for communication with LAN-based heat pump controller

## Counterintuitive Patterns
- Write operations use GET requests (not POST) with `itemno` parameter
- Domain must be exactly `svk_heatpump` (no variations allowed)
- Only entries with `enabled: true` in catalog are polled from heat pump
- Exact file structure required - no additional files allowed

## Hidden Dependencies
- Requires `httpx>=0.27.0` for Digest Authentication
- Must provide both English and Danish translations
- Uses DataUpdateCoordinator for all async operations
- Entity creation tightly coupled to catalog structure

## Configuration Requirements
- Two-step configuration flow: credentials, then options
- Must perform actual read call to validate connection during setup
- Default values: write access=false, fetch interval=30 seconds
- Must implement reauth flow for credential failures