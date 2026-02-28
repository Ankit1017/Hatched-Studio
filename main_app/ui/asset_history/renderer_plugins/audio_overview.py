from __future__ import annotations

from main_app.ui.asset_history.renderer_plugins.types import AssetHistoryRendererPlugin
from main_app.ui.asset_history.renderers.audio_overview import render_audio_overview_record


PLUGIN = AssetHistoryRendererPlugin(
    intent="audio_overview",
    renderer=render_audio_overview_record,
)
