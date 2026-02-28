from __future__ import annotations

import streamlit as st

from main_app.ui.agent_dashboard.renderer_plugins.types import AgentAssetRendererPlugin


def _render_${tool_key}_asset(**kwargs: object) -> None:
    st.caption("TODO: implement renderer for ${intent} asset")


agent_asset_renderer_plugin = AgentAssetRendererPlugin(
    intent="${intent}",
    handler=_render_${tool_key}_asset,
)
