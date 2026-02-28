from __future__ import annotations

import sys
import types
import unittest

if "streamlit" not in sys.modules:
    try:
        import streamlit  # noqa: F401
    except ModuleNotFoundError:
        sys.modules["streamlit"] = types.SimpleNamespace()

from main_app.services.agent_dashboard.default_asset_executor_registrations import (
    build_default_asset_executor_registrations,
)
from main_app.services.agent_dashboard.executor_plugins import (
    discover_asset_executor_plugins,
)
from main_app.services.agent_dashboard.intent_catalog import ASSET_INTENTS
from main_app.ui.agent_dashboard.render_handlers import build_default_render_handlers
from main_app.ui.agent_dashboard.renderer_plugins import (
    discover_agent_asset_renderer_plugins,
)
from main_app.ui.asset_history.renderer_plugins import (
    discover_asset_history_renderer_plugins,
)
from main_app.ui.asset_history.renderer_registry import build_record_renderers


class TestAssetPluginDiscovery(unittest.TestCase):
    def test_executor_plugins_cover_all_catalog_intents(self) -> None:
        discovered_intents = {
            " ".join(str(plugin.intent).strip().split()).lower()
            for plugin in discover_asset_executor_plugins()
        }
        self.assertTrue(set(ASSET_INTENTS).issubset(discovered_intents))

    def test_default_executor_registrations_are_discovered(self) -> None:
        registrations = list(
            build_default_asset_executor_registrations(
                explainer_service=object(),  # type: ignore[arg-type]
                mind_map_service=object(),  # type: ignore[arg-type]
                flashcards_service=object(),  # type: ignore[arg-type]
                data_table_service=object(),  # type: ignore[arg-type]
                quiz_service=object(),  # type: ignore[arg-type]
                slideshow_service=object(),  # type: ignore[arg-type]
                video_service=object(),  # type: ignore[arg-type]
                audio_overview_service=object(),  # type: ignore[arg-type]
                report_service=object(),  # type: ignore[arg-type]
            )
        )
        registration_intents = [registration.intent for registration in registrations]
        self.assertEqual(
            [intent for intent in ASSET_INTENTS if intent in registration_intents],
            [intent for intent in ASSET_INTENTS if intent in set(registration_intents)],
        )
        self.assertTrue(set(ASSET_INTENTS).issubset(set(registration_intents)))

    def test_agent_renderer_plugins_cover_all_catalog_intents(self) -> None:
        discovered_intents = {
            " ".join(str(plugin.intent).strip().split()).lower()
            for plugin in discover_agent_asset_renderer_plugins()
        }
        self.assertTrue(set(ASSET_INTENTS).issubset(discovered_intents))

        handlers = build_default_render_handlers()
        self.assertTrue(set(ASSET_INTENTS).issubset(set(handlers.keys())))

    def test_asset_history_renderer_plugins_cover_all_catalog_intents(self) -> None:
        discovered_intents = {
            " ".join(str(plugin.intent).strip().split()).lower()
            for plugin in discover_asset_history_renderer_plugins()
        }
        self.assertTrue(set(ASSET_INTENTS).issubset(discovered_intents))

        handlers = build_record_renderers()
        self.assertTrue(set(ASSET_INTENTS).issubset(set(handlers.keys())))


if __name__ == "__main__":
    unittest.main()
