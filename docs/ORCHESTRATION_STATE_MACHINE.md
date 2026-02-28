# Orchestration State Machine

## States

- `pending`
- `ready`
- `running`
- `blocked`
- `completed`
- `failed`
- `skipped`

## Allowed Transitions

- `pending -> ready|blocked|skipped`
- `ready -> running|blocked|skipped`
- `running -> completed|failed`
- `blocked -> ready|skipped`

Invalid transitions emit:
- `E_STATE_TRANSITION_INVALID`

## Service

Implemented in:
- `main_app/services/agent_dashboard/orchestration_state_service.py`

## Scheduler Integration

`AgentDashboardAssetService` updates state during DAG execution and emits stage diagnostics with:
- `from_state`
- `to_state`
- `transition_valid`
