# Agent Dashboard Workflows and Tools

## Package Map (Phase 1 Domain-First)

Primary runtime and compatibility namespaces:

1. `main_app/orchestration/*`
- New orchestration-facing namespace (engine, registries, governance, telemetry).

2. `main_app/platform/*`
- Contracts, runtime config, and error taxonomy facades.

3. `main_app/domains/*`
- Domain-specific service facades per asset.

4. `main_app/app/*`
- Bootstrap and dependency composition container.

5. `main_app/services/*`
- Backward-compatible legacy paths preserved during migration.

## Definitions

- `Tool`: a single executable asset capability mapped to one intent and one executor plugin.
- `Workflow`: a named set of tools plus optional dependency edges for DAG execution.
- `Tool Execution Spec`: per-tool metadata that drives stage profile, requirement schema key, and artifact dependencies.
- `tool_stage`: reusable lifecycle stages executed by `AgentToolStageOrchestrator`.
- `Artifact Envelope`: normalized output contract (`artifact`) attached to every `AgentAssetResult`.

## Generic Contracts

Primary types live in `main_app/contracts.py`:

1. `AssetSection`
- `kind`, `key`, `title`, `data`, `mime`, `optional`

2. `AssetArtifactEnvelope`
- `intent`, `title`, `summary`, `sections`, `attachments`, `metrics`, `provenance`

3. `ToolDependencySpec`
- `requires_artifacts`, `produces_artifacts`, `optional_requires`

4. `ToolExecutionSpec`
- `intent`, `tool_key`, `stage_profile`, `requirements_schema_key`, `dependency`

`AgentAssetResult` in `main_app/models.py` now includes:
- `artifact: AssetArtifactEnvelope | None`
- plus backward-compatible legacy fields (`content`, `audio_bytes`, `parse_note`, `raw_text`, etc.)

## Current Tool Inventory

Source of truth:
- `main_app/services/agent_dashboard/tool_registry.py`

Default tools:

1. `topic`
2. `mindmap`
3. `flashcards`
4. `data table`
5. `quiz`
6. `slideshow`
7. `video`
8. `audio_overview`
9. `report`

Each tool is registered with `execution_spec` that declares:
- stage profile
- requirement schema key
- dependency artifact inputs/outputs

## Current Workflow Inventory

Source of truth:
- `main_app/services/agent_dashboard/workflow_registry.py`

Default named workflows:

1. `core_learning_assets`
- tools: `topic`, `mindmap`, `flashcards`, `quiz`, `slideshow`

2. `media_production_assets`
- tools: `slideshow`, `video`, `audio_overview`, `report`
- explicit edge: `slideshow -> video`

3. `full_asset_suite`
- tools: all defaults in intent order

Runtime workflow:

1. `plan_selected_assets`
- generated from active plan intents
- dependencies inferred from tool execution specs
- resolved with DAG topological ordering (catalog order tie-break)
- optional resume support: `resume_from_run_id`, `resume_from_tool_key`

## Stage Profiles and Lifecycle

Source of truth:
- `main_app/services/agent_dashboard/tool_stage_service.py`

Current profiles:

1. `default_asset_profile`
2. `media_asset_profile`

Current stage sequence:

1. `validate_tool_registration`
2. `validate_stage_requirements`
3. `resolve_dependencies`
4. `execute_tool`
5. `normalize_artifact`
6. `validate_schema`
7. `verify_result`
8. `policy_gate_result`
9. `finalize_result`

Requirement coverage:
- every stage has at least one requirement check
- dependency stage enforces required artifact inputs
- normalization stage ensures every result has artifact envelope
- verify stage enforces strict output quality and shape checks

## Artifact Dependency Defaults

Source of truth:
- `main_app/services/agent_dashboard/artifact_adapter.py`

Produced artifacts by tool:

1. `topic` -> `artifact.topic.text`
2. `mindmap` -> `artifact.mindmap.tree`
3. `flashcards` -> `artifact.flashcards.cards`
4. `data table` -> `artifact.table.data`
5. `quiz` -> `artifact.quiz.data`
6. `slideshow` -> `artifact.slideshow.slides`
7. `video` -> `artifact.video.payload`, `artifact.video.audio`
8. `audio_overview` -> `artifact.audio_overview.payload`, `artifact.audio_overview.audio`
9. `report` -> `artifact.report.text`

Required dependency example:
- `video` requires `artifact.slideshow.slides`

## Single Point Result Handling

Source of truth:
- `main_app/services/agent_dashboard/executor_plugins/parsed_asset_result.py`

Shared handlers:

1. `build_artifact_result(...)`
2. `build_error_asset_result(...)`
3. `build_content_asset_result(...)`
4. `build_media_asset_result(...)`
5. `build_parsed_asset_result(...)`

Behavior:
- all executor plugins return through shared handlers
- shared handler constructs `AgentAssetResult`
- shared handler attaches normalized `artifact` envelope

## Verification and Errors

Source of truth:
- `main_app/services/agent_dashboard/verification_service.py`
- `main_app/services/agent_dashboard/error_codes.py`

Verification profiles:
1. `text_asset_verify`
2. `structured_asset_verify`
3. `media_asset_verify`

Strict verification policy:
- verification runs after artifact normalization
- any verification `error` fails the asset (`status=error`)
- failed assets do not publish dependency artifacts
- unknown verify profile creates warning issue and falls back safely

Standard error codes:
- `E_TOOL_NOT_REGISTERED`
- `E_PAYLOAD_MISSING_MANDATORY`
- `E_DEPENDENCY_MISSING`
- `E_EXECUTOR_FAILED`
- `E_ARTIFACT_NORMALIZATION_FAILED`
- `E_VERIFY_FAILED`
- `E_WORKFLOW_CYCLE`
- `E_STAGE_TIMEOUT`
- `E_STAGE_EXCEPTION`
- `E_VERIFY_PROFILE_UNKNOWN`
- `E_ARTIFACT_SCHEMA_MISMATCH`
- `E_SCHEMA_VALIDATION_FAILED`
- `E_PLUGIN_SPEC_INVALID`
- `E_STATE_TRANSITION_INVALID`

Runtime invariants:
1. Each stage emits timing (`started_at`, `ended_at`, `duration_ms`) and status.
2. Artifact metrics include:
- `stage_durations_ms`
- `attempt_durations_ms`
- `total_duration_ms`
- `retry_count`
- `verification_issue_count`
- `queue_wait_ms`
- `policy_enforced`
3. Every stage failure contains structured error section with `code`, `stage`, `message`, and `details`.

## Execution Flow (Generic)

1. Resolve tools from plan intents
2. Build runtime workflow (`plan_selected_assets`)
3. Resolve DAG order + detect cycles
4. Execute stage lifecycle per tool
5. Verify each result (`verify_result`)
6. Validate schema contracts (`validate_schema`)
7. Apply governance checks (`policy_gate_result`)
8. Collect produced artifacts only from verified/policy-passed tools
9. Continue independent tools even if one branch fails
10. Return ordered `AgentAssetResult` list

## Simulation Mode

- `AgentDashboardAssetService.simulate_plan_execution(...)` provides a no-side-effect plan simulation.
- Simulation returns:
  - planned DAG order
  - expected stage sequence per tool
  - planned state path (`pending -> ready -> running -> completed/blocked`)
  - dependency block hints
- Simulation does not execute tool executors and does not mutate run/stage ledgers.

## Per-Asset Plan / Execute / Verify

1. `topic`
- Plan: require `topic`
- Execute: generate explainer text
- Verify: `artifact.topic.text` exists and text length is meaningful

2. `mindmap`
- Plan: require `topic`
- Execute: generate parsed map tree
- Verify: root node has `name`, structure is valid tree

3. `flashcards`
- Plan: require `topic`
- Execute: generate cards payload
- Verify: cards exist and include `question` + `short_answer`

4. `data table`
- Plan: require `topic`
- Execute: generate table payload
- Verify: columns and rows are present and consistent

5. `quiz`
- Plan: require `topic`
- Execute: generate quiz payload
- Verify: questions exist, option counts are valid, answer index fits bounds

6. `slideshow`
- Plan: require `topic`
- Execute: generate slides
- Verify: non-empty slide list and slide content fields present

7. `video`
- Plan: require `topic` and slideshow dependency artifact
- Execute: generate video payload + audio
- Verify: payload/slides/scripts are present and audio output is represented

8. `audio_overview`
- Plan: require `topic`
- Execute: generate dialogue payload + audio
- Verify: dialogue turns exist and audio output is represented

9. `report`
- Plan: require `topic`
- Execute: generate report markdown/text
- Verify: primary report text section exists and is non-empty

## Backward Compatibility

1. Legacy fields in `AgentAssetResult` remain available
2. `legacy_result_to_artifact(...)` adapts old-shaped results to envelope
3. UI default/fallback renderers read artifact sections when present, else legacy payload
4. No destructive migration for stored history

## Feature Flag

- `USE_GENERIC_ASSET_FLOW`
- default: enabled
- values `0/false/no/off` switch to linear compatibility path
- `ENABLE_VERIFY_STAGE`
- default: enabled
- values `0/false/no/off` skip verification stage
- `ENABLE_PARALLEL_DAG`
- `MAX_PARALLEL_TOOLS`
- `ENABLE_POLICY_GATE`
- `POLICY_GATE_MODE` (`strict` or `warn_only`)
- `SCHEMA_VALIDATE_ENFORCE`

## How to Add a New Tool

1. Add intent requirement spec and optional metadata in:
- `main_app/services/intent/intent_requirement_spec.py`

2. Register tool in:
- `main_app/services/agent_dashboard/tool_registry.py`
- include `execution_spec` with stage profile + dependencies

3. Add executor plugin in:
- `main_app/services/agent_dashboard/executor_plugins/<tool>.py`
- return with shared handler `build_artifact_result(...)` or wrappers

4. Optional UI enhancers:
- agent dashboard renderer plugin
- asset history renderer plugin

5. Add/extend tests:
- tool metadata
- workflow DAG behavior
- stage orchestration
- plugin artifact output

## How to Create/Modify Workflows

1. Add/update `AgentWorkflowDefinition` in:
- `main_app/services/agent_dashboard/workflow_registry.py`

2. Set:
- `tool_keys` in preferred order
- `tool_dependencies` for explicit edges

3. Validate with DAG resolver tests.

## Key Files

- `main_app/contracts.py`
- `main_app/models.py`
- `main_app/services/agent_dashboard/artifact_adapter.py`
- `main_app/services/agent_dashboard/tool_registry.py`
- `main_app/services/agent_dashboard/workflow_registry.py`
- `main_app/services/agent_dashboard/tool_stage_service.py`
- `main_app/services/agent_dashboard/asset_service.py`
- `main_app/services/agent_dashboard/executor_plugins/parsed_asset_result.py`
- `docs/GENERIC_ASSET_ARCHITECTURE.md`
