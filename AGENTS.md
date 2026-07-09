# AGENTS.md

This file provides guidance for AI coding agents working in this repository.

## Data anonymization (mandatory)

**All concrete data committed to this repository must be anonymized.** This applies everywhere: test fixtures, documentation examples, scripts, comments, and any other artifacts that contain VideoIPath or customer-specific information.

Before adding or modifying data, replace real identifiers with generic placeholders:

| Category | Do not commit | Use instead |
|---|---|---|
| Hostnames / FQDNs | `vip-prod.example.customer.com` | `vip-server.example` or `device-host-a` |
| IP addresses | Real network addresses | `10.0.0.1`, `192.0.2.1` (RFC 5737 documentation ranges) |
| Usernames / passwords | Real credentials | `test-user`, `test-password` |
| Device / module / port names | Customer site labels | `device-a`, `module-1`, `port-out-1` |
| Service / path / edge labels | Production naming | `service-a`, `path-1`, `edge-a` |
| Organization / site names | Customer or internal names | `example-org`, `site-a` |
| MAC addresses, serial numbers | Real hardware IDs | Synthetic values with no production mapping |

Rules:

1. **Never commit live API responses as-is.** Capture from a real server only in a local, untracked workflow; anonymize before staging.
2. **Apply the same rules to docs and inline examples** — a markdown code block with a real hostname is as sensitive as a JSON fixture.
3. **Preserve structure, not identity.** Keep IDs, relationships, and field shapes realistic so tests and docs remain meaningful; only replace identifying values.
4. **Review diffs for leaks.** Scan new files for hostnames, email addresses, customer abbreviations, and internal project codenames.
5. **When in doubt, generalize.** Prefer `device-a` / `port-out-1` style names already used under `tests/fixtures/`.

Inspect fixtures can be anonymized with `scripts/anonymize_inspect_fixtures.py` when available.

## Commands

```bash
# Install all dependencies (including dev and test groups)
poetry install --with dev,test

# Run unit tests (offline; same as CI default)
poetry run test-unit

# Run e2e tests against a live server (loads connection vars from .env — see .env.template)
poetry run test-e2e

# Run unit then e2e sequentially
poetry run test

# Single file or test (extra args pass through)
poetry run test-unit tests/validators/test_device_id.py
poetry run test-e2e tests/e2e/inspect/test_e2e_inspect.py::test_name

# Bare pytest also runs unit tests only (e2e excluded via pyproject addopts)
poetry run pytest

# Lint with auto-fix
poetry run ruff check --fix src/ tests/

# Format
poetry run ruff format src/ tests/

# Install pre-commit hooks (runs ruff lint+format on commit)
pre-commit install

# Driver schema CLI tools (after package install)
set-videoipath-version <version>   # e.g. 2024.3.3
get-videoipath-version
list-videoipath-versions
```

## Agent rules

Global repo guidance lives in this file. Path-scoped Python rules are in `.claude/rules/`:

- `python-style.md` — type hints, ruff formatting, naming, pathlib
- `python-quality.md` — Pydantic, exceptions, lint gates, change scope
- `python-testing.md` — pytest, fixtures, fakes, e2e gating
- `agent-rules-layout.md` — how to add/remove rules and maintain `.cursor/rules/` symlinks

Cursor reads the same content via symlinks in `.cursor/rules/*.mdc`. Canonical rule files live in `.claude/rules/`; see `agent-rules-layout.md` when creating or deleting rules. Python rules load when working on files under `src/` or `tests/`.

## Architecture

### Three-layer design

```
VideoIPathApp  (public entry point — src/videoipath_automation_tool/apps/videoipath_app.py)
    ├── inventory   → InventoryApp
    ├── topology    → TopologyApp
    ├── preferences → PreferencesApp
    ├── profile     → ProfileApp
    └── security    → SecurityApp

Each App:
    App class  (user-facing methods, business logic)
      └── *API class  (raw API calls, response parsing)
            └── VideoIPathConnector  (src/videoipath_automation_tool/connector/)
                  ├── VideoIPathRestConnector  (REST v2 GET/PATCH)
                  └── VideoIPathRPCConnector   (RPC POST)
```

`VideoIPathApp` lazily initializes each sub-app on first property access. When `VIPAT_ENVIRONMENT=DEV`, the internal `*_api` objects are also exposed directly on the `VideoIPathApp` instance for easier exploration.

### Connector layer

`VideoIPathConnector` (`connector/vip_connector.py`) wraps two low-level connectors for the two VideoIPath API styles:
- **REST connector**: `/rest/v2/data/…` endpoints (GET, PATCH)
- **RPC connector**: RPC POST calls

Response models live in `connector/models/` as Pydantic models.

### Inventory app structure

`InventoryApp` (`apps/inventory/`) uses Python mixins to split its methods across files:
- `app/app.py` — composes `InventoryCreateDeviceMixin`, `InventoryGetDeviceMixin`, etc.
- `inventory_api.py` — raw API methods
- `model/drivers.py` — auto-generated driver schemas; `SELECTED_SCHEMA_VERSION` and `AVAILABLE_SCHEMA_VERSIONS` control which VideoIPath server version is targeted

### Inspect app (in-progress)

`apps/inspect/` follows a different, read-only pattern built around `InspectSnapshot`:
- `snapshot.py` — builds in-memory indexes from a bulk API response; domain objects (`InspectDevice`, `InspectPort`, `InspectEdge`, `InspectService`) are created lazily and cached on the snapshot
- `domain/` — thin view objects that hold a back-reference to the snapshot for cross-entity lookups
- `model/` — raw Pydantic models for the API response (`collector.py`, etc.)

### Driver versioning

Driver schemas (Pydantic models for device `custom_settings`) are auto-generated from the VideoIPath API's JSON schema and live under `apps/inventory/model/drivers.py`. Run `set-videoipath-version <version>` to regenerate them for a different server version. The CLI scripts are in `src/vipat_cli_scripts/`.

### Settings and environment variables

All configuration is loaded via `Settings` (`settings.py`, backed by `pydantic-settings`). Variables are prefixed `VIPAT_`. Copy `.env.template` to `.env` for local development and e2e tests (gitignored). Unit tests set dummy `VIPAT_*` values in `tests/conftest.py`.

Key variables:
| Variable | Default | Notes |
|---|---|---|
| `VIPAT_ENVIRONMENT` | `PROD` | `DEV` exposes internal APIs on `VideoIPathApp` |
| `VIPAT_VIDEOIPATH_SERVER_ADDRESS` | — | Required |
| `VIPAT_VIDEOIPATH_USERNAME` | — | Required |
| `VIPAT_VIDEOIPATH_PASSWORD` | — | Required |
| `VIPAT_USE_HTTPS` | `true` | |
| `VIPAT_VERIFY_SSL_CERT` | `true` | |
| `VIPAT_LOG_LEVEL` | _(root logger)_ | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` |
| `VIPAT_ADVANCED_DRIVER_SCHEMA_CHECK` | `true` | Compares local vs. server driver schema on init |

## Release process

1. Update `version` in `pyproject.toml`
2. Create a GitHub Release with a `v*` tag
3. CI builds and publishes to PyPI automatically

Hotfix branches must use the `hotfix/` prefix. Development builds are published automatically for every commit on `main` or open PRs with a `.dev<run_id>` suffix.
