from __future__ import annotations

from main_app.ui.asset_history.renderer_plugins.types import AssetHistoryRendererPlugin
from main_app.ui.asset_history.renderers.interactive import render_slideshow_record


PLUGIN = AssetHistoryRendererPlugin(intent="slideshow", renderer=render_slideshow_record)
