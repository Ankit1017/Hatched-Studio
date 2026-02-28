# Migration Guide: Folder Restructure

## Scope

This guide tracks the phased migration from legacy layer-first paths to the domain-first platform layout.

## Phase 1 (Current): Skeleton + Compatibility

Completed goals:

1. Added new package skeleton:
- `main_app/app`
- `main_app/platform`
- `main_app/orchestration`
- `main_app/domains`
- `main_app/plugins/sdk`
- `main_app/ui/shell`
- `main_app/shared`

2. Introduced compatibility facades:
- Legacy `main_app/services/agent_dashboard/__init__.py` re-exports orchestration APIs.
- New wrapper modules map to existing service implementations.

3. Added architecture check tooling:
- `scripts/check_import_cycles.py --check-boundaries`

4. Moved app composition to:
- `main_app/app/dependency_container.py`
- `main_app/app/bootstrap.py`
- `main_app/app/runtime.py`

## Phase 2: Domain Extraction + Import Cleanup

Planned:

1. Move implementation files from `main_app/services/*` and `main_app/parsers/*` into `main_app/domains/*`.
2. Keep old import paths as deprecating shims.
3. Update plugin discovery paths to prefer `main_app/plugins/tool_plugins` and `main_app/plugins/workflow_plugins`.
4. Enforce boundary checks for new modules.

## Phase 3: Final Cutover

Planned:

1. Remove deprecated legacy module aliases.
2. Update scaffold scripts to generate only domain-first paths.
3. Enable strict architecture boundary enforcement by default.
4. Freeze ownership and dependency rules in CI.
