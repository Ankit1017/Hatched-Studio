from __future__ import annotations

from main_app.plugins import discover_module_plugins
from main_app.ui.agent_dashboard.renderer_plugins.types import AgentAssetRendererPlugin


def discover_agent_asset_renderer_plugins() -> list[AgentAssetRendererPlugin]:
    plugins = discover_module_plugins(
        package_name="main_app.ui.agent_dashboard.renderer_plugins",
        plugin_type=AgentAssetRendererPlugin,
    )
    deduped: dict[str, AgentAssetRendererPlugin] = {}
    for plugin in plugins:
        normalized_intent = " ".join(str(plugin.intent).strip().split()).lower()
        if not normalized_intent:
            continue
        deduped[normalized_intent] = plugin
    return list(deduped.values())
