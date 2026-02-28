from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from main_app.contracts import IntentPayload

if TYPE_CHECKING:
    from main_app.ui.agent_dashboard.context import AgentAssetRenderContext

AgentAsset = dict[str, Any]
AgentAssetRenderHandler = Callable[["AgentAssetRenderContext", str, IntentPayload, Any, AgentAsset], None]
