from __future__ import annotations

from main_app.ui.asset_history.renderer_plugins.types import AssetHistoryRendererPlugin
from main_app.ui.asset_history.renderers.common import render_report_record


PLUGIN = AssetHistoryRendererPlugin(intent="report", renderer=render_report_record)
