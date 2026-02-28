from __future__ import annotations

from main_app.models import AssetHistoryRecord
from main_app.services.agent_dashboard import ASSET_INTENTS
from main_app.ui.asset_history.context import AssetHistoryRenderContext, RendererFn
from main_app.ui.asset_history.renderer_plugins import (
    discover_asset_history_renderer_plugins,
)


def build_record_renderers(*, custom_renderers: dict[str, RendererFn] | None = None) -> dict[str, RendererFn]:
    plugins = discover_asset_history_renderer_plugins()
    plugin_map: dict[str, RendererFn] = {}
    for plugin in plugins:
        normalized_intent = " ".join(str(plugin.intent).strip().split()).lower()
        if not normalized_intent:
            continue
        plugin_map[normalized_intent] = plugin.renderer

    ordered_intents = [intent for intent in ASSET_INTENTS if intent in plugin_map]
    ordered_intents.extend(
        sorted(intent for intent in plugin_map.keys() if intent not in ASSET_INTENTS)
    )
    renderers: dict[str, RendererFn] = {intent: plugin_map[intent] for intent in ordered_intents}
    for intent, renderer in (custom_renderers or {}).items():
        normalized_intent = " ".join(str(intent).strip().split()).lower()
        if normalized_intent:
            renderers[normalized_intent] = renderer
    return renderers


def render_default_record(record: AssetHistoryRecord, context: AssetHistoryRenderContext) -> None:
    from main_app.ui.asset_history.renderers.common import render_default_record as _render_default_record

    _render_default_record(record, context)


__all__ = ["build_record_renderers", "render_default_record"]
