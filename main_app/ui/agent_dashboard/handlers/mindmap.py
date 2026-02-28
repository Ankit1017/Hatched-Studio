from __future__ import annotations

from html import escape

import streamlit as st

from main_app.contracts import IntentPayload
from main_app.mindmap.graph_utils import build_mind_map_dot, collect_mind_map_nodes, render_dot_as_png
from main_app.ui.agent_dashboard.context import AgentAssetRenderContext
from main_app.ui.agent_dashboard.handlers.types import AgentAsset


def render_mindmap_asset(
    context: AgentAssetRenderContext,
    scope: str,
    payload: IntentPayload,
    content: object,
    asset: AgentAsset,
) -> None:
    del asset
    tree = content if isinstance(content, dict) else {}
    if not tree or not str(tree.get("name", "")).strip():
        st.json(content)
        return

    nodes_flat = collect_mind_map_nodes(tree)
    if not nodes_flat:
        st.json(content)
        return

    node_paths = [node["path"] for node in nodes_flat]
    selected_key = f"agent_dashboard_mindmap_selected_{scope}"
    explained_path_key = f"agent_dashboard_mindmap_explained_path_{scope}"
    explanation_key = f"agent_dashboard_mindmap_explanation_{scope}"

    selected_value = st.session_state.get(selected_key, "")
    if selected_value not in node_paths:
        st.session_state[selected_key] = node_paths[0]

    map_col, control_col = st.columns([0.72, 0.28], gap="large")
    explain_clicked = False
    dot_source = ""
    with control_col:
        st.markdown("#### Node Explorer")
        st.selectbox(
            "Select Node",
            options=node_paths,
            key=selected_key,
            help="Pick any node path and click explain.",
        )
        explain_clicked = st.button(
            "Explain Selected Node",
            key=f"agent_dashboard_mindmap_explain_btn_{scope}",
            type="primary",
            width="stretch",
        )

    with map_col:
        dot = build_mind_map_dot(
            tree,
            selected_path=str(st.session_state.get(selected_key, node_paths[0])),
            direction="LR",
        )
        dot_source = dot
        st.graphviz_chart(dot, width="stretch")

    if dot_source:
        safe_topic = " ".join(str(payload.get("topic", tree.get("name", "mind_map"))).split())
        safe_topic = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in safe_topic)[:60].strip("_") or "mind_map"
        png_bytes, png_error = render_dot_as_png(dot_source)
        _, download_col = st.columns([0.72, 0.28], gap="large")
        with download_col:
            if png_bytes is not None:
                st.download_button(
                    "Download Mind Map (PNG)",
                    data=png_bytes,
                    file_name=f"{safe_topic}.png",
                    mime="image/png",
                    key=f"agent_dashboard_mindmap_png_download_{scope}",
                    width="stretch",
                )
            else:
                st.button(
                    "Download Mind Map (PNG)",
                    key=f"agent_dashboard_mindmap_png_download_disabled_{scope}",
                    disabled=True,
                    width="stretch",
                )
                if png_error:
                    st.caption(png_error)

    if explain_clicked:
        if not context.settings.has_api_key():
            st.error("Please enter your Groq API key in the sidebar.")
        elif not context.settings.has_model():
            st.error("Please select or enter a valid model.")
        else:
            selected_path = str(st.session_state.get(selected_key, node_paths[0]))
            root_topic = str(payload.get("topic", "")).strip() or str(tree.get("name", "")).strip()
            with st.spinner(f"Explaining: {selected_path}"):
                explanation_text, cache_hit = context.agent_dashboard_service.explain_mindmap_node(
                    root_topic=root_topic,
                    node_path=selected_path,
                    settings=context.settings,
                )
            st.session_state[explained_path_key] = selected_path
            st.session_state[explanation_key] = explanation_text
            if cache_hit:
                st.info("Explanation served from cache.")
            else:
                context.cache_count_placeholder.caption(f"Cached responses: {context.llm_service.count}")

    explanation_text = str(st.session_state.get(explanation_key, "")).strip()
    if explanation_text:
        explained_path = str(st.session_state.get(explained_path_key, "")).strip()
        st.markdown("---")
        st.markdown(f"**Node Explanation:** `{escape(explained_path)}`")
        st.markdown(explanation_text)
