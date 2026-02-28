# Architecture Boundaries (Phase 1)

This document defines package-level dependency direction for the domain-first layout.

## Layers

1. `main_app/app`
- Composition root and runtime bootstrap.
- Can depend on all runtime layers.

2. `main_app/ui`
- Rendering and interaction only.
- Must not be imported by `domains`, `orchestration`, or `platform`.

3. `main_app/domains`
- Asset-specific behavior (topic, quiz, slideshow, video, etc).
- Must not import `ui`.

4. `main_app/orchestration`
- Cross-asset workflow execution, stage lifecycle, and governance.
- Must not import tab or renderer modules from `ui`.

5. `main_app/platform`
- Contracts, config, error taxonomy, storage abstractions.
- No dependency on `ui`.

6. `main_app/shared`
- Cross-cutting helpers and utilities.
- No dependency on `ui`.

## Compatibility Policy

Phase 1 keeps legacy imports operational through shims:

- `main_app/services/agent_dashboard/*` remains source-compatible.
- New modules are introduced under:
  - `main_app/orchestration/*`
  - `main_app/platform/*`
  - `main_app/domains/*`
  - `main_app/plugins/sdk/*`
  - `main_app/ui/shell/*`
  - `main_app/shared/*`

## Boundary Enforcement

Use:

```bash
python scripts/check_import_cycles.py --package main_app --check-boundaries
```

For strict enforcement:

```bash
python scripts/check_import_cycles.py --package main_app --check-boundaries --enforce-boundaries
```

Default CI mode in Phase 1 is warning-only for boundary violations.
