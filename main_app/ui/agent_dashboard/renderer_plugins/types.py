from __future__ import annotations

from dataclasses import dataclass

from main_app.ui.agent_dashboard.handlers.types import AgentAssetRenderHandler


@dataclass(frozen=True)
class AgentAssetRendererPlugin:
    intent: str
    handler: AgentAssetRenderHandler
