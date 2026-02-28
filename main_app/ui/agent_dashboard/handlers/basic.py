from __future__ import annotations

from main_app.contracts import IntentPayload
from main_app.domains.topic.renderer.topic_render_model import extract_topic_markdown
from main_app.parsers.markdown_utils import normalize_markdown_text
from main_app.ui.agent_dashboard.context import AgentAssetRenderContext
from main_app.ui.agent_dashboard.handlers.types import AgentAsset
from main_app.ui.components import ReportRenderConfig, render_report_view

import streamlit as st


def render_generic_artifact_sections(asset: AgentAsset) -> bool:
    artifact = asset.get("artifact")
    if not isinstance(artifact, dict):
        return False
    provenance = artifact.get("provenance")
    if isinstance(provenance, dict):
        verification = provenance.get("verification")
        if isinstance(verification, dict):
            verify_status = " ".join(str(verification.get("status", "")).split()).strip().lower()
            if verify_status:
                if verify_status == "passed":
                    st.success("Verification: passed")
                else:
                    st.error("Verification: failed")
            issues = verification.get("issues")
            if isinstance(issues, list) and issues:
                st.caption("Verification issues")
                st.table(
                    [
                        {
                            "code": str(issue.get("code", "")),
                            "severity": str(issue.get("severity", "")),
                            "path": str(issue.get("path", "")),
                            "message": str(issue.get("message", "")),
                        }
                        for issue in issues
                        if isinstance(issue, dict)
                    ]
                )
    sections = artifact.get("sections")
    if not isinstance(sections, list) or not sections:
        return False
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_title = " ".join(str(section.get("title", "")).split()).strip() or "Section"
        st.markdown(f"**{section_title}**")
        data = section.get("data")
        if isinstance(data, (dict, list)):
            st.json(data)
        else:
            st.write(data)
    return True


def render_topic_asset(
    context: AgentAssetRenderContext,
    scope: str,
    payload: IntentPayload,
    content: object,
    asset: AgentAsset,
) -> None:
    del context, scope, payload
    topic_markdown = extract_topic_markdown(
        content=content,
        artifact=asset.get("artifact") if isinstance(asset.get("artifact"), dict) else None,
    )
    st.markdown(topic_markdown)


def render_report_asset(
    context: AgentAssetRenderContext,
    scope: str,
    payload: IntentPayload,
    content: object,
    asset: AgentAsset,
) -> None:
    del asset
    topic = str(payload.get("topic", "")).strip() or "Report"
    format_title = str(payload.get("format_title", "")).strip()
    if not format_title:
        format_key = str(payload.get("format_key", "")).strip().replace("_", " ")
        format_title = format_key.title() if format_key else "Report"
    render_report_view(
        topic=topic,
        format_title=format_title,
        markdown_content=normalize_markdown_text(str(content)),
        config=ReportRenderConfig(
            template_select_key=f"agent_dashboard_report_template_{scope}",
            download_md_key=f"agent_dashboard_report_download_md_{scope}",
            download_pdf_key=f"agent_dashboard_report_download_pdf_{scope}",
            download_pdf_disabled_key=f"agent_dashboard_report_download_pdf_disabled_{scope}",
        ),
        report_exporter=context.report_exporter,
    )


def render_data_table_asset(
    context: AgentAssetRenderContext,
    scope: str,
    payload: IntentPayload,
    content: object,
    asset: AgentAsset,
) -> None:
    del context, scope, payload, asset
    import pandas as pd

    columns = (content or {}).get("columns", []) if isinstance(content, dict) else []
    rows = (content or {}).get("rows", []) if isinstance(content, dict) else []
    if rows:
        dataframe = pd.DataFrame(rows)
        if columns:
            dataframe = dataframe.reindex(columns=columns)
        st.dataframe(dataframe, width="stretch")
    else:
        st.json(content)


def render_audio_overview_asset(
    context: AgentAssetRenderContext,
    scope: str,
    payload: IntentPayload,
    content: object,
    asset: AgentAsset,
) -> None:
    del context, scope, payload
    overview = content if isinstance(content, dict) else {}
    speakers = overview.get("speakers", [])
    dialogue = overview.get("dialogue", [])
    st.caption(f"Speakers: {len(speakers)} | Turns: {len(dialogue)}")
    summary = str(overview.get("summary", "")).strip()
    if summary:
        st.write(summary)
    audio_bytes = asset.get("audio_bytes")
    audio_error = str(asset.get("audio_error", "")).strip()
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3")
    elif audio_error:
        st.warning(audio_error)
    with st.expander("Show audio overview JSON", expanded=False):
        st.json(overview)


def render_unknown_asset(
    context: AgentAssetRenderContext,
    scope: str,
    payload: IntentPayload,
    content: object,
    asset: AgentAsset,
) -> None:
    del context, scope, payload
    if render_generic_artifact_sections(asset):
        return
    st.json(content)
