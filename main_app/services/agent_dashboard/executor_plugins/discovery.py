from __future__ import annotations

from main_app.plugins import discover_module_plugins
from main_app.services.agent_dashboard.executor_types import AssetExecutorPlugin


def discover_asset_executor_plugins() -> list[AssetExecutorPlugin]:
    plugins = discover_module_plugins(
        package_name="main_app.services.agent_dashboard.executor_plugins",
        plugin_type=AssetExecutorPlugin,
    )
    deduped: dict[str, AssetExecutorPlugin] = {}
    for plugin in plugins:
        normalized_intent = " ".join(str(plugin.intent).strip().split()).lower()
        if not normalized_intent:
            continue
        deduped[normalized_intent] = plugin
    return list(deduped.values())
