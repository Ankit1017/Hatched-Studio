from __future__ import annotations

from main_app.ui.agent_dashboard.handlers.basic import render_audio_overview_asset
from main_app.ui.agent_dashboard.renderer_plugins.types import AgentAssetRendererPlugin


PLUGIN = AgentAssetRendererPlugin(
    intent="audio_overview",
    handler=render_audio_overview_asset,
)
