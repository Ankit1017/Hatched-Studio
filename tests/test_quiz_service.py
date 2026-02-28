from __future__ import annotations

import sys
import types

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(choices=[])))

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

import unittest

from main_app.models import GroqSettings
from main_app.services.quiz_service import QuizService


class _FakeLLMService:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text

    def call(self, **_kwargs: object) -> tuple[str, bool]:
        return self._response_text, False


class _FakeParser:
    def parse(self, *_args: object, **_kwargs: object):
        return (
            {
                "topic": "CDC Pipeline",
                "questions": [
                    {
                        "question": "What is CDC?",
                        "options": ["A", "B", "C", "D"],
                        "correct_index": 0,
                    }
                ],
            },
            None,
            "parsed",
        )

    def normalize_payload(self, payload: object, **_kwargs: object):
        return payload, None


class _FailingHistoryStore:
    def upsert_quiz(self, _record: dict[str, object]) -> None:
        raise RuntimeError("disk write failed")

    def list_quizzes(self) -> list[dict[str, object]]:
        return []

    def get_quiz(self, _quiz_id: str):
        return None


class TestQuizService(unittest.TestCase):
    def test_generate_quiz_reports_persistence_failure_in_note(self) -> None:
        service = QuizService(
            llm_service=_FakeLLMService('{"topic": "CDC", "questions": []}'),
            parser=_FakeParser(),
            history_store=_FailingHistoryStore(),
        )
        settings = GroqSettings(
            api_key="test-key",
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=512,
        )

        with self.assertLogs("main_app.services.quiz_service", level="ERROR") as logs:
            result = service.generate_quiz(
                topic="CDC Pipeline",
                question_count=3,
                difficulty="Intermediate",
                constraints="",
                settings=settings,
            )

        self.assertIsNotNone(result.parsed_quiz)
        self.assertIn("could not persist history", (result.parse_note or "").lower())
        self.assertTrue(any("Quiz history persistence failed." in line for line in logs.output))

    def test_parse_feedback_json_handles_repair(self) -> None:
        raw = '{"correct_one_liner":"Correct.","wrong_one_liner":"Wrong.",}'
        parsed = QuizService._parse_feedback_json(raw)

        self.assertEqual(parsed["correct_one_liner"], "Correct.")
        self.assertEqual(parsed["wrong_one_liner"], "Wrong.")

    def test_parse_feedback_json_invalid_payload_returns_defaults(self) -> None:
        with self.assertLogs("main_app.services.quiz_service", level="WARNING") as logs:
            parsed = QuizService._parse_feedback_json("not-json")
        self.assertEqual(parsed, {"correct_one_liner": "", "wrong_one_liner": ""})
        self.assertTrue(any("parse failed after local repair" in line for line in logs.output))


if __name__ == "__main__":
    unittest.main()
