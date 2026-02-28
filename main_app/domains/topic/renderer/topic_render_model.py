from __future__ import annotations

from typing import Any


def extract_topic_markdown(
    *,
    content: object = None,
    result_payload: dict[str, Any] | None = None,
    artifact: dict[str, Any] | None = None,
) -> str:
    if isinstance(content, str):
        return content
    if content is not None:
        return str(content)

    payload = result_payload if isinstance(result_payload, dict) else {}
    payload_content = payload.get("content")
    if isinstance(payload_content, str):
        return payload_content
    if payload_content is not None:
        return str(payload_content)

    artifact_payload = artifact if isinstance(artifact, dict) else {}
    sections = artifact_payload.get("sections")
    if not isinstance(sections, list):
        return ""
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_key = " ".join(str(section.get("key", "")).split()).strip()
        if section_key != "artifact.topic.text":
            continue
        section_data = section.get("data")
        if isinstance(section_data, str):
            return section_data
        if section_data is not None:
            return str(section_data)
    return ""
