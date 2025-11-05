# Roo Prompt: Home Assistant HACS Integration — `svk_heatpump`

You are Roo, an expert Home Assistant (HA) custom component generator. Create a production‑ready, **minimal** but extensible HACS integration named **SVK Heatpump** that talks to a LAN controller using **Digest Authentication** and simple HTTP endpoints.

Only implement what is explicitly requested. Avoid unneeded features, diagnostics, options, or sensors beyond the catalog file. Keep code idiomatic with type hints and docstrings.

---

## Goals & Scope (must-have)

- **Platform:** Home Assistant custom component (HACS installable).
- **Domain:** `svk_heatpump` (path: `custom_components/svk_heatpump`).
- **Auth:** **HTTP Digest** auth using IP, username, and password.
- **Endpoints:**
  - **Read (GET):** `http://<IP>/cgi-bin/json_values.cgi?ids=<id1>;<id2>;...`  
    Returns JSON list, e.g.:  
    ```json
    [
      {"id": "301", "name": "HeatPump.RunTime", "value": "33181"},
      {"id": "297", "name": "HeatPump.State", "value": "5"}
    ]
    ```
  - **Write (GET):** `http://<IP>/cgi-bin/rdb_edit.cgi?itemval=<value>&itemno=<id>`  
    Note: `itemno` equals the entity’s `id` (same as read catalog id).
- **Config / Options (and nothing else):**
  - **Host/IP** (string, required).
  - **Username** (string, required).
  - **Password** (secret, required).
  - **Write access** (boolean, default **off**). If **off**, block write service and show warning in logs.
  - **Fetch interval** (integer seconds, default **30**, min **5**, max **3600**).
- **Data model:**
  - IDs to fetch are defined in a **catalog** file: `custom_components/svk_heatpump/catalog.yaml`.
  - Each entry declares **all properties** of an entity: `id`, `key`, `enabled`, `platform`, `device_class`, `unit_of_measurement`, `state_class`, `entity_category`, `icon`, `value_map`, `precision`, etc. Use only the subset needed by HA.
  - **Important**: The `key` field serves dual purpose as both the internal identifier AND the translation key. All entities must use translations - no static names allowed.
  - Only **enabled** entries are polled; others are ignored.
  - Examples (only a few to start; user will provide a full list later).
- **Entities:** Implement **sensors** only to start (no binary_sensors, numbers, switches, etc.). Derive additional platform types later from the same catalog (keep code structured for easy extension).
- **Services:**
  - `svk_heatpump.set_value` — write a value using the write endpoint. Enforce **Write access** setting; if disabled, reject with a helpful error.
- **Internationalization (i18n):** Provide translations for **English** and **Danish**.
- **Docs:** Include **`README.md`** and **`info.md`** in the repo root (concise, install & setup steps, troubleshooting).
- **Testing target:** allow configuring `192.168.50.9` as the device in manual tests (no test-mocks required).

> Important: Keep the implementation **as small as possible**, but cleanly structured for growth. No config entries beyond those listed. No diagnostics, no config flows for extra platforms, no helpers, no entities beyond catalog. No references to external manuals in the code or docs.

---

## Tech & Framework Constraints

- Use **latest HACS-compatible HA integration layout**.
- Use **`httpx`** (async) with **DigestAuth** for requests. Add it as a `manifest.json` requirement.
- Use `DataUpdateCoordinator` for polling.
- Use aio-style patterns and HA’s `ConfigEntry`/`OptionsFlow`.
- Handle **reauth** if credentials fail (401) and provide a simple reauth flow.
- Enforce robust error handling: connection timeouts, non-200 responses, bad JSON.
- Keep logging minimal and helpful (no secrets).

---

## Project Structure

Create exactly these files (and only those required for the MVP):

```
README.md
info.md
logo.png                 # HACS integration logo (128x128px recommended)
hacs.json                # minimal metadata for HACS
custom_components/svk_heatpump/__init__.py
custom_components/svk_heatpump/manifest.json
custom_components/svk_heatpump/config_flow.py
custom_components/svk_heatpump/const.py
custom_components/svk_heatpump/coordinator.py
custom_components/svk_heatpump/api.py
custom_components/svk_heatpump/sensor.py
custom_components/svk_heatpump/services.yaml
custom_components/svk_heatpump/catalog.yaml
custom_components/svk_heatpump/translations/en.json
custom_components/svk_heatpump/translations/da.json
```

### `manifest.json`
- `domain`: `"svk_heatpump"`
- `name`: `"SVK Heatpump"`
- `version`: start at `"0.0.1"`
- `requirements`: `["httpx>=0.27.0"]`
- `codeowners`: `["@repo-owner-placeholder"]`
- `iot_class`: `"local_polling"`
- `integration_type`: `"hub"`
- `config_flow`: `true`

### `hacs.json`
Minimal HACS metadata (name, domains, render_readme).

### Logo Requirements
- **File:** `logo.png` in repository root
- **Size:** 128x128 pixels recommended (square format)
- **Format:** PNG with transparency support
- **Usage:** Must be referenced at the top of both README.md and info.md using markdown: `![SVK Heatpump Logo](logo.png)`
- **Purpose:** Displayed in HACS store and documentation for brand recognition

---

## Behavior & Implementation Details

### Catalog-driven entities
- Load `catalog.yaml` at setup. Example minimal content to include:
  ```yaml
  # custom_components/svk_heatpump/catalog.yaml
  sensors:
    - id: "297"
      key: heatpump_state  # Serves as both internal key AND translation key
      enabled: true
      platform: sensor
      device_class: ""
      unit_of_measurement: ""
      state_class: ""
      icon: "mdi:heat-pump"
      value_map:
        "0": "off"
        "1": "ready"
        "2": "startup"
        "5": "heating"
        "7": "defrost"
    - id: "301"
      key: heatpump_runtime  # Serves as both internal key AND translation key
      enabled: true
      platform: sensor
      device_class: "duration"
      unit_of_measurement: "h"
      state_class: "total_increasing"
      precision: 0
  ```
- Build request `ids` list from enabled entries.
- For each JSON item, map `id` -> entity key via catalog; cast/transform using `precision` and `value_map`.

### API client
- Async `httpx.AsyncClient` with `httpx.DigestAuth(username, password)` and timeouts (default 10 seconds).
- `GET /cgi-bin/json_values.cgi?ids=...` → return list of dicts.
- `GET /cgi-bin/rdb_edit.cgi?itemval=<value>&itemno=<id>` → return success if 200 and basic sanity (no need to parse body).

### Error Handling Requirements
- **Connection timeouts**: Log warning, return empty data, coordinator will retry
- **401 Authentication errors**: Trigger reauth flow immediately
- **403 Forbidden**: Log error, treat as authentication failure
- **404 Not Found**: Log warning, return empty data
- **500+ Server errors**: Log error, return empty data, coordinator will retry
- **Invalid JSON**: Log error, return empty data
- **Network errors**: Log warning, return empty data, coordinator will retry
- **Write operation failures**: Log error with response details, raise HomeAssistantError
- **All errors must be logged without exposing credentials**

### Polling & entities
- `DataUpdateCoordinator` polls at `fetch_interval` seconds with exponential backoff on failures.
- Entities are `CoordinatorEntity` sensors.
- Unique IDs built from host + id (e.g., `svk_heatpump-<host>-<id>`).
- Coordinator should handle partial data gracefully (some entities succeed, others fail)
- Last successful data should be preserved during connection issues

### Config Flow
- **Step 1 (user):** host/ip, username, password.
- **Step 2 (options):** write access (bool, default false), fetch interval (int, default 30). Also accessible later via OptionsFlow.
- **Reauth:** when auth fails, prompt for username+password again.
- **Validation:** perform one read call to confirm connection and at least one enabled id is returned.

### Service: `svk_heatpump.set_value`
- Schema: `{"entity_id": str | list[str], "value": Any}` or `{"id": str, "value": Any}`.
- Resolve `id` from `entity_id` via catalog mapping.
- If write access is **false**, raise `HomeAssistantError` with friendly text.
- Use the write endpoint. Return nothing; log outcome at INFO on success, WARNING on failures.
- **Service error handling**:
  - Invalid entity_id: raise `HomeAssistantError` with "Entity not found"
  - Network timeout: raise `HomeAssistantError` with "Write operation timed out"
  - Authentication failure: raise `HomeAssistantError` with "Authentication failed"
  - Server error: raise `HomeAssistantError` with "Server rejected write operation"
  - Invalid value: raise `HomeAssistantError` with "Invalid value for entity"

### Translations
- `en.json` and `da.json` with keys:
  - titles/labels for config flow & options
  - errors: cannot_connect, invalid_auth, write_disabled
  - **ALL sensor names** using the `key` as translation key (no static names allowed)
- Danish strings should be natural HA style.
- Translation structure:
  ```json
  {
    "entity": {
      "sensor": {
        "heatpump_state": {
          "name": "Heat Pump State"
        },
        "heatpump_runtime": {
          "name": "Heat Pump Runtime"
        }
      }
    }
  }
  ```

### Minimal README.md
- What it does, prerequisites, install via HACS (Custom repo), configuration steps, enabling write access, service example, troubleshooting.
- Include logo reference at the top: `![SVK Heatpump Logo](logo.png)`
- Mention example read endpoints but **do not** reference any external manuals.

### Minimal info.md
- Short description for HACS store card.
- Include logo reference at the top: `![SVK Heatpump Logo](logo.png)`
- Badges optional; keep it short.

---

## Quality & Style

- Python 3.12 compatible.
- Use dataclasses or TypedDicts for catalog items.
- Small, readable modules; no over-engineering.
- 100% non-blocking async I/O.
- Safe logging: never log passwords/queries fully.

---

## Acceptance Criteria

1. Component loads and creates sensor entities from `catalog.yaml` against a reachable device using Digest auth.
2. Only the configured options (IP/username/password/write access/fetch interval) exist.
3. Polling updates sensors; bad network/auth shows `ConfigEntryNotReady` or `reauth` properly.
4. `svk_heatpump.set_value` rejects when write access is off; performs the HTTP write otherwise.
5. English & Danish translations appear in UI (config steps, errors, **ALL entity labels** using the `key` as translation key).
6. A clean `README.md` and `info.md` exist in root with proper logo.png references.
7. Logo.png (128x128px) exists in repository root and is properly referenced in documentation.
8. No unused code, no extra platforms, no diagnostics, no device actions, no config beyond scope.

---

## Deliverables

Generate the full repository content with the structure above. Ensure paths and filenames match exactly. Keep the solution minimal while cleanly architected for later extension (e.g., adding binary_sensors, numbers, switches via the catalog pattern).
