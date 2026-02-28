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
from main_app.services.intent.intent_requirement_spec import INTENT_ALIASES, INTENT_ORDER
from main_app.services.intent.intent_router_payload_utils import IntentRouterPayloadUtils
from main_app.services.intent.intent_router_text_utils import IntentRouterTextUtils
from main_app.services.intent.intent_topic_service import IntentTopicService


class _FakeLLMService:
    def __init__(self, response_text: str = '{"topic": ""}', cache_hit: bool = False) -> None:
        self._response_text = response_text
        self._cache_hit = cache_hit
        self.call_count = 0

    def call(self, **_kwargs: object) -> tuple[str, bool]:
        self.call_count += 1
        return self._response_text, self._cache_hit


class TestIntentTopicService(unittest.TestCase):
    def _settings(self, *, with_api: bool) -> GroqSettings:
        return GroqSettings(
            api_key="test-key" if with_api else "",
            model="llama-3.1-8b-instant" if with_api else "",
            temperature=0.2,
            max_tokens=256,
        )

    def _service(self, llm_service: _FakeLLMService) -> IntentTopicService:
        return IntentTopicService(
            llm_service=llm_service,
            payload_utils=IntentRouterPayloadUtils(intent_aliases=INTENT_ALIASES, intent_order=INTENT_ORDER),
            text_utils=IntentRouterTextUtils(),
        )

    def test_extract_topic_locally_without_llm(self) -> None:
        llm = _FakeLLMService()
        service = self._service(llm)

        topic, note, error, cache_hit = service.extract_topic_from_message(
            message="Explain me about CDC Pipeline deeply.",
            settings=self._settings(with_api=False),
        )

        self.assertEqual(topic, "CDC Pipeline")
        self.assertIn("locally", note or "")
        self.assertIsNone(error)
        self.assertFalse(cache_hit)
        self.assertEqual(llm.call_count, 0)

    def test_missing_settings_returns_topic_error_when_local_fails(self) -> None:
        llm = _FakeLLMService()
        service = self._service(llm)

        topic, note, error, cache_hit = service.extract_topic_from_message(
            message="please explain it",
            settings=self._settings(with_api=False),
        )

        self.assertIsNone(topic)
        self.assertIsNone(note)
        self.assertIn("could not infer topic locally", (error or "").lower())
        self.assertFalse(cache_hit)
        self.assertEqual(llm.call_count, 0)

    def test_llm_success_topic_extraction(self) -> None:
        llm = _FakeLLMService(response_text='{"topic":"Segment Trees"}', cache_hit=True)
        service = self._service(llm)

        topic, note, error, cache_hit = service.extract_topic_from_message(
            message="Can you explain this?",
            settings=self._settings(with_api=True),
        )

        self.assertEqual(topic, "Segment Trees")
        self.assertIn("llm", (note or "").lower())
        self.assertIsNone(error)
        self.assertTrue(cache_hit)
        self.assertEqual(llm.call_count, 1)

    def test_llm_parse_error_returns_error(self) -> None:
        llm = _FakeLLMService(response_text="not json")
        service = self._service(llm)

        topic, note, error, cache_hit = service.extract_topic_from_message(
            message="Can you explain this?",
            settings=self._settings(with_api=True),
        )

        self.assertIsNone(topic)
        self.assertIsNone(note)
        self.assertIn("parse failed", (error or "").lower())
        self.assertFalse(cache_hit)
        self.assertEqual(llm.call_count, 1)


if __name__ == "__main__":
    unittest.main()
