# Policy Gates

## Profiles
- `text_policy_gate`: text assets (`topic`, `report`)
- `structured_policy_gate`: structured assets
- `media_policy_gate`: media assets (`video`, `audio_overview`)

## Lifecycle Position
`policy_gate_result` runs after `verify_result` and before `finalize_result`.

## Modes
- `strict`: policy errors fail the asset.
- `warn_only`: policy issues are recorded, asset can continue.

## Provenance Shape
Policy output is written to:
- `artifact.provenance.policy_gate.status`
- `artifact.provenance.policy_gate.issues`
- `artifact.provenance.policy_gate.checks_run`

## Metrics
- `artifact.metrics.policy_enforced`
- `artifact.metrics.queue_wait_ms`
- `artifact.metrics.attempt_durations_ms`
