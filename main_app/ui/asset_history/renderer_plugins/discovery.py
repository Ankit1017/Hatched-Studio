from __future__ import annotations

from main_app.plugins import discover_module_plugins
from main_app.ui.asset_history.renderer_plugins.types import AssetHistoryRendererPlugin


def discover_asset_history_renderer_plugins() -> list[AssetHistoryRendererPlugin]:
    plugins = discover_module_plugins(
        package_name="main_app.ui.asset_history.renderer_plugins",
        plugin_type=AssetHistoryRendererPlugin,
    )
    deduped: dict[str, AssetHistoryRendererPlugin] = {}
    for plugin in plugins:
        normalized_intent = " ".join(str(plugin.intent).strip().split()).lower()
        if not normalized_intent:
            continue
        deduped[normalized_intent] = plugin
    return list(deduped.values())
