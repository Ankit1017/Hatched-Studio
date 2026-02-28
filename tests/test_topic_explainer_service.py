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

from main_app.models import GroqSettings
from main_app.domains.topic.services.topic_explainer_service import TopicExplainerService


class _FakeLLMService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def call(self, **_kwargs: object) -> tuple[str, bool]:
        self.calls.append(dict(_kwargs))
        return "Detailed explanation", True


class _FakeHistoryService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def record_generation(self, **kwargs: object) -> str | None:
        self.calls.append(dict(kwargs))
        return "record-1"


class TestTopicExplainerService(unittest.TestCase):
    def test_legacy_service_import_resolves_domain_class(self) -> None:
        from main_app.services.topic_explainer_service import TopicExplainerService as LegacyTopicExplainerService

        self.assertIs(LegacyTopicExplainerService, TopicExplainerService)

    def test_generate_persists_asset_history_record(self) -> None:
        fake_history = _FakeHistoryService()
        fake_llm = _FakeLLMService()
        service = TopicExplainerService(
            llm_service=fake_llm,  # type: ignore[arg-type]
            history_service=fake_history,  # type: ignore[arg-type]
        )
        settings = GroqSettings(
            api_key="key",
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=512,
        )

        content, cache_hit = service.generate(
            topic="CDC Pipeline",
            additional_instructions="Include architecture trade-offs.",
            settings=settings,
        )

        self.assertEqual(content, "Detailed explanation")
        self.assertTrue(cache_hit)
        self.assertEqual(len(fake_history.calls), 1)
        self.assertEqual(fake_history.calls[0]["asset_type"], "topic")
        self.assertEqual(fake_history.calls[0]["status"], "success")
        payload = fake_history.calls[0]["request_payload"]
        self.assertIsInstance(payload, dict)
        assert isinstance(payload, dict)
        self.assertFalse(payload.get("grounded_mode"))
        self.assertFalse(payload.get("require_citations"))

    def test_generate_with_grounding_includes_source_metadata(self) -> None:
        fake_history = _FakeHistoryService()
        fake_llm = _FakeLLMService()
        service = TopicExplainerService(
            llm_service=fake_llm,  # type: ignore[arg-type]
            history_service=fake_history,  # type: ignore[arg-type]
        )
        settings = GroqSettings(
            api_key="key",
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=512,
        )
        source_manifest = [{"source_id": "S1", "name": "doc.md", "char_count": 123, "truncated": False}]

        service.generate(
            topic="CDC Pipeline",
            additional_instructions="",
            grounding_context="[S1] doc.md\nCDC captures row-level changes.",
            source_manifest=source_manifest,
            require_citations=True,
            settings=settings,
        )

        payload = fake_history.calls[0]["request_payload"]
        self.assertIsInstance(payload, dict)
        assert isinstance(payload, dict)
        self.assertTrue(payload.get("grounded_mode"))
        self.assertTrue(payload.get("require_citations"))
        self.assertEqual(payload.get("sources"), source_manifest)
        self.assertEqual(len(fake_llm.calls), 1)
        messages = fake_llm.calls[0]["messages"]
        self.assertIsInstance(messages, list)
        assert isinstance(messages, list)
        full_prompt = "\n".join(str(item.get("content", "")) for item in messages if isinstance(item, dict))
        self.assertIn("[S1]", full_prompt)
        self.assertIn("Citation requirement", full_prompt)


if __name__ == "__main__":
    unittest.main()
