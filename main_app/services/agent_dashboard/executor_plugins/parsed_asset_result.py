from __future__ import annotations

from main_app.contracts import IntentPayload
from main_app.models import AgentAssetResult
from main_app.services.agent_dashboard.artifact_adapter import legacy_result_to_artifact
from main_app.services.agent_dashboard.error_codes import E_EXECUTOR_FAILED, E_PARSE_FAILED


def build_error_asset_result(
    *,
    intent: str,
    payload: IntentPayload,
    error: str,
    raw_text: str = "",
    error_code: str = E_EXECUTOR_FAILED,
) -> AgentAssetResult:
    return build_artifact_result(
        intent=intent,
        payload=payload,
        status="error",
        title=intent.title(),
        error=error,
        raw_text=raw_text,
        error_code=error_code,
    )


def build_content_asset_result(
    *,
    intent: str,
    payload: IntentPayload,
    topic: str,
    title_prefix: str,
    content: object,
    cache_hit: bool = False,
    parse_note: str | None = None,
) -> AgentAssetResult:
    return build_artifact_result(
        intent=intent,
        payload=payload,
        status="success",
        title=f"{title_prefix}: {topic}",
        content=content,
        cache_hit=cache_hit,
        parse_note=(parse_note or "").strip(),
    )


def build_media_asset_result(
    *,
    intent: str,
    payload: IntentPayload,
    topic: str,
    title_prefix: str,
    content: object,
    audio_bytes: bytes | None,
    audio_error: str | None,
    cache_hit: bool = False,
    parse_note: str | None = None,
) -> AgentAssetResult:
    return build_artifact_result(
        intent=intent,
        payload=payload,
        status="success",
        title=f"{title_prefix}: {topic}",
        content=content,
        cache_hit=cache_hit,
        audio_bytes=audio_bytes,
        audio_error=audio_error or "",
        parse_note=(parse_note or "").strip(),
    )


def build_artifact_result(
    *,
    intent: str,
    payload: IntentPayload,
    status: str,
    title: str,
    content: object | None = None,
    error: str = "",
    raw_text: str = "",
    cache_hit: bool = False,
    parse_note: str = "",
    audio_bytes: bytes | None = None,
    audio_error: str = "",
    error_code: str = "",
) -> AgentAssetResult:
    result = AgentAssetResult(
        intent=intent,
        status=status,
        payload=payload,
        title=title,
        content=content,
        error=error,
        raw_text=raw_text,
        cache_hit=cache_hit,
        parse_note=parse_note,
        audio_bytes=audio_bytes,
        audio_error=audio_error,
    )
    result.artifact = legacy_result_to_artifact(result)
    artifact = result.artifact if isinstance(result.artifact, dict) else {}
    provenance = artifact.get("provenance") if isinstance(artifact.get("provenance"), dict) else {}
    if error_code:
        provenance["error_code"] = error_code
    if status == "error" and not error_code:
        provenance["error_code"] = E_EXECUTOR_FAILED
    artifact["provenance"] = provenance
    metrics = artifact.get("metrics") if isinstance(artifact.get("metrics"), dict) else {}
    metrics["cache_hit"] = bool(cache_hit)
    artifact["metrics"] = metrics
    result.artifact = artifact
    return result


def build_parsed_asset_result(
    *,
    intent: str,
    payload: IntentPayload,
    topic: str,
    title_prefix: str,
    parsed_content: object,
    parse_error: str | None,
    raw_text: str,
    parse_note: str | None,
    cache_hit: bool = False,
    failure_message: str,
) -> AgentAssetResult:
    if parse_error or parsed_content is None:
        return build_error_asset_result(
            intent=intent,
            payload=payload,
            error=parse_error or failure_message,
            raw_text=raw_text,
            error_code=E_PARSE_FAILED,
        )

    return build_content_asset_result(
        intent=intent,
        payload=payload,
        topic=topic,
        title_prefix=title_prefix,
        content=parsed_content,
        cache_hit=cache_hit,
        parse_note=parse_note,
    )
