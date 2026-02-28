from __future__ import annotations

import argparse
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

from main_app.services.agent_dashboard.error_codes import E_SCAFFOLD_TEMPLATE_MISSING
from main_app.services.agent_dashboard.plugin_sdk import default_capabilities_for_intent


def _load_template(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"[{E_SCAFFOLD_TEMPLATE_MISSING}] Missing template: {path}")
    return path.read_text(encoding="utf-8")


def _render(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("${" + key + "}", value)
    return rendered


def _quoted_csv(values: list[str]) -> str:
    return ", ".join(f'"{item}"' for item in values)


def _parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold tool plugin + schema + test + optional renderer.")
    parser.add_argument("--intent", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--description", default="")
    parser.add_argument("--kind", choices=["text", "structured", "media"], default="structured")
    parser.add_argument("--depends-on", default="")
    parser.add_argument("--produces", default="")
    parser.add_argument("--with-renderer", default="false")
    parser.add_argument("--with-workflow-key", default="")
    args = parser.parse_args()

    intent = " ".join(str(args.intent).split()).strip().lower()
    if not intent:
        raise SystemExit("intent is required")
    tool_key = intent.replace(" ", "_")
    title = args.title.strip() or intent.title()
    description = args.description.strip() or f"{title} plugin."
    schema_id = f"{tool_key}.v1"

    depends_on = _parse_csv(args.depends_on)
    produces = _parse_csv(args.produces)
    if not produces:
        produces = [f"artifact.{tool_key}.primary"]

    kind = str(args.kind).strip().lower()
    if kind == "text":
        verify_profile = "text_asset_verify"
        policy_profile = "text_policy_gate"
        required_data_type = "string"
        stage_profile = "default_asset_profile"
    elif kind == "media":
        verify_profile = "media_asset_verify"
        policy_profile = "media_policy_gate"
        required_data_type = "object"
        stage_profile = "media_asset_profile"
    else:
        verify_profile = "structured_asset_verify"
        policy_profile = "structured_policy_gate"
        required_data_type = "object"
        stage_profile = "default_asset_profile"

    required_section_key = produces[0]
    capabilities = default_capabilities_for_intent(intent)

    template_dir = Path("scripts/templates")
    plugin_tpl = _load_template(template_dir / "tool_plugin.py.tpl")
    schema_tpl = _load_template(template_dir / "schema.json.tpl")
    test_tpl = _load_template(template_dir / "test_plugin.py.tpl")
    renderer_tpl = _load_template(template_dir / "renderer_plugin.py.tpl")

    values = {
        "tool_key": tool_key,
        "intent": intent,
        "title": title,
        "description": description,
        "schema_id": schema_id,
        "capabilities": _quoted_csv(capabilities),
        "stage_profile": stage_profile,
        "verify_profile": verify_profile,
        "policy_profile": policy_profile,
        "depends_on": _quoted_csv(depends_on),
        "produces": _quoted_csv(produces),
        "required_section_key": required_section_key,
        "required_data_type": required_data_type,
        "class_name": tool_key.title().replace("_", ""),
    }

    plugin_path = Path("main_app/services/agent_dashboard/executor_plugins") / f"{tool_key}_plugin.py"
    schema_path = Path("main_app/schemas/assets") / f"{tool_key}.v1.json"
    test_path = Path("tests") / f"test_{tool_key}_plugin.py"
    renderer_path = Path("main_app/ui/agent_dashboard/renderer_plugins") / f"{tool_key}.py"

    plugin_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.parent.mkdir(parents=True, exist_ok=True)

    plugin_code = _render(plugin_tpl, values)
    plugin_code += "\n\n# TODO: wire executor registration and intent catalog aliases if needed.\n"
    plugin_path.write_text(plugin_code, encoding="utf-8")
    schema_path.write_text(_render(schema_tpl, values), encoding="utf-8")
    test_path.write_text(_render(test_tpl, values), encoding="utf-8")

    with_renderer = " ".join(str(args.with_renderer).split()).strip().lower() in {"1", "true", "yes", "on"}
    if with_renderer:
        renderer_path.parent.mkdir(parents=True, exist_ok=True)
        renderer_path.write_text(_render(renderer_tpl, values), encoding="utf-8")
        print(f"Created: {renderer_path}")

    workflow_key = " ".join(str(args.with_workflow_key).split()).strip()
    if workflow_key:
        print(f"Note: add `{tool_key}` to workflow `{workflow_key}` in workflow registry plugin specs.")

    print(f"Created: {plugin_path}")
    print(f"Created: {schema_path}")
    print(f"Created: {test_path}")


if __name__ == "__main__":
    main()
