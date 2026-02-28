from __future__ import annotations

from dataclasses import dataclass
import re

import streamlit as st

from main_app.parsers.markdown_utils import normalize_markdown_text
from main_app.services.report_exporter import ReportExporter


@dataclass(frozen=True)
class ReportRenderConfig:
    template_select_key: str
    download_md_key: str
    download_pdf_key: str
    download_pdf_disabled_key: str


def render_report_view(
    *,
    topic: str,
    format_title: str,
    markdown_content: str,
    config: ReportRenderConfig,
    report_exporter: ReportExporter,
) -> None:
    normalized_content = normalize_markdown_text(markdown_content)
    template_options = report_exporter.list_templates()
    if not template_options:
        template_options = [
            {
                "key": "default",
                "title": "Default",
                "description": "Default report template.",
            }
        ]

    template_keys = [str(item.get("key", "")).strip() for item in template_options if str(item.get("key", "")).strip()]
    if not template_keys:
        template_keys = ["default"]
        template_options = [
            {
                "key": "default",
                "title": "Default",
                "description": "Default report template.",
            }
        ]

    template_by_key = {str(item.get("key", "")).strip(): item for item in template_options}
    if st.session_state.get(config.template_select_key) not in template_keys and config.template_select_key in st.session_state:
        del st.session_state[config.template_select_key]
    selected_template = str(st.session_state.get(config.template_select_key, template_keys[0]))
    selected_index = template_keys.index(selected_template) if selected_template in template_keys else 0

    safe_topic = re.sub(r"[^a-zA-Z0-9_-]+", "_", topic.strip())[:60].strip("_") or "report"
    safe_format = re.sub(r"[^a-zA-Z0-9_-]+", "_", format_title.strip().lower())[:30].strip("_") or "report"
    markdown_file_name = f"{safe_topic}_{safe_format}.md"
    pdf_file_name = f"{safe_topic}_{safe_format}.pdf"

    template_col, download_md_col, download_pdf_col = st.columns([1.4, 1.0, 1.0], gap="small")
    with template_col:
        selected_template = st.selectbox(
            "Export Template",
            options=template_keys,
            index=selected_index,
            format_func=lambda value: str(template_by_key.get(value, {}).get("title", value)),
            key=config.template_select_key,
        )
        template_description = str(template_by_key.get(selected_template, {}).get("description", "")).strip()
        if template_description:
            st.caption(template_description)

    pdf_bytes, pdf_error = report_exporter.build_pdf(
        topic=topic,
        format_title=format_title,
        markdown_content=normalized_content,
        template_key=selected_template,
    )

    with download_md_col:
        st.download_button(
            "Download .md",
            data=normalized_content,
            file_name=markdown_file_name,
            mime="text/markdown",
            key=config.download_md_key,
            width="stretch",
        )
    with download_pdf_col:
        if pdf_bytes is not None:
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=pdf_file_name,
                mime="application/pdf",
                key=config.download_pdf_key,
                width="stretch",
            )
        else:
            st.button(
                "Download PDF",
                disabled=True,
                key=config.download_pdf_disabled_key,
                width="stretch",
            )
            if pdf_error:
                st.caption(pdf_error)

    with st.container(border=True):
        st.markdown(normalized_content)
