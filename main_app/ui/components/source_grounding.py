from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from main_app.services.source_grounding_service import SourceDocument, SourceGroundingService


@dataclass(frozen=True)
class SourceGroundingSelection:
    enabled: bool
    require_citations: bool
    sources: list[SourceDocument]
    grounding_context: str
    source_manifest: list[dict[str, Any]]
    warnings: list[str]


def render_source_grounding_controls(
    *,
    key_prefix: str,
    source_grounding_service: SourceGroundingService,
    heading: str = "Source-Grounded Generation",
) -> SourceGroundingSelection:
    with st.container(border=True):
        st.markdown(f"#### {heading}")
        enabled = st.checkbox(
            "Enable source-grounded mode",
            key=f"{key_prefix}_grounded_enabled",
            help="When enabled, uploaded files are used as grounding context for generation.",
        )
        if not enabled:
            return SourceGroundingSelection(
                enabled=False,
                require_citations=False,
                sources=[],
                grounding_context="",
                source_manifest=[],
                warnings=[],
            )

        require_citations = st.checkbox(
            "Require citation markers in output (e.g. [S1], [S2])",
            value=True,
            key=f"{key_prefix}_grounded_citations",
        )
        max_sources = st.slider(
            "Max sources to use",
            min_value=1,
            max_value=12,
            value=6,
            step=1,
            key=f"{key_prefix}_grounded_max_sources",
        )
        uploaded_files = st.file_uploader(
            "Upload source files",
            type=source_grounding_service.supported_upload_types,
            accept_multiple_files=True,
            key=f"{key_prefix}_grounded_files",
        )

        sources, warnings = source_grounding_service.extract_sources(
            uploaded_files or [],
            max_sources=max_sources,
        )
        grounding_context = source_grounding_service.build_grounding_context(sources)
        source_manifest = source_grounding_service.build_source_manifest(sources)

        if sources:
            st.caption(
                f"Loaded {len(sources)} source(s), total context size: {len(grounding_context)} characters."
            )
            with st.expander("Source Summary", expanded=False):
                for source in sources:
                    truncation_note = " (truncated)" if source.truncated else ""
                    st.markdown(f"- `[{source.source_id}]` {source.name} ({source.char_count} chars){truncation_note}")
        else:
            st.caption("No valid sources loaded yet.")

        for warning_text in warnings:
            st.caption(f"Note: {warning_text}")

        return SourceGroundingSelection(
            enabled=True,
            require_citations=require_citations,
            sources=sources,
            grounding_context=grounding_context,
            source_manifest=source_manifest,
            warnings=warnings,
        )
