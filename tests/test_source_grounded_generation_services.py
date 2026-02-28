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

from main_app.models import GroqSettings
from main_app.services.quiz_service import QuizService
from main_app.services.report_service import ReportService
from main_app.services.slideshow_service import SlideShowService


class _RecordingLLMService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def call(self, **kwargs: object) -> tuple[str, bool]:
        self.calls.append(dict(kwargs))
        return "{}", False


class _FakeQuizParser:
    def parse(self, *_args: object, **_kwargs: object):
        return (
            {
                "topic": "CDC Pipeline",
                "questions": [
                    {
                        "question": "What is CDC? [S1]",
                        "options": ["A", "B", "C", "D"],
                        "correct_index": 0,
                    }
                ],
            },
            None,
            None,
        )

    def normalize_payload(self, payload: object, **_kwargs: object):
        return payload, None


class _FakeQuizHistoryStore:
    def upsert_quiz(self, _record: dict[str, object]) -> None:
        return None

    def list_quizzes(self):
        return []

    def get_quiz(self, _quiz_id: str):
        return None


class _FakeSlideParser:
    def parse_outline(self, *_args: object, **_kwargs: object):
        return (
            {
                "topic": "CDC Pipeline",
                "subtopics": [
                    {"title": "Intro", "focus": "Basics"},
                    {"title": "Architecture", "focus": "Flow"},
                ],
            },
            None,
            None,
        )

    def parse_section_slides(self, *_args: object, **_kwargs: object):
        return (
            [
                {
                    "title": "Slide",
                    "bullets": ["Fact [S1]", "More■detail [S1]"],
                    "speaker_notes": "",
                    "code_snippet": "",
                    "code_language": "",
                }
            ],
            None,
            None,
        )


class TestSourceGroundedGenerationServices(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = GroqSettings(
            api_key="key",
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=512,
        )
        self.grounding_context = "[S1] source.md\nCDC emits change events."
        self.source_manifest = [{"source_id": "S1", "name": "source.md", "char_count": 35, "truncated": False}]

    def test_report_service_includes_grounding_prompt(self) -> None:
        llm = _RecordingLLMService()
        service = ReportService(llm_service=llm)  # type: ignore[arg-type]

        service.generate(
            topic="CDC Pipeline",
            format_key="briefing_doc",
            additional_notes="",
            grounding_context=self.grounding_context,
            source_manifest=self.source_manifest,
            require_citations=True,
            settings=self.settings,
        )

        self.assertEqual(len(llm.calls), 1)
        messages = llm.calls[0]["messages"]
        self.assertIsInstance(messages, list)
        assert isinstance(messages, list)
        full_prompt = "\n".join(str(item.get("content", "")) for item in messages if isinstance(item, dict))
        self.assertIn(self.grounding_context, full_prompt)
        self.assertIn("Citation requirement", full_prompt)

    def test_quiz_service_includes_grounding_prompt(self) -> None:
        llm = _RecordingLLMService()
        service = QuizService(
            llm_service=llm,  # type: ignore[arg-type]
            parser=_FakeQuizParser(),  # type: ignore[arg-type]
            history_store=_FakeQuizHistoryStore(),  # type: ignore[arg-type]
        )

        result = service.generate_quiz(
            topic="CDC Pipeline",
            question_count=5,
            difficulty="Intermediate",
            constraints="",
            grounding_context=self.grounding_context,
            source_manifest=self.source_manifest,
            require_citations=True,
            settings=self.settings,
        )

        self.assertIsNone(result.parse_error)
        self.assertEqual(len(llm.calls), 1)
        self.assertFalse(bool(llm.calls[0].get("use_cache", True)))
        messages = llm.calls[0]["messages"]
        self.assertIsInstance(messages, list)
        assert isinstance(messages, list)
        full_prompt = "\n".join(str(item.get("content", "")) for item in messages if isinstance(item, dict))
        self.assertIn(self.grounding_context, full_prompt)
        self.assertIn("Citation requirement", full_prompt)

    def test_slideshow_service_includes_grounding_prompt(self) -> None:
        llm = _RecordingLLMService()
        service = SlideShowService(
            llm_service=llm,  # type: ignore[arg-type]
            parser=_FakeSlideParser(),  # type: ignore[arg-type]
        )

        result = service.generate(
            topic="CDC Pipeline",
            constraints="",
            subtopic_count=2,
            slides_per_subtopic=1,
            code_mode="none",
            grounding_context=self.grounding_context,
            source_manifest=self.source_manifest,
            require_citations=True,
            settings=self.settings,
        )

        self.assertIsNone(result.parse_error)
        self.assertGreaterEqual(len(llm.calls), 3)
        combined_prompt = "\n".join(
            str(message.get("content", ""))
            for call in llm.calls
            for message in call.get("messages", [])
            if isinstance(message, dict)
        )
        self.assertIn(self.grounding_context, combined_prompt)
        self.assertIn("Citation requirement", combined_prompt)
        slides = result.slides or []
        joined = " ".join(
            " ".join(str(item) for item in slide.get("bullets", []))
            for slide in slides
            if isinstance(slide, dict)
        )
        self.assertIn("[S1]", joined)

    def test_slideshow_service_removes_citations_when_not_required(self) -> None:
        llm = _RecordingLLMService()
        service = SlideShowService(
            llm_service=llm,  # type: ignore[arg-type]
            parser=_FakeSlideParser(),  # type: ignore[arg-type]
        )

        result = service.generate(
            topic="CDC Pipeline",
            constraints="",
            subtopic_count=2,
            slides_per_subtopic=1,
            code_mode="none",
            grounding_context="",
            source_manifest=[],
            require_citations=False,
            settings=self.settings,
        )

        self.assertIsNone(result.parse_error)
        slides = result.slides or []
        joined = " ".join(
            " ".join(str(item) for item in slide.get("bullets", []))
            for slide in slides
            if isinstance(slide, dict)
        )
        self.assertNotIn("[S1]", joined)
        self.assertNotIn("■", joined)


if __name__ == "__main__":
    unittest.main()
