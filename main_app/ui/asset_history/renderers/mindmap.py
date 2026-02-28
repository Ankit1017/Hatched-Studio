from __future__ import annotations

import re

import streamlit as st

from main_app.mindmap.graph_utils import (
    build_mind_map_dot,
    clone_subtree_for_layers,
    collect_mind_map_nodes,
    localize_selected_path,
    render_dot_as_png,
    visible_nodes_for_focus,
)
from main_app.models import AssetHistoryRecord
from main_app.ui.asset_history.context import AssetHistoryRenderContext


def render_mindmap_record(record: AssetHistoryRecord, context: AssetHistoryRenderContext) -> None:
    tree = record.result_payload if isinstance(record.result_payload, dict) else {}
    if not tree or not str(tree.get("name", "")).strip():
        st.json(record.result_payload)
        return

    scope = f"asset_history_mindmap_{record.id}"
    selected_path_key = f"{scope}_selected_path"
    focus_path_key = f"{scope}_focus_path"
    view_mode_key = f"{scope}_view_mode"
    direction_key = f"{scope}_direction"
    last_explained_path_key = f"{scope}_last_explained_path"
    last_explanation_key = f"{scope}_last_explanation"

    nodes_flat = collect_mind_map_nodes(tree)
    nodes_by_path = {node["path"]: node for node in nodes_flat}
    root_path = nodes_flat[0]["path"] if nodes_flat else ""
    if not root_path:
        st.json(record.result_payload)
        return

    if st.session_state.get(selected_path_key) not in nodes_by_path:
        st.session_state[selected_path_key] = root_path
    if st.session_state.get(focus_path_key) not in nodes_by_path:
        st.session_state[focus_path_key] = root_path
    if st.session_state.get(view_mode_key) not in {"Full Graph", "Layer by Layer (2 Levels)"}:
        st.session_state[view_mode_key] = "Full Graph"
    if st.session_state.get(direction_key) not in {"LR", "TB"}:
        st.session_state[direction_key] = "TB"

    st.subheader(f"Mind Map: {record.topic or tree.get('name', 'Topic')}")
    st.caption("Use Full Graph for complete overview, or Layer by Layer to drill down 2 levels at a time.")

    total_nodes = len(nodes_flat)
    leaf_nodes = sum(1 for node in nodes_flat if node["is_leaf"])
    max_actual_depth = max((node["depth"] for node in nodes_flat), default=0) + 1
    stat_col_1, stat_col_2, stat_col_3 = st.columns(3)
    stat_col_1.metric("Total Nodes", total_nodes)
    stat_col_2.metric("Leaf Nodes", leaf_nodes)
    stat_col_3.metric("Depth Reached", max_actual_depth)

    map_col, control_col = st.columns([0.72, 0.28], gap="large")
    explain_path: str | None = None
    dot_source = ""
    with control_col:
        st.markdown("#### Node Explorer")
        st.session_state[view_mode_key] = st.radio(
            "View Mode",
            options=["Full Graph", "Layer by Layer (2 Levels)"],
            index=0 if st.session_state[view_mode_key] == "Full Graph" else 1,
            key=f"{scope}_view_mode_radio",
        )

        direction_label = st.selectbox(
            "Graph Layout",
            options=["Left to Right", "Top to Bottom"],
            index=0 if st.session_state[direction_key] == "LR" else 1,
            key=f"{scope}_graph_layout",
        )
        st.session_state[direction_key] = "LR" if direction_label == "Left to Right" else "TB"

        if st.session_state[view_mode_key] == "Full Graph":
            node_paths = [node["path"] for node in nodes_flat]
            selected_index = node_paths.index(st.session_state[selected_path_key]) if st.session_state[selected_path_key] in node_paths else 0
            selected_path = st.selectbox(
                "Select Node",
                options=node_paths,
                index=selected_index,
                help="Choose any node path from the graph to explain.",
                key=f"{scope}_full_selected_path",
            )
            st.session_state[selected_path_key] = selected_path
            if st.button("Explain Selected Node", key=f"{scope}_explain_selected", type="primary", width="stretch"):
                explain_path = selected_path
        else:
            focus_path = st.session_state[focus_path_key]
            focus_node_info = nodes_by_path.get(focus_path)
            focus_parent_path = focus_node_info["parent_path"] if focus_node_info else None

            nav_col_1, nav_col_2 = st.columns(2)
            if nav_col_1.button("Root", key=f"{scope}_layer_root", width="stretch"):
                st.session_state[focus_path_key] = root_path
                st.session_state[selected_path_key] = root_path
                st.rerun()
            if nav_col_2.button(
                "Up",
                key=f"{scope}_layer_up",
                width="stretch",
                disabled=focus_parent_path is None,
            ):
                st.session_state[focus_path_key] = focus_parent_path
                st.session_state[selected_path_key] = focus_parent_path
                st.rerun()

            st.caption(f"Current focus: {st.session_state[focus_path_key]}")
            st.caption("Click a node button to dive into its subtopics. `Mind` explains that node.")

    with map_col:
        if st.session_state[view_mode_key] == "Full Graph":
            dot = build_mind_map_dot(
                tree,
                selected_path=st.session_state[selected_path_key],
                direction=st.session_state[direction_key],
            )
            dot_source = dot
            try:
                st.graphviz_chart(dot, width="stretch")
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Graph render fallback: {exc}")
                st.code(dot)
        else:
            focus_path = st.session_state[focus_path_key]
            focus_node_info = nodes_by_path.get(focus_path)
            if focus_node_info:
                layer_subtree = clone_subtree_for_layers(focus_node_info["node_ref"], remaining_layers=2)
                local_selected = localize_selected_path(st.session_state[selected_path_key], focus_path)
                dot = build_mind_map_dot(
                    layer_subtree,
                    selected_path=local_selected,
                    direction=st.session_state[direction_key],
                )
                dot_source = dot
                try:
                    st.graphviz_chart(dot, width="stretch")
                except Exception as exc:  # noqa: BLE001
                    st.warning(f"Graph render fallback: {exc}")
                    st.code(dot)

                visible_nodes = visible_nodes_for_focus(nodes_flat, focus_path=focus_path, max_relative_layers=2)
                st.markdown("#### Layer Node Actions")
                action_cols = st.columns(2)
                for idx, node in enumerate(visible_nodes):
                    node_key = re.sub(r"[^a-zA-Z0-9_]+", "_", node["path"])[:42]
                    target_col = action_cols[idx % 2]
                    with target_col:
                        with st.container(border=True):
                            node_button_cols = st.columns([0.72, 0.28])
                            if node_button_cols[0].button(node["name"], key=f"{scope}_open_{node_key}", width="stretch"):
                                st.session_state[focus_path_key] = node["path"]
                                st.session_state[selected_path_key] = node["path"]
                                st.rerun()
                            if node_button_cols[1].button("Mind", key=f"{scope}_mind_{node_key}", width="stretch"):
                                st.session_state[selected_path_key] = node["path"]
                                explain_path = node["path"]
                            st.caption(node["path"])

    if dot_source:
        safe_topic = re.sub(r"[^a-zA-Z0-9_-]+", "_", (record.topic or str(tree.get("name", "mind_map"))).strip())[:60].strip("_")
        safe_topic = safe_topic or "mind_map"
        mode_tag = "full" if st.session_state[view_mode_key] == "Full Graph" else "layer"
        png_bytes, png_error = render_dot_as_png(dot_source)
        _, export_col = st.columns([0.72, 0.28], gap="large")
        with export_col:
            if png_bytes is not None:
                st.download_button(
                    "Download Mind Map (PNG)",
                    data=png_bytes,
                    file_name=f"{safe_topic}_{mode_tag}.png",
                    mime="image/png",
                    key=f"{scope}_download_png",
                    width="stretch",
                )
            else:
                st.button(
                    "Download Mind Map (PNG)",
                    key=f"{scope}_download_png_disabled",
                    disabled=True,
                    width="stretch",
                )
                if png_error:
                    st.caption(png_error)

    if explain_path:
        if not context.settings.has_api_key():
            st.error("Please enter your Groq API key in the sidebar to explain a node.")
        elif not context.settings.has_model():
            st.error("Please select or enter a valid model in the sidebar.")
        else:
            try:
                with st.spinner(f"Explaining: {explain_path}"):
                    explanation_text, cache_hit = context.agent_dashboard_service.explain_mindmap_node(
                        root_topic=record.topic or str(tree.get("name", "")).strip(),
                        node_path=explain_path,
                        settings=context.settings,
                    )
                st.session_state[last_explained_path_key] = explain_path
                st.session_state[last_explanation_key] = explanation_text
                if cache_hit:
                    st.info("Explanation served from cache.")
                else:
                    context.cache_count_placeholder.caption(f"Cached responses: {context.llm_service.count}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Request failed: {exc}")

    last_explanation = str(st.session_state.get(last_explanation_key, "")).strip()
    if last_explanation:
        st.markdown("---")
        st.subheader(f"Explanation: {st.session_state.get(last_explained_path_key, '')}")
        st.markdown(last_explanation)
