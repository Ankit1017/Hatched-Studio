from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any

import streamlit as st

from main_app.mindmap.graph_utils import (
    build_mind_map_dot,
    clone_subtree_for_layers,
    collect_mind_map_nodes,
    localize_selected_path,
    render_dot_as_png,
    visible_nodes_for_focus,
)
from main_app.models import GroqSettings
from main_app.services.cached_llm_service import CachedLLMService
from main_app.services.mind_map_service import MindMapService
from main_app.ui.error_handling import UI_HANDLED_EXCEPTIONS, report_ui_error, report_ui_warning


@dataclass(frozen=True)
class _GenerationInputs:
    topic: str
    max_depth: int
    constraints: str
    requested: bool


@dataclass(frozen=True)
class _NodeContext:
    nodes_flat: list[dict[str, Any]]
    nodes_by_path: dict[str, dict[str, Any]]
    root_path: str
    total_nodes: int
    leaf_nodes: int
    max_actual_depth: int


def _render_generation_inputs() -> _GenerationInputs:
    st.subheader("Mind Map Topic")
    topic = st.text_input(
        "Topic for Mind Map",
        placeholder="e.g. Machine Learning",
        key="mindmap_topic_input",
    )
    max_depth = st.slider(
        "Max Depth (n)",
        min_value=2,
        max_value=8,
        value=4,
        help="The model will try to expand the map as deep as possible up to this level.",
        key="mindmap_depth",
    )
    constraints = st.text_area(
        "Optional Mind Map Constraints",
        placeholder="e.g. Focus on healthcare use-cases and include regulations.",
        height=100,
        key="mindmap_constraints",
    )
    requested = st.button("Generate Mind Map", type="primary", key="generate_mindmap")
    return _GenerationInputs(
        topic=topic,
        max_depth=max_depth,
        constraints=constraints,
        requested=requested,
    )


def _handle_generation_request(
    *,
    inputs: _GenerationInputs,
    mind_map_service: MindMapService,
    llm_service: CachedLLMService,
    settings: GroqSettings,
    cache_count_placeholder: Any,
) -> None:
    if not inputs.requested:
        return

    if not settings.has_api_key():
        st.error("Please enter your Groq API key in the sidebar.")
        st.stop()
    if not settings.has_model():
        st.error("Please select or enter a valid model.")
        st.stop()
    if not inputs.topic or not inputs.topic.strip():
        st.error("Please enter a topic for the mind map.")
        st.stop()

    try:
        with st.spinner("Generating mind map from Groq..."):
            generation_result = mind_map_service.generate(
                topic=inputs.topic,
                max_depth=inputs.max_depth,
                constraints=inputs.constraints,
                settings=settings,
            )

        if generation_result.cache_hit:
            st.info("Mind map served from cache. No API call made.")
        else:
            cache_count_placeholder.caption(f"Cached responses: {llm_service.count}")

        cache_count_placeholder.caption(f"Cached responses: {llm_service.count}")
        if generation_result.parse_note:
            st.info(generation_result.parse_note)
        if generation_result.parse_error:
            st.error(generation_result.parse_error)
            st.caption("Raw model response:")
            st.code(generation_result.raw_text)
            return

        parsed_map = generation_result.parsed_map
        if not parsed_map:
            st.error("Mind map generation failed.")
            return
        root_name = parsed_map["name"]
        st.session_state.mind_map_tree = parsed_map
        st.session_state.mind_map_topic = inputs.topic.strip()
        st.session_state.mind_map_selected_path = root_name
        st.session_state.mind_map_focus_path = root_name
        st.session_state.mind_map_last_explained_path = ""
        st.session_state.mind_map_last_explanation = ""
        st.success("Mind map generated.")
    except UI_HANDLED_EXCEPTIONS as exc:
        report_ui_error(action="mindmap_generate", exc=exc)


def _build_node_context(tree: dict[str, Any]) -> _NodeContext:
    nodes_flat = collect_mind_map_nodes(tree)
    nodes_by_path = {node["path"]: node for node in nodes_flat}
    root_path = nodes_flat[0]["path"] if nodes_flat else ""
    total_nodes = len(nodes_flat)
    leaf_nodes = sum(1 for node in nodes_flat if node["is_leaf"])
    max_actual_depth = max((node["depth"] for node in nodes_flat), default=0) + 1
    return _NodeContext(
        nodes_flat=nodes_flat,
        nodes_by_path=nodes_by_path,
        root_path=root_path,
        total_nodes=total_nodes,
        leaf_nodes=leaf_nodes,
        max_actual_depth=max_actual_depth,
    )


def _sync_selected_paths(context: _NodeContext) -> None:
    if not context.root_path:
        return
    if st.session_state.mind_map_selected_path not in context.nodes_by_path:
        st.session_state.mind_map_selected_path = context.root_path
    if st.session_state.mind_map_focus_path not in context.nodes_by_path:
        st.session_state.mind_map_focus_path = context.root_path


def _render_stats(context: _NodeContext) -> None:
    stat_col_1, stat_col_2, stat_col_3 = st.columns(3)
    stat_col_1.metric("Total Nodes", context.total_nodes)
    stat_col_2.metric("Leaf Nodes", context.leaf_nodes)
    stat_col_3.metric("Depth Reached", context.max_actual_depth)


def _render_node_explorer(context: _NodeContext) -> str | None:
    st.markdown("#### Node Explorer")
    explain_path: str | None = None

    st.session_state.mind_map_view_mode = st.radio(
        "View Mode",
        options=["Full Graph", "Layer by Layer (2 Levels)"],
        index=0 if st.session_state.mind_map_view_mode == "Full Graph" else 1,
        key="mind_map_view_mode_radio",
    )

    direction_label = st.selectbox(
        "Graph Layout",
        options=["Left to Right", "Top to Bottom"],
        index=0 if st.session_state.mind_map_graph_direction == "LR" else 1,
    )
    st.session_state.mind_map_graph_direction = "LR" if direction_label == "Left to Right" else "TB"

    if st.session_state.mind_map_view_mode == "Full Graph":
        node_paths = [node["path"] for node in context.nodes_flat]
        selected_index = 0
        if st.session_state.mind_map_selected_path in node_paths:
            selected_index = node_paths.index(st.session_state.mind_map_selected_path)

        selected_path = st.selectbox(
            "Select Node",
            options=node_paths,
            index=selected_index,
            help="Choose any node path from the graph to explain.",
            key="mind_map_full_selected_path",
        )
        st.session_state.mind_map_selected_path = selected_path
        if st.button(
            "Explain Selected Node",
            key="mindmap_explain_selected",
            type="primary",
            width="stretch",
        ):
            explain_path = st.session_state.mind_map_selected_path
        return explain_path

    focus_path = st.session_state.mind_map_focus_path
    focus_node_info = context.nodes_by_path.get(focus_path)
    focus_parent_path = focus_node_info["parent_path"] if focus_node_info else None

    nav_col_1, nav_col_2 = st.columns(2)
    if nav_col_1.button("Root", key="mindmap_layer_root", width="stretch"):
        st.session_state.mind_map_focus_path = context.root_path
        st.session_state.mind_map_selected_path = context.root_path
        st.rerun()
    if nav_col_2.button(
        "Up",
        key="mindmap_layer_up",
        width="stretch",
        disabled=focus_parent_path is None,
    ):
        st.session_state.mind_map_focus_path = focus_parent_path
        st.session_state.mind_map_selected_path = focus_parent_path
        st.rerun()

    st.caption(f"Current focus: {st.session_state.mind_map_focus_path}")
    st.caption("Click a node button to dive into its subtopics. `Mind` explains that node.")
    return None


def _try_render_graph(dot_source: str) -> None:
    try:
        st.graphviz_chart(dot_source, width="stretch")
    except UI_HANDLED_EXCEPTIONS as exc:
        report_ui_warning(
            action="mindmap_render_graph",
            exc=exc,
            prefix="Graph render fallback",
        )
        st.code(dot_source)


def _render_full_graph(tree: dict[str, Any]) -> str:
    mind_map_dot = build_mind_map_dot(
        tree,
        selected_path=st.session_state.mind_map_selected_path,
        direction=st.session_state.mind_map_graph_direction,
    )
    _try_render_graph(mind_map_dot)
    return mind_map_dot


def _render_layer_graph(context: _NodeContext) -> tuple[str, str | None]:
    explain_path: str | None = None
    focus_path = st.session_state.mind_map_focus_path
    focus_node_info = context.nodes_by_path.get(focus_path)
    if not focus_node_info:
        return "", explain_path

    layer_subtree = clone_subtree_for_layers(focus_node_info["node_ref"], remaining_layers=2)
    local_selected = localize_selected_path(st.session_state.mind_map_selected_path, focus_path)
    layer_dot = build_mind_map_dot(
        layer_subtree,
        selected_path=local_selected,
        direction=st.session_state.mind_map_graph_direction,
    )
    _try_render_graph(layer_dot)

    visible_nodes = visible_nodes_for_focus(
        context.nodes_flat,
        focus_path=focus_path,
        max_relative_layers=2,
    )
    st.markdown("#### Layer Node Actions")
    action_cols = st.columns(2)
    for idx, node in enumerate(visible_nodes):
        node_key_hash = hashlib.sha1(node["path"].encode("utf-8")).hexdigest()[:10]
        target_col = action_cols[idx % 2]
        with target_col:
            with st.container(border=True):
                node_button_cols = st.columns([0.72, 0.28])
                if node_button_cols[0].button(
                    node["name"],
                    key=f"mindmap_layer_open_{node_key_hash}",
                    width="stretch",
                ):
                    st.session_state.mind_map_focus_path = node["path"]
                    st.session_state.mind_map_selected_path = node["path"]
                    st.rerun()
                if node_button_cols[1].button(
                    "Mind",
                    key=f"mindmap_layer_mind_{node_key_hash}",
                    width="stretch",
                ):
                    st.session_state.mind_map_selected_path = node["path"]
                    explain_path = node["path"]
                st.caption(node["path"])
    return layer_dot, explain_path


def _render_map(tree: dict[str, Any], context: _NodeContext) -> tuple[str, str | None]:
    if st.session_state.mind_map_view_mode == "Full Graph":
        return _render_full_graph(tree), None
    return _render_layer_graph(context)


def _render_png_export(dot_source: str) -> None:
    if not dot_source:
        return
    safe_topic = re.sub(r"[^a-zA-Z0-9_-]+", "_", st.session_state.mind_map_topic.strip())[:60].strip("_") or "mind_map"
    mode_tag = "full" if st.session_state.mind_map_view_mode == "Full Graph" else "layer"
    png_bytes, png_error = render_dot_as_png(dot_source)
    _, export_right = st.columns([0.72, 0.28], gap="large")
    with export_right:
        if png_bytes is not None:
            st.download_button(
                "Download Mind Map (PNG)",
                data=png_bytes,
                file_name=f"{safe_topic}_{mode_tag}.png",
                mime="image/png",
                key="mind_map_download_png",
                width="stretch",
            )
            return

        st.button(
            "Download Mind Map (PNG)",
            key="mind_map_download_png_disabled",
            disabled=True,
            width="stretch",
        )
        if png_error:
            st.caption(png_error)


def _handle_explain_request(
    *,
    explain_path: str | None,
    mind_map_service: MindMapService,
    llm_service: CachedLLMService,
    settings: GroqSettings,
    cache_count_placeholder: Any,
) -> None:
    if not explain_path:
        return
    if not settings.has_api_key():
        st.error("Please enter your Groq API key in the sidebar to explain a node.")
        return
    if not settings.has_model():
        st.error("Please select or enter a valid model in the sidebar.")
        return

    try:
        with st.spinner(f"Explaining: {explain_path}"):
            explanation_text, cache_hit = mind_map_service.explain_node(
                root_topic=st.session_state.mind_map_topic,
                node_path=explain_path,
                settings=settings,
            )

        st.session_state.mind_map_last_explained_path = explain_path
        st.session_state.mind_map_last_explanation = explanation_text

        if cache_hit:
            st.info("Explanation served from cache. No API call made.")
        else:
            cache_count_placeholder.caption(f"Cached responses: {llm_service.count}")
    except UI_HANDLED_EXCEPTIONS as exc:
        report_ui_error(action="mindmap_explain_node", exc=exc)


def _render_latest_explanation() -> None:
    if not st.session_state.mind_map_last_explanation:
        return
    st.markdown("---")
    st.subheader(f"Explanation: {st.session_state.mind_map_last_explained_path}")
    st.markdown(st.session_state.mind_map_last_explanation)


def render_mind_map_tab(
    *,
    mind_map_service: MindMapService,
    llm_service: CachedLLMService,
    settings: GroqSettings,
    cache_count_placeholder: Any,
) -> None:
    inputs = _render_generation_inputs()
    _handle_generation_request(
        inputs=inputs,
        mind_map_service=mind_map_service,
        llm_service=llm_service,
        settings=settings,
        cache_count_placeholder=cache_count_placeholder,
    )

    tree = st.session_state.mind_map_tree
    if tree is None:
        return

    st.subheader(f"Mind Map: {st.session_state.mind_map_topic}")
    st.caption("Use Full Graph for complete overview, or Layer by Layer to drill down 2 levels at a time.")

    context = _build_node_context(tree)
    _sync_selected_paths(context)
    _render_stats(context)

    map_col, control_col = st.columns([0.72, 0.28], gap="large")
    explain_path_from_controls: str | None = None
    with control_col:
        explain_path_from_controls = _render_node_explorer(context)

    current_dot = ""
    explain_path_from_map: str | None = None
    with map_col:
        current_dot, explain_path_from_map = _render_map(tree, context)

    _render_png_export(current_dot)
    _handle_explain_request(
        explain_path=explain_path_from_map or explain_path_from_controls,
        mind_map_service=mind_map_service,
        llm_service=llm_service,
        settings=settings,
        cache_count_placeholder=cache_count_placeholder,
    )
    _render_latest_explanation()
