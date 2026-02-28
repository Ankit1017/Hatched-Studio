# Operations Runbook

## Runtime Controls

Environment flags:

1. `USE_GENERIC_ASSET_FLOW`
- `true` default
- `false` uses linear fallback path

2. `ENABLE_VERIFY_STAGE`
- `true` default
- `false` disables verification stage

3. `WORKFLOW_FAIL_POLICY`
- `continue` default
- `fail_fast` stops workflow on first failed tool

4. `EXECUTE_RETRY_COUNT`
- default `1`
- retries only execute stage failures marked retryable

5. `STAGE_TIMEOUT_MS`
- global timeout default for stages

6. `EXECUTE_STAGE_TIMEOUT_MS`
- execute stage timeout override (default 30000ms)

7. `VERIFY_STAGE_TIMEOUT_MS`
- verify stage timeout override (default 5000ms)

## Error Code Matrix

1. `E_TOOL_NOT_REGISTERED`
- tool intent was not mapped to an executor

2. `E_PAYLOAD_MISSING_MANDATORY`
- required payload fields were missing

3. `E_DEPENDENCY_MISSING`
- required upstream artifact not available

4. `E_EXECUTOR_FAILED`
- executor returned failure result

5. `E_PARSE_FAILED`
- parser path failed for structured generation

6. `E_ARTIFACT_NORMALIZATION_FAILED`
- conversion to normalized artifact envelope failed

7. `E_VERIFY_FAILED`
- strict verification failed

8. `E_VERIFY_PROFILE_UNKNOWN`
- unknown verify profile configured; fallback applied

9. `E_ARTIFACT_SCHEMA_MISMATCH`
- artifact shape did not satisfy schema gate

10. `E_STAGE_TIMEOUT`
- stage exceeded timeout budget

11. `E_STAGE_EXCEPTION`
- unexpected stage exception occurred

12. `E_WORKFLOW_CYCLE`
- workflow DAG cycle detected

## Triage Flow

1. Identify failing asset/tool from notes (`run_id`, `tool_key`, `stage_key`)
2. Inspect artifact error section:
- `artifact.sections[*].data.code`
- `artifact.sections[*].data.stage`
- `artifact.sections[*].data.details`
3. Inspect verification block:
- `artifact.provenance.verification.status`
- `artifact.provenance.verification.issues`
4. Inspect stage metrics:
- `artifact.metrics.stage_durations_ms`
- `artifact.metrics.total_duration_ms`
- `artifact.metrics.retry_count`
5. Check dependency suppression notes when downstream tools fail after verify failure.

## SLO Snapshots

Use `OpsReportingService` to compute:

1. success rate by intent
2. verify failure rate by intent
3. top error codes
4. total duration p50/p95
