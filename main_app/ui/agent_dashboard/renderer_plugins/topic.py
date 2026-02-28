from __future__ import annotations

from main_app.ui.agent_dashboard.handlers.basic import render_topic_asset
from main_app.ui.agent_dashboard.renderer_plugins.types import AgentAssetRendererPlugin


PLUGIN = AgentAssetRendererPlugin(intent="topic", handler=render_topic_asset)
