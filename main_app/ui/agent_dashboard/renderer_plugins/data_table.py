from __future__ import annotations

from main_app.ui.agent_dashboard.handlers.basic import render_data_table_asset
from main_app.ui.agent_dashboard.renderer_plugins.types import AgentAssetRendererPlugin


PLUGIN = AgentAssetRendererPlugin(intent="data table", handler=render_data_table_asset)
