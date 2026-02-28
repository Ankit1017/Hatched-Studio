from __future__ import annotations

from main_app.contracts import ToolPluginSpec


def build_${tool_key}_plugin_spec() -> ToolPluginSpec:
    return {
        "plugin_key": "${tool_key}",
        "intent": "${intent}",
        "title": "${title}",
        "description": "${description}",
        "capabilities": [${capabilities}],
        "schema_ref": {
            "intent": "${intent}",
            "version": "v1",
            "id": "${schema_id}",
        },
        "execution_spec": {
            "intent": "${intent}",
            "tool_key": "${tool_key}",
            "stage_profile": "${stage_profile}",
            "requirements_schema_key": "${intent}",
            "verify_profile": "${verify_profile}",
            "verify_required": True,
            "execution_policy": {
                "timeout_ms": None,
                "max_retries": 1,
                "retry_backoff_ms": [0],
                "fail_policy": "continue",
                "concurrency_group": None,
                "profile": "${policy_profile}",
            },
            "dependency": {
                "requires_artifacts": [${depends_on}],
                "produces_artifacts": [${produces}],
                "optional_requires": [],
            },
        },
    }
