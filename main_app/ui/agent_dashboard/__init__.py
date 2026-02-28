"""Agent dashboard UI building blocks (lazy exports)."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AgentAssetRenderContext",
    "AgentAssetRenderer",
    "AgentDashboardChatFlowController",
    "AgentDashboardSessionManager",
    "SessionStateGateway",
    "StreamlitSessionStateGateway",
    "apply_agent_dashboard_styles",
]


def __getattr__(name: str) -> Any:
    if name == "AgentAssetRenderContext":
        module = import_module("main_app.ui.agent_dashboard.context")
        return getattr(module, name)
    if name == "AgentAssetRenderer":
        module = import_module("main_app.ui.agent_dashboard.asset_renderer")
        return getattr(module, name)
    if name == "AgentDashboardChatFlowController":
        module = import_module("main_app.ui.agent_dashboard.chat_flow_controller")
        return getattr(module, name)
    if name == "AgentDashboardSessionManager":
        module = import_module("main_app.ui.agent_dashboard.session_manager")
        return getattr(module, name)
    if name in {"SessionStateGateway", "StreamlitSessionStateGateway"}:
        module = import_module("main_app.ui.agent_dashboard.state_gateway")
        return getattr(module, name)
    if name == "apply_agent_dashboard_styles":
        module = import_module("main_app.ui.agent_dashboard.styles")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
