from __future__ import annotations

import sys
import types
import unittest

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(choices=[]))
            )

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

from main_app.ui.components.slideshow_view import _render_representation_html


class TestSlideshowViewComponent(unittest.TestCase):
    def test_render_representation_blocks(self) -> None:
        slides = [
            {"representation": "bullet", "layout_payload": {"items": ["A"]}, "bullets": ["A"]},
            {
                "representation": "two_column",
                "layout_payload": {
                    "left_title": "Left",
                    "left_items": ["L1"],
                    "right_title": "Right",
                    "right_items": ["R1"],
                },
                "bullets": ["L1", "R1"],
            },
            {
                "representation": "timeline",
                "layout_payload": {"events": [{"label": "Start", "detail": "Kickoff"}]},
                "bullets": ["Start kickoff"],
            },
            {
                "representation": "process_flow",
                "layout_payload": {"steps": [{"title": "Plan", "detail": "Scope"}]},
                "bullets": ["Plan scope"],
            },
            {
                "representation": "metric_cards",
                "layout_payload": {"cards": [{"label": "Latency", "value": "120ms", "context": "p95"}]},
                "bullets": ["Latency 120ms"],
            },
            {
                "representation": "comparison",
                "layout_payload": {
                    "left_title": "A",
                    "left_points": ["A1"],
                    "right_title": "B",
                    "right_points": ["B1"],
                },
                "bullets": ["A1", "B1"],
            },
        ]
        for slide in slides:
            with self.subTest(representation=slide["representation"]):
                html = _render_representation_html(slide)
                self.assertTrue(str(html).strip())
                self.assertIn("ss-", html)


if __name__ == "__main__":
    unittest.main()
