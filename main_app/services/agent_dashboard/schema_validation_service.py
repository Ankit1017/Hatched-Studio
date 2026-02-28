from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

from main_app.services.agent_dashboard.error_codes import E_SCHEMA_VALIDATION_FAILED
from main_app.services.agent_dashboard.runtime_config import schema_validate_enforce


class SchemaValidationIssue(TypedDict, total=False):
    code: str
    severity: str
    message: str
    path: str


class ValidationSummary(TypedDict, total=False):
    status: str
    schema_id: str
    checks_run: list[str]
    issues: list[SchemaValidationIssue]
    enforce: bool


def validate_artifact(*, intent: str, artifact: dict[str, Any] | None, schema_ref: dict[str, str] | None = None) -> ValidationSummary:
    normalized_intent = " ".join(str(intent).split()).strip().lower()
    checks_run: list[str] = []
    issues: list[SchemaValidationIssue] = []
    enforce = schema_validate_enforce()

    schema = _load_schema(intent=normalized_intent, schema_ref=schema_ref)
    schema_id = str(schema.get("id", f"{normalized_intent}.v1")) if isinstance(schema, dict) else f"{normalized_intent}.v1"
    if not isinstance(artifact, dict):
        issues.append(_issue("Artifact envelope is missing or invalid.", "artifact"))
        return _build_summary(schema_id=schema_id, checks_run=checks_run, issues=issues, enforce=enforce)

    checks_run.append("sections_present")
    sections = artifact.get("sections")
    if not isinstance(sections, list):
        issues.append(_issue("Artifact sections must be a list.", "artifact.sections"))
        return _build_summary(schema_id=schema_id, checks_run=checks_run, issues=issues, enforce=enforce)

    required_key = str(schema.get("required_section_key", "")).strip() if isinstance(schema, dict) else ""
    required_type = str(schema.get("required_data_type", "")).strip().lower() if isinstance(schema, dict) else ""
    if not required_key:
        return _build_summary(schema_id=schema_id, checks_run=checks_run, issues=issues, enforce=enforce)

    checks_run.append("required_section_present")
    target_section = None
    for section in sections:
        if not isinstance(section, dict):
            continue
        if " ".join(str(section.get("key", "")).split()).strip() == required_key:
            target_section = section
            break
    if target_section is None:
        issues.append(_issue(f"Required section `{required_key}` missing.", f"artifact.sections.{required_key}"))
        return _build_summary(schema_id=schema_id, checks_run=checks_run, issues=issues, enforce=enforce)

    checks_run.append("required_data_type")
    data = target_section.get("data")
    if required_type == "string" and not isinstance(data, str):
        issues.append(_issue("Section data must be string.", f"artifact.sections.{required_key}.data"))
    elif required_type == "object" and not isinstance(data, dict):
        issues.append(_issue("Section data must be object.", f"artifact.sections.{required_key}.data"))

    return _build_summary(schema_id=schema_id, checks_run=checks_run, issues=issues, enforce=enforce)


def schema_validation_passed(summary: ValidationSummary) -> bool:
    return " ".join(str(summary.get("status", "")).split()).strip().lower() == "passed"


def schema_validation_error_message(summary: ValidationSummary) -> str:
    issues = summary.get("issues", [])
    if not isinstance(issues, list) or not issues:
        return "Schema validation failed."
    messages = [str(issue.get("message", "")).strip() for issue in issues if isinstance(issue, dict)]
    if not messages:
        return "Schema validation failed."
    return "Schema validation failed: " + "; ".join(messages[:3])


def _build_summary(
    *,
    schema_id: str,
    checks_run: list[str],
    issues: list[SchemaValidationIssue],
    enforce: bool,
) -> ValidationSummary:
    has_error = any(str(issue.get("severity", "")).strip().lower() == "error" for issue in issues if isinstance(issue, dict))
    if has_error and enforce:
        status = "failed"
    else:
        status = "passed"
    return {
        "status": status,
        "schema_id": schema_id,
        "checks_run": checks_run,
        "issues": issues,
        "enforce": enforce,
    }


def _issue(message: str, path: str) -> SchemaValidationIssue:
    return {
        "code": E_SCHEMA_VALIDATION_FAILED,
        "severity": "error",
        "message": message,
        "path": path,
    }


def _load_schema(*, intent: str, schema_ref: dict[str, str] | None) -> dict[str, Any]:
    version = "v1"
    if isinstance(schema_ref, dict):
        raw_version = " ".join(str(schema_ref.get("version", "v1")).split()).strip().lower()
        if raw_version:
            version = raw_version
    repo_root = Path(__file__).resolve().parents[2]
    for path in _schema_candidate_paths(root=repo_root, intent=intent, version=version):
        if not path.exists():
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(loaded, dict):
            return loaded
    return {}


def _schema_candidate_paths(*, root: Path, intent: str, version: str) -> list[Path]:
    normalized = intent.replace(" ", "_")
    return [
        root / "domains" / normalized / "schema" / f"{normalized}.{version}.json",
        root / "schemas" / "assets" / f"{intent}.{version}.json",
        root / "schemas" / "assets" / f"{normalized}.{version}.json",
    ]
