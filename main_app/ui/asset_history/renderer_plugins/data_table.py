from __future__ import annotations

from main_app.ui.asset_history.renderer_plugins.types import AssetHistoryRendererPlugin
from main_app.ui.asset_history.renderers.common import render_data_table_record


PLUGIN = AssetHistoryRendererPlugin(intent="data table", renderer=render_data_table_record)
