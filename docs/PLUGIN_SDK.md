# Plugin SDK

## Tool Plugin Spec

Tool plugins are declared with `ToolPluginSpec` and registered via tool registry adapters.

Required fields:
- `plugin_key`
- `intent`
- `execution_spec`

Recommended fields:
- `title`
- `description`
- `capabilities`
- `schema_ref`

Validation helper:
- `main_app/plugins/sdk/plugin_sdk.py`
- `validate_tool_plugin_spec(...)`
- `normalize_tool_plugin_spec(...)`
- `plugin_spec_fix_hints(...)`
- `default_capabilities_for_intent(...)`

## Workflow Plugin Spec

Workflow plugins are declared with `WorkflowPluginSpec`.

Required fields:
- `workflow_key`
- `tool_keys`

Validation helper:
- `validate_workflow_plugin_spec(...)`

## Scaffolding

Target structure for new plugins:
- tool plugins: `main_app/plugins/tool_plugins/`
- workflow plugins: `main_app/plugins/workflow_plugins/`
- renderer plugins: `main_app/plugins/renderer_plugins/`
- domain services: `main_app/domains/<intent>/services/`

Use:

```bash
python scripts/scaffold_tool_plugin.py --intent "new asset"
```

Advanced options:

```bash
python scripts/scaffold_tool_plugin.py \
  --intent "new asset" \
  --kind structured \
  --depends-on artifact.topic.text \
  --produces artifact.new_asset.primary \
  --with-renderer true \
  --with-workflow-key full_asset_suite
```

This creates:
- plugin spec skeleton
- schema file
- unit test skeleton
- optional renderer plugin skeleton

## Fast Validation

Run:

```bash
python scripts/validate_plugin_specs.py
python scripts/simulate_workflow.py --workflow full_asset_suite --dry
python scripts/dev_checks.py
```
