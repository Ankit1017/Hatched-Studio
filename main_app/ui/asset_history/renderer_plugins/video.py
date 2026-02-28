from __future__ import annotations

from main_app.ui.asset_history.renderer_plugins.types import AssetHistoryRendererPlugin
from main_app.ui.asset_history.renderers.interactive import render_video_record


PLUGIN = AssetHistoryRendererPlugin(intent="video", renderer=render_video_record)
