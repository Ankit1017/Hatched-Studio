from __future__ import annotations

from main_app.ui.agent_dashboard.handlers.interactive import render_flashcards_asset
from main_app.ui.agent_dashboard.renderer_plugins.types import AgentAssetRendererPlugin


PLUGIN = AgentAssetRendererPlugin(intent="flashcards", handler=render_flashcards_asset)
