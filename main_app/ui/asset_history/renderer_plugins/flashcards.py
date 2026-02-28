from __future__ import annotations

from main_app.ui.asset_history.renderer_plugins.types import AssetHistoryRendererPlugin
from main_app.ui.asset_history.renderers.interactive import render_flashcards_record


PLUGIN = AssetHistoryRendererPlugin(intent="flashcards", renderer=render_flashcards_record)
