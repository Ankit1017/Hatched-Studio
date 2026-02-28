# Developer Onboarding Fastpath

## Add a New Tool in 10 Steps

1. Scaffold:
`python scripts/scaffold_tool_plugin.py --intent "my new tool" --kind structured`
2. Open generated plugin file under:
`main_app/services/agent_dashboard/executor_plugins/`
3. Implement executor wiring TODOs.
4. Adjust produced dependency artifact keys if needed.
5. Update schema data type/required section if needed.
6. Optionally scaffold renderer:
`--with-renderer true`
7. Validate plugin and schema:
`python scripts/validate_plugin_specs.py`
8. Simulate workflow behavior:
`python scripts/simulate_workflow.py --intents topic,my new tool --dry`
9. Run fast dev checks:
`python scripts/dev_checks.py`
10. Run full tests before PR:
`python -m pytest tests`

## Common Failures and Fixes

1. Missing `execution_spec`:
- Add full stage/dependency config in plugin spec.
2. Missing schema file:
- Ensure `schema_ref.id/version` matches filename in `main_app/schemas/assets`.
3. Simulation shows blocked node:
- Check required artifacts are produced by upstream tools.
4. Schema validation fails at runtime:
- Align primary section key and data type with schema file.
