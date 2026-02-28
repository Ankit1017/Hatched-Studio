from __future__ import annotations

from dataclasses import dataclass

from main_app.ui.asset_history.context import RendererFn


@dataclass(frozen=True)
class AssetHistoryRendererPlugin:
    intent: str
    renderer: RendererFn
