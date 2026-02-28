from __future__ import annotations

from main_app.ui.agent_dashboard.handlers.mindmap import render_mindmap_asset
from main_app.ui.agent_dashboard.renderer_plugins.types import AgentAssetRendererPlugin


PLUGIN = AgentAssetRendererPlugin(intent="mindmap", handler=render_mindmap_asset)
