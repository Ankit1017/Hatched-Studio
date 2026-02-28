from __future__ import annotations

from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(choices=[])))

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

from main_app.services.agent_dashboard.plugin_sdk import (
    plugin_spec_fix_hints,
    validate_tool_plugin_spec,
    validate_workflow_plugin_spec,
)
from main_app.services.agent_dashboard.tool_registry import build_default_agent_tool_registry
from main_app.services.agent_dashboard.workflow_registry import build_default_agent_workflow_registry


def _schema_path(intent: str, version: str) -> Path:
    key = " ".join(str(intent).split()).strip().lower().replace(" ", "_")
    ver = " ".join(str(version).split()).strip().lower() or "v1"
    return Path("main_app/schemas/assets") / f"{key}.{ver}.json"


def main() -> int:
    errors: list[str] = []
    registry = build_default_agent_tool_registry()
    for spec in registry.list_plugin_specs():
        result = validate_tool_plugin_spec(spec)
        if not result.ok:
            errors.append(f"Tool plugin invalid `{spec.get('plugin_key', '')}`: {result.message}")
            hints = plugin_spec_fix_hints(spec)
            for hint in hints:
                errors.append(f"  hint: {hint}")
            continue
        schema_ref = spec.get("schema_ref") if isinstance(spec.get("schema_ref"), dict) else {}
        schema_path = _schema_path(
            intent=str(schema_ref.get("intent", spec.get("intent", ""))),
            version=str(schema_ref.get("version", "v1")),
        )
        if not schema_path.exists():
            errors.append(
                f"Schema missing for `{spec.get('plugin_key', '')}`: expected `{schema_path}`"
            )

    workflow_registry = build_default_agent_workflow_registry()
    for workflow_spec in workflow_registry.list_workflow_plugin_specs():
        result = validate_workflow_plugin_spec(workflow_spec)
        if not result.ok:
            errors.append(f"Workflow plugin invalid `{workflow_spec.get('workflow_key', '')}`: {result.message}")

    if errors:
        print("Plugin/schema validation failed:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("Plugin/schema validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
