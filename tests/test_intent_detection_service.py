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
from main_app.parsers.intent_parser import IntentParser
from main_app.services.intent.intent_detection_service import IntentDetectionService
from main_app.services.intent.intent_requirement_spec import INTENT_ALIASES, INTENT_ORDER
from main_app.services.intent.intent_router_payload_utils import IntentRouterPayloadUtils
from main_app.services.intent.intent_router_text_utils import IntentRouterTextUtils


class _FakeLLMService:
    def __init__(self, response_text: str = '{"intents": []}', cache_hit: bool = False) -> None:
        self._response_text = response_text
        self._cache_hit = cache_hit
        self.call_count = 0

    def call(self, **_kwargs: object) -> tuple[str, bool]:
        self.call_count += 1
        return self._response_text, self._cache_hit


class TestIntentDetectionService(unittest.TestCase):
    def _settings(self, *, with_api: bool) -> GroqSettings:
        return GroqSettings(
            api_key="test-key" if with_api else "",
            model="llama-3.1-8b-instant" if with_api else "",
            temperature=0.2,
            max_tokens=256,
        )

    def _service(self, llm_service: _FakeLLMService) -> IntentDetectionService:
        return IntentDetectionService(
            llm_service=llm_service,
            parser=IntentParser(),
            payload_utils=IntentRouterPayloadUtils(intent_aliases=INTENT_ALIASES, intent_order=INTENT_ORDER),
            text_utils=IntentRouterTextUtils(),
        )

    def test_local_first_detects_intent_without_llm_call(self) -> None:
        llm = _FakeLLMService(response_text='{"intents":["quiz"]}')
        service = self._service(llm)

        result = service.detect_intent(
            message="Create a quiz on CDC pipeline.",
            settings=self._settings(with_api=False),
            mode=IntentDetectionService.MODE_LOCAL_FIRST,
        )

        self.assertEqual(result.intents, ["quiz"])
        self.assertIn("detected locally", (result.parse_note or "").lower())
        self.assertEqual(llm.call_count, 0)

    def test_missing_settings_and_no_local_intent_returns_error(self) -> None:
        llm = _FakeLLMService()
        service = self._service(llm)

        result = service.detect_intent(
            message="hello there",
            settings=self._settings(with_api=False),
            mode=IntentDetectionService.MODE_LOCAL_FIRST,
        )

        self.assertIsNone(result.intents)
        self.assertIn("missing", result.parse_error or "")
        self.assertEqual(llm.call_count, 0)

    def test_llm_driven_mode_uses_llm_intents(self) -> None:
        llm = _FakeLLMService(response_text='{"intents":["mindmap","quiz"]}', cache_hit=True)
        service = self._service(llm)

        result = service.detect_intent(
            message="Please help me",
            settings=self._settings(with_api=True),
            mode=IntentDetectionService.MODE_LLM_DRIVEN,
        )

        self.assertEqual(result.intents, ["mindmap", "quiz"])
        self.assertIn("llm-driven mode", (result.parse_note or "").lower())
        self.assertTrue(result.cache_hit)
        self.assertEqual(llm.call_count, 1)

    def test_llm_parse_failure_falls_back_to_user_message_match(self) -> None:
        llm = _FakeLLMService(response_text="### invalid ###")
        service = self._service(llm)

        result = service.detect_intent(
            message="Can you create a mind map for CDC pipeline?",
            settings=self._settings(with_api=True),
            mode=IntentDetectionService.MODE_LLM_DRIVEN,
        )

        self.assertEqual(result.intents, ["mindmap"])
        self.assertIn("fallback local intent matching", (result.parse_note or "").lower())
        self.assertEqual(llm.call_count, 1)

    def test_local_first_detects_video_intent(self) -> None:
        llm = _FakeLLMService(response_text='{"intents":["video"]}')
        service = self._service(llm)

        result = service.detect_intent(
            message="Create a narrated video on CDC pipeline with multiple voices.",
            settings=self._settings(with_api=False),
            mode=IntentDetectionService.MODE_LOCAL_FIRST,
        )

        self.assertEqual(result.intents, ["video"])
        self.assertEqual(llm.call_count, 0)


if __name__ == "__main__":
    unittest.main()
