from __future__ import annotations

from typing import Any, TypedDict

from main_app.models import AgentAssetResult
from main_app.services.agent_dashboard.artifact_adapter import (
    ARTIFACT_AUDIO_OVERVIEW_PAYLOAD,
    ARTIFACT_REPORT_TEXT,
    ARTIFACT_TOPIC_TEXT,
    ARTIFACT_VIDEO_PAYLOAD,
    legacy_result_to_artifact,
)
from main_app.services.agent_dashboard.error_codes import (
    E_POLICY_GATE_FAILED,
    E_POLICY_PROFILE_UNKNOWN,
)
from main_app.services.agent_dashboard.runtime_config import policy_gate_mode
from main_app.services.agent_dashboard.tool_registry import AgentToolDefinition


TEXT_POLICY_PROFILE = "text_policy_gate"
STRUCTURED_POLICY_PROFILE = "structured_policy_gate"
MEDIA_POLICY_PROFILE = "media_policy_gate"


class PolicyIssue(TypedDict, total=False):
    code: str
    severity: str
    message: str
    path: str
    rule_id: str


class PolicyGateSummary(TypedDict, total=False):
    status: str
    profile: str
    checks_run: list[str]
    issues: list[PolicyIssue]


def evaluate_policy_gate(*, result: AgentAssetResult, tool: AgentToolDefinition) -> PolicyGateSummary:
    profile, fallback_issue = _policy_profile(tool)
    if profile == TEXT_POLICY_PROFILE:
        summary = _check_text_policy(result=result, tool=tool)
    elif profile == MEDIA_POLICY_PROFILE:
        summary = _check_media_policy(result=result, tool=tool)
    else:
        summary = _check_structured_policy(result=result, tool=tool)

    issues = summary.get("issues", []) if isinstance(summary.get("issues"), list) else []
    checks_run = summary.get("checks_run", []) if isinstance(summary.get("checks_run"), list) else []
    if fallback_issue is not None:
        issues.append(fallback_issue)
        checks_run.append("policy_profile_fallback")

    strict = policy_gate_mode() == "strict"
    has_errors = any(
        isinstance(issue, dict) and str(issue.get("severity", "")).strip().lower() == "error"
        for issue in issues
    )
    summary["issues"] = issues
    summary["checks_run"] = checks_run
    summary["profile"] = profile
    summary["status"] = "failed" if strict and has_errors else "passed"
    return summary


def policy_gate_passed(summary: PolicyGateSummary) -> bool:
    return " ".join(str(summary.get("status", "")).split()).strip().lower() == "passed"


def policy_gate_error_message(summary: PolicyGateSummary) -> str:
    issues = summary.get("issues", [])
    if not isinstance(issues, list):
        return "Policy gate failed."
    messages = [
        str(issue.get("message", "")).strip()
        for issue in issues
        if isinstance(issue, dict) and str(issue.get("severity", "")).strip().lower() == "error"
    ]
    if not messages:
        return "Policy gate failed."
    return "Policy gate failed: " + "; ".join(messages[:3])


def _check_text_policy(*, result: AgentAssetResult, tool: AgentToolDefinition) -> PolicyGateSummary:
    del tool
    checks_run: list[str] = []
    issues: list[PolicyIssue] = []
    key = ARTIFACT_TOPIC_TEXT if result.intent == "topic" else ARTIFACT_REPORT_TEXT
    text = _section_data(result=result, section_key=key)
    checks_run.append("text_exists")
    if not isinstance(text, str) or not text.strip():
        issues.append(_error_issue("Text content is empty.", f"sections.{key}.data", "text_not_empty"))
    checks_run.append("text_reference_marker_policy")
    if isinstance(text, str) and ("[S1]" in text or "[S2]" in text or "[S3]" in text):
        issues.append(
            _warning_issue(
                "Reference markers detected in text. Consider disabling references when not requested.",
                f"sections.{key}.data",
                "no_unrequested_reference_markers",
            )
        )
    return {"status": "passed", "profile": TEXT_POLICY_PROFILE, "checks_run": checks_run, "issues": issues}


def _check_structured_policy(*, result: AgentAssetResult, tool: AgentToolDefinition) -> PolicyGateSummary:
    del tool
    checks_run: list[str] = ["structured_section_exists"]
    issues: list[PolicyIssue] = []
    artifact = result.artifact if isinstance(result.artifact, dict) else legacy_result_to_artifact(result)
    sections = artifact.get("sections", [])
    if not isinstance(sections, list) or not sections:
        issues.append(_error_issue("Structured artifact has no sections.", "sections", "has_sections"))
    return {"status": "passed", "profile": STRUCTURED_POLICY_PROFILE, "checks_run": checks_run, "issues": issues}


def _check_media_policy(*, result: AgentAssetResult, tool: AgentToolDefinition) -> PolicyGateSummary:
    del tool
    checks_run: list[str] = []
    issues: list[PolicyIssue] = []
    payload_key = ARTIFACT_VIDEO_PAYLOAD if result.intent == "video" else ARTIFACT_AUDIO_OVERVIEW_PAYLOAD
    payload = _section_data(result=result, section_key=payload_key)
    checks_run.append("media_payload_exists")
    if not isinstance(payload, dict):
        issues.append(_error_issue("Media payload is missing.", f"sections.{payload_key}.data", "media_payload_exists"))
    checks_run.append("audio_error_propagation")
    if result.audio_error and result.status == "success":
        issues.append(
            _error_issue(
                "Audio error must not be hidden on success status.",
                "audio_error",
                "audio_error_consistency",
            )
        )
    return {"status": "passed", "profile": MEDIA_POLICY_PROFILE, "checks_run": checks_run, "issues": issues}


def _policy_profile(tool: AgentToolDefinition) -> tuple[str, PolicyIssue | None]:
    spec = tool.execution_spec if isinstance(tool.execution_spec, dict) else {}
    raw_profile = ""
    if isinstance(spec.get("execution_policy"), dict):
        raw_profile = " ".join(str(spec["execution_policy"].get("profile", "")).split()).strip().lower()
    if raw_profile in {TEXT_POLICY_PROFILE, STRUCTURED_POLICY_PROFILE, MEDIA_POLICY_PROFILE}:
        return raw_profile, None
    intent = " ".join(str(tool.intent).split()).strip().lower()
    inferred = STRUCTURED_POLICY_PROFILE
    if intent in {"topic", "report"}:
        inferred = TEXT_POLICY_PROFILE
    elif intent in {"video", "audio_overview"}:
        inferred = MEDIA_POLICY_PROFILE
    if not raw_profile:
        return inferred, None
    severity = "error" if policy_gate_mode() == "strict" else "warning"
    return inferred, {
        "code": E_POLICY_PROFILE_UNKNOWN,
        "severity": severity,
        "message": f"Unknown policy profile `{raw_profile}`. Fallback `{inferred}` was applied.",
        "path": "execution_spec.execution_policy.profile",
        "rule_id": "known_policy_profile",
    }


def _section_data(*, result: AgentAssetResult, section_key: str) -> Any:
    artifact = result.artifact if isinstance(result.artifact, dict) else legacy_result_to_artifact(result)
    sections = artifact.get("sections", [])
    if not isinstance(sections, list):
        return None
    for section in sections:
        if not isinstance(section, dict):
            continue
        key = " ".join(str(section.get("key", "")).split()).strip()
        if key == section_key:
            return section.get("data")
    return None


def _error_issue(message: str, path: str, rule_id: str) -> PolicyIssue:
    return {
        "code": E_POLICY_GATE_FAILED,
        "severity": "error",
        "message": message,
        "path": path,
        "rule_id": rule_id,
    }


def _warning_issue(message: str, path: str, rule_id: str) -> PolicyIssue:
    return {
        "code": E_POLICY_GATE_FAILED,
        "severity": "warning",
        "message": message,
        "path": path,
        "rule_id": rule_id,
    }
