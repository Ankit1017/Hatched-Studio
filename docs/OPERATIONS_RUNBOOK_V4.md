# Operations Runbook v4

## Core Signals
- `run_id`: immutable id emitted once per plan execution.
- `StageDiagnostic`: structured stage telemetry (`tool_key`, `intent`, `stage_key`, `attempt`, `duration_ms`, `error_code`).
- `RunLedgerRecord`: durable run summary for workflow-level triage.

## Triage Order
1. Find run by `run_id`.
2. Check run status and `error_counts`.
3. Inspect failing tool summaries.
4. Inspect stage diagnostics for first failing stage.
5. If `verify_result` passed but `policy_gate_result` failed, inspect policy issues in artifact provenance.

## Runtime Flags
- `ENABLE_PARALLEL_DAG=true|false`
- `MAX_PARALLEL_TOOLS=1..16`
- `ENABLE_POLICY_GATE=true|false`
- `POLICY_GATE_MODE=strict|warn_only`
- `RUN_LEDGER_RETENTION_DAYS=1..3650`

## Common Error Codes
- `E_STAGE_TIMEOUT`
- `E_STAGE_EXCEPTION`
- `E_VERIFY_FAILED`
- `E_POLICY_GATE_FAILED`
- `E_PARALLEL_SCHEDULER_FAILURE`
- `E_RUN_LEDGER_WRITE_FAILED`
- `E_DEDUP_SIGNATURE_INVALID`
