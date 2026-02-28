from __future__ import annotations

import sys
import types

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(choices=[]))
            )

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

import unittest
import json

from main_app.models import GroqSettings
from main_app.parsers.slideshow_parser import SlideShowParser


class _DummyLLMService:
    def call(self, **_kwargs: object) -> tuple[str, bool]:
        raise AssertionError("LLM repair should not be used in this parser unit test.")


class TestSlideShowParser(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = SlideShowParser(llm_service=_DummyLLMService())  # type: ignore[arg-type]
        self.settings = GroqSettings(api_key="", model="", temperature=0.2, max_tokens=512)

    def test_parse_section_slides_recovers_when_last_slide_is_truncated(self) -> None:
        raw_text = """```json
{
  "slides": [
    {
      "title": "Tree Data Structures",
      "bullets": ["Tree concept", "Types of trees", "Real-world usage"],
      "speaker_notes": "",
      "code_snippet": "",
      "code_language": ""
    },
    {
      "title": "B-Tree Example in Python",
      "bullets": ["Example implementation", "Insertion and deletion basics"],
      "speaker_notes": "Explain quickly.",
      "code_snippet": "class BTree:\\n  def insert(self, x):\\n    return x",
      "code_language": "python"
    },
    {
      "title": "Depth-First Search (DFS) Example",
      "bullets": ["Graph traversal", "DFS recursion"],
      "speaker_notes": "This one is intentionally cut.",
      "code_snippet": "def dfs(graph, node):\\n  seen = {\\"root\\": node}
"""

        slides, parse_error, parse_note = self.parser.parse_section_slides(
            raw_text,
            max_slides=4,
            settings=self.settings,
        )

        self.assertIsNone(parse_error)
        self.assertIsNotNone(slides)
        self.assertEqual(len(slides or []), 2)
        self.assertIn("truncated", (parse_note or "").lower())
        first_slide = (slides or [])[0]
        self.assertEqual(first_slide.get("representation"), "bullet")
        self.assertIn("layout_payload", first_slide)

    def test_parse_section_slides_supports_all_representations(self) -> None:
        representation_payloads = {
            "bullet": {"items": ["One", "Two"]},
            "two_column": {
                "left_title": "Pros",
                "left_items": ["Fast", "Simple"],
                "right_title": "Cons",
                "right_items": ["Limited", "Rigid"],
            },
            "timeline": {"events": [{"label": "Start", "detail": "Kickoff"}]},
            "comparison": {
                "left_title": "Option A",
                "left_points": ["Easy"],
                "right_title": "Option B",
                "right_points": ["Flexible"],
            },
            "process_flow": {"steps": [{"title": "Plan", "detail": "Create scope"}]},
            "metric_cards": {"cards": [{"label": "Latency", "value": "120ms", "context": "p95"}]},
        }
        for representation, layout_payload in representation_payloads.items():
            with self.subTest(representation=representation):
                raw_text = (
                    "{"
                    '"slides":['
                    "{"
                    f'"title":"{representation} slide",'
                    f'"representation":"{representation}",'
                    f'"layout_payload":{json.dumps(layout_payload)},'
                    '"bullets":["Primary point","Secondary point"],'
                    '"speaker_notes":"",'
                    '"code_snippet":"",'
                    '"code_language":""'
                    "}"
                    "]"
                    "}"
                )
                slides, parse_error, _ = self.parser.parse_section_slides(
                    raw_text,
                    max_slides=1,
                    settings=self.settings,
                )
                self.assertIsNone(parse_error)
                self.assertIsNotNone(slides)
                parsed_slide = (slides or [])[0]
                self.assertEqual(parsed_slide.get("representation"), representation)
                self.assertIn("layout_payload", parsed_slide)
                self.assertTrue(parsed_slide.get("bullets"))

    def test_parse_section_slides_falls_back_unknown_representation_to_bullet(self) -> None:
        raw_text = (
            "{"
            '"slides":['
            "{"
            '"title":"Invalid rep",'
            '"representation":"radar_chart",'
            '"layout_payload":{"points":[1,2,3]},'
            '"bullets":["A","B"],'
            '"speaker_notes":"",'
            '"code_snippet":"",'
            '"code_language":""'
            "}"
            "]"
            "}"
        )
        slides, parse_error, parse_note = self.parser.parse_section_slides(
            raw_text,
            max_slides=1,
            settings=self.settings,
        )
        self.assertIsNone(parse_error)
        self.assertIsNotNone(slides)
        parsed_slide = (slides or [])[0]
        self.assertEqual(parsed_slide.get("representation"), "bullet")
        self.assertIn("Unknown representation", parse_note or "")


if __name__ == "__main__":
    unittest.main()
