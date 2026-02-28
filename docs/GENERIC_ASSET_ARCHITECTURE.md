# Generic Asset Architecture

## Goal

Provide one generic platform for all assets where:
- tools declare metadata and dependencies,
- workflows execute as DAGs,
- results use one normalized artifact contract,
- UI/history can render new tools with minimal custom code.

## Core Building Blocks

## 1) Contracts

Defined in `main_app/contracts.py`:

- `AssetSection`
- `AssetArtifactEnvelope`
- `ToolDependencySpec`
- `ToolExecutionSpec`

These contracts make output and orchestration metadata explicit.

## 2) Tool Specs

Defined in `main_app/services/agent_dashboard/tool_registry.py`:

Each tool has:
- business identity (`intent`, `title`, `description`)
- execution metadata (`execution_spec`)

`execution_spec` includes:
- `stage_profile`
- `requirements_schema_key`
- dependency I/O artifact keys

## 3) Workflow DAG

Defined in `main_app/services/agent_dashboard/workflow_registry.py`:

- static workflows include optional `tool_dependencies`
- runtime `plan_selected_assets` infers edges from tool dependency outputs/inputs
- DAG resolver performs topological sort and emits cycle notes

## 4) Stage Orchestrator

Defined in `main_app/services/agent_dashboard/tool_stage_service.py`:

Stages:
1. `validate_tool_registration`
2. `validate_stage_requirements`
3. `resolve_dependencies`
4. `execute_tool`
5. `normalize_artifact`
6. `validate_schema`
7. `verify_result`
8. `policy_gate_result`
9. `finalize_result`

Context carries:
- tool metadata
- payload
- available artifacts
- resolved input artifacts
- execution trace

## 5) Artifact Adapter

Defined in `main_app/services/agent_dashboard/artifact_adapter.py`:

Responsibilities:
- artifact key constants and defaults
- `legacy_result_to_artifact(...)`
- produced artifact extraction for downstream tools

## 6) Executor Result Handlers

Defined in `main_app/services/agent_dashboard/executor_plugins/parsed_asset_result.py`:

- `build_artifact_result(...)`
- `build_error_asset_result(...)`
- `build_content_asset_result(...)`
- `build_media_asset_result(...)`
- `build_parsed_asset_result(...)`

All executors should return through these helpers.

## Runtime Flow

1. Planner outputs intents + payloads
2. Asset service resolves tools and builds runtime workflow
3. Workflow resolver returns DAG order
4. Each tool runs through stage orchestrator
5. Produced artifacts are added to shared artifact map
6. Downstream tools consume dependencies
7. Final results include both legacy fields and artifact envelope

## Compatibility Strategy

- Keep legacy `AgentAssetResult` fields
- Attach `artifact` alongside legacy fields (dual shape)
- UI/history fallback renderers prefer artifact sections when present
- no data migration required for old history records

## Feature Flag

- `USE_GENERIC_ASSET_FLOW`
- enabled by default
- set to `false` (`0/no/off`) for linear fallback path
- `ENABLE_VERIFY_STAGE`
- enabled by default
- set to `false` (`0/no/off`) to skip verification stage
- `ENABLE_POLICY_GATE`
- enabled by default
- set to `false` (`0/no/off`) to skip policy gate stage
- `SCHEMA_VALIDATE_ENFORCE`
- enabled by default
- set to `false` to record schema issues without failing
- `POLICY_GATE_MODE`
- `strict` (default) or `warn_only`
- `ENABLE_PARALLEL_DAG`
- enabled by default
- set to `false` to force sequential DAG execution
- `MAX_PARALLEL_TOOLS`
- maximum parallel ready-tools (default `2`)
- `WORKFLOW_FAIL_POLICY`
- `continue` (default) or `fail_fast`
- `EXECUTE_RETRY_COUNT`
- default `1` retry for execute stage
- `STAGE_TIMEOUT_MS`, `EXECUTE_STAGE_TIMEOUT_MS`, `VERIFY_STAGE_TIMEOUT_MS`
- timeout budgets for stage execution

## Troubleshooting

## Missing dependency artifact

Symptom:
- tool returns error before execution

Check:
- `tool.execution_spec.dependency.requires_artifacts`
- upstream tool `produces_artifacts`
- stage notes for `resolve_dependencies`

## Cycle warning in workflow

Symptom:
- note contains `Workflow dependency cycle detected`

Fix:
- update workflow `tool_dependencies`
- or adjust produced/required artifact keys in tool specs

## New tool not rendering nicely

Default behavior:
- generic section renderer shows artifact sections

Enhancement:
- add tool-specific renderer plugin for richer UX

## Adding a New Tool Checklist

1. Add requirement schema for intent
2. Register tool with execution spec + dependencies
3. Add executor plugin using shared result helper
4. Add tests for registry, DAG behavior, and artifact output
5. Optional: add renderer plugins for dashboard/history
