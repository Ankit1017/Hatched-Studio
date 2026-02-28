from __future__ import annotations

from main_app.ui.agent_dashboard.handlers.interactive import render_video_asset
from main_app.ui.agent_dashboard.renderer_plugins.types import AgentAssetRendererPlugin


PLUGIN = AgentAssetRendererPlugin(intent="video", handler=render_video_asset)
