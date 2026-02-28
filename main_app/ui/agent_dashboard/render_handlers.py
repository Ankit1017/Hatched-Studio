from __future__ import annotations

from main_app.services.agent_dashboard import ASSET_INTENTS
from main_app.ui.agent_dashboard.handlers.basic import render_unknown_asset
from main_app.ui.agent_dashboard.handlers.types import AgentAsset, AgentAssetRenderHandler
from main_app.ui.agent_dashboard.renderer_plugins import (
    discover_agent_asset_renderer_plugins,
)


def build_default_render_handlers() -> dict[str, AgentAssetRenderHandler]:
    discovered_plugins = discover_agent_asset_renderer_plugins()
    plugin_map: dict[str, AgentAssetRenderHandler] = {}
    for plugin in discovered_plugins:
        normalized_intent = " ".join(str(plugin.intent).strip().split()).lower()
        if not normalized_intent:
            continue
        plugin_map[normalized_intent] = plugin.handler

    ordered_intents = [intent for intent in ASSET_INTENTS if intent in plugin_map]
    ordered_intents.extend(
        sorted(intent for intent in plugin_map.keys() if intent not in ASSET_INTENTS)
    )
    return {intent: plugin_map[intent] for intent in ordered_intents}


__all__ = [
    "AgentAsset",
    "AgentAssetRenderHandler",
    "build_default_render_handlers",
    "render_unknown_asset",
]
