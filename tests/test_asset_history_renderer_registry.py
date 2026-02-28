from __future__ import annotations

import sys
import types
import unittest

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(choices=[])))

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

from main_app.ui.asset_history.context import RendererFn

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace()

from main_app.ui.asset_history.renderer_registry import build_record_renderers


class TestAssetHistoryRendererRegistry(unittest.TestCase):
    def test_default_renderers_include_all_assets(self) -> None:
        renderers = build_record_renderers()
        expected = {
            "topic",
            "report",
            "mindmap",
            "flashcards",
            "data table",
            "quiz",
            "slideshow",
            "video",
            "audio_overview",
        }
        self.assertTrue(expected.issubset(set(renderers.keys())))

    def test_custom_renderer_keys_are_normalized(self) -> None:
        def custom_renderer(record, context) -> None:  # type: ignore[no-untyped-def]
            del record, context
            return None

        custom: dict[str, RendererFn] = {"  DATA   TABLE ": custom_renderer}
        renderers = build_record_renderers(custom_renderers=custom)
        self.assertIs(renderers["data table"], custom_renderer)


if __name__ == "__main__":
    unittest.main()
