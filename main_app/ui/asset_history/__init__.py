"""Asset history rendering components."""

from __future__ import annotations

from typing import Any

from main_app.ui.asset_history.context import AssetHistoryRenderContext


def render_asset_history_tab(*args: Any, **kwargs: Any) -> None:
    from main_app.ui.asset_history.record_renderer import render_asset_history_tab as _render_impl

    _render_impl(*args, **kwargs)


__all__ = ["AssetHistoryRenderContext", "render_asset_history_tab"]
