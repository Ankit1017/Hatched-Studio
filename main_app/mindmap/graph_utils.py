from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from typing import Any


def collect_mind_map_nodes(
    node: dict[str, Any],
    *,
    path: list[str] | None = None,
    depth: int = 0,
    parent_path: str | None = None,
) -> list[dict[str, Any]]:
    if path is None:
        path = [node["name"]]

    current_path = " > ".join(path)
    children = node.get("children", [])
    nodes: list[dict[str, Any]] = [
        {
            "name": node["name"],
            "path": current_path,
            "depth": depth,
            "is_leaf": len(children) == 0,
            "parent_path": parent_path,
            "node_ref": node,
        }
    ]

    for child in children:
        nodes.extend(
            collect_mind_map_nodes(
                child,
                path=path + [child["name"]],
                depth=depth + 1,
                parent_path=current_path,
            )
        )

    return nodes


def build_mind_map_dot(
    node: dict[str, Any],
    *,
    selected_path: str | None = None,
    direction: str = "LR",
) -> str:
    depth_palette = {
        0: ("#0f172a", "#f8fafc", "#0f172a"),
        1: ("#dbeafe", "#1e3a8a", "#93c5fd"),
        2: ("#dcfce7", "#166534", "#86efac"),
        3: ("#fef3c7", "#92400e", "#fde68a"),
        4: ("#ffe4e6", "#9f1239", "#fda4af"),
        5: ("#ffedd5", "#9a3412", "#fdba74"),
        6: ("#ecfeff", "#155e75", "#67e8f9"),
        7: ("#f1f5f9", "#334155", "#cbd5e1"),
    }

    lines = [
        "digraph MindMap {",
        f'  graph [rankdir={direction}, splines=polyline, bgcolor="transparent", nodesep="0.5", ranksep="0.9"];',
        '  node [shape=box, style="filled,rounded", fontname="Helvetica", fontsize="11", penwidth="1.2"];',
        '  edge [color="#9ca3af", penwidth="1.0"];',
    ]

    def walk(current_node: dict[str, Any], path: list[str] | None = None, depth: int = 0) -> None:
        current_path_list = path if path is not None else [current_node["name"]]
        current_path = " > ".join(current_path_list)
        node_id = _mind_map_node_id(current_path_list)
        fill, font, border = depth_palette.get(min(depth, 7), depth_palette[7])
        penwidth = "2.4" if selected_path and current_path == selected_path else "1.2"
        border_color = "#ef4444" if selected_path and current_path == selected_path else border

        lines.append(
            f'  {node_id} [label="{_dot_escape(current_node["name"])}", '
            f'fillcolor="{fill}", fontcolor="{font}", color="{border_color}", '
            f'penwidth="{penwidth}"];'
        )

        for child in current_node.get("children", []):
            child_path = current_path_list + [child["name"]]
            child_id = _mind_map_node_id(child_path)
            lines.append(f"  {node_id} -> {child_id};")
            walk(child, child_path, depth + 1)

    walk(node)
    lines.append("}")
    return "\n".join(lines)


def clone_subtree_for_layers(node: dict[str, Any], *, remaining_layers: int) -> dict[str, Any]:
    cloned = {"name": node["name"], "children": []}
    if remaining_layers <= 0:
        return cloned

    for child in node.get("children", []):
        cloned["children"].append(clone_subtree_for_layers(child, remaining_layers=remaining_layers - 1))

    return cloned


def localize_selected_path(global_selected_path: str, focus_path: str) -> str | None:
    focus_name = focus_path.split(" > ")[-1]
    if global_selected_path == focus_path:
        return focus_name
    if global_selected_path.startswith(focus_path + " > "):
        suffix = global_selected_path[len(focus_path) + 3 :]
        return f"{focus_name} > {suffix}"
    return None


def visible_nodes_for_focus(
    nodes_flat: list[dict[str, Any]],
    *,
    focus_path: str,
    max_relative_layers: int = 2,
) -> list[dict[str, Any]]:
    focus_depth = None
    for node in nodes_flat:
        if node["path"] == focus_path:
            focus_depth = node["depth"]
            break
    if focus_depth is None:
        return []

    focus_prefix = focus_path + " > "
    visible_nodes: list[dict[str, Any]] = []
    for node in nodes_flat:
        if node["path"] == focus_path:
            visible_nodes.append(node)
        elif node["path"].startswith(focus_prefix) and node["depth"] <= focus_depth + max_relative_layers:
            visible_nodes.append(node)
    return visible_nodes


def _dot_escape(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _mind_map_node_id(path: list[str]) -> str:
    key = " > ".join(path)
    return f"n_{hashlib.sha1(key.encode('utf-8')).hexdigest()[:14]}"


def render_dot_as_png(dot_source: str) -> tuple[bytes | None, str | None]:
    source = str(dot_source or "").strip()
    if not source:
        return None, "Mind map graph is empty."

    dot_binary = _resolve_dot_binary()
    if dot_binary and not os.environ.get("GRAPHVIZ_DOT"):
        os.environ["GRAPHVIZ_DOT"] = dot_binary

    graphviz_error = ""
    try:
        import graphviz  # type: ignore

        png_bytes = graphviz.Source(source).pipe(format="png")
        if png_bytes:
            return bytes(png_bytes), None
    except Exception as exc:  # noqa: BLE001
        graphviz_error = str(exc).strip()

    if not dot_binary:
        base_error = (
            "Graphviz 'dot' binary is not installed or not visible to this app. "
            "Install Graphviz and ensure `dot` is on PATH."
        )
        if graphviz_error:
            return None, f"{base_error} graphviz-python error: {graphviz_error}"
        return None, base_error

    try:
        result = subprocess.run(
            [dot_binary, "-Tpng"],
            input=source.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return None, f"Failed to render PNG with Graphviz: {exc}"

    if result.returncode != 0 or not result.stdout:
        stderr_text = result.stderr.decode("utf-8", errors="ignore").strip()
        message = stderr_text or "Unknown Graphviz rendering error."
        if graphviz_error:
            return None, f"{message} graphviz-python error: {graphviz_error}"
        return None, message

    return bytes(result.stdout), None


def _resolve_dot_binary() -> str | None:
    env_dot = str(os.environ.get("GRAPHVIZ_DOT", "")).strip()
    if env_dot and os.path.isfile(env_dot):
        return env_dot

    which_dot = shutil.which("dot")
    if which_dot:
        return which_dot

    common_paths = [
        "/opt/homebrew/bin/dot",
        "/usr/local/bin/dot",
        "/usr/bin/dot",
    ]
    for candidate in common_paths:
        if os.path.isfile(candidate):
            return candidate

    return None
