from __future__ import annotations

from main_app.ui.asset_history.renderer_plugins.types import AssetHistoryRendererPlugin
from main_app.ui.asset_history.renderers.mindmap import render_mindmap_record


PLUGIN = AssetHistoryRendererPlugin(intent="mindmap", renderer=render_mindmap_record)
