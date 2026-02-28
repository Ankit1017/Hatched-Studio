from __future__ import annotations

from main_app.ui.asset_history.renderer_plugins.types import AssetHistoryRendererPlugin
from main_app.ui.asset_history.renderers.interactive import render_quiz_record


PLUGIN = AssetHistoryRendererPlugin(intent="quiz", renderer=render_quiz_record)
