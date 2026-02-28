from __future__ import annotations

from main_app.models import GroqSettings, IntentDetectionResult
from main_app.parsers.intent_parser import IntentParser
from main_app.services.cached_llm_service import CachedLLMService
from main_app.services.intent.intent_router_payload_utils import IntentRouterPayloadUtils
from main_app.services.intent.intent_router_text_utils import IntentRouterTextUtils


class IntentDetectionService:
    MODE_LOCAL_FIRST = "local_first"
    MODE_LLM_DRIVEN = "llm_driven"

    def __init__(
        self,
        *,
        llm_service: CachedLLMService,
        parser: IntentParser,
        payload_utils: IntentRouterPayloadUtils,
        text_utils: IntentRouterTextUtils,
    ) -> None:
        self._llm_service = llm_service
        self._parser = parser
        self._payload_utils = payload_utils
        self._text_utils = text_utils

    def detect_intent(
        self,
        *,
        message: str,
        settings: GroqSettings,
        mode: str = MODE_LOCAL_FIRST,
    ) -> IntentDetectionResult:
        normalized_mode = mode if mode in {self.MODE_LOCAL_FIRST, self.MODE_LLM_DRIVEN} else self.MODE_LOCAL_FIRST
        local_intents = self._payload_utils.ordered_intents(self._parser.fallback_from_user_message(message))

        if normalized_mode == self.MODE_LOCAL_FIRST and local_intents:
            return IntentDetectionResult(
                raw_text="",
                intents=local_intents,
                parse_error=None,
                parse_note="Intent detected locally from user message.",
                cache_hit=False,
            )

        if not settings.has_api_key() or not settings.has_model():
            if local_intents:
                return IntentDetectionResult(
                    raw_text="",
                    intents=local_intents,
                    parse_error=None,
                    parse_note="Groq settings missing; fallback local intent detection used.",
                    cache_hit=False,
                )
            return IntentDetectionResult(
                raw_text="",
                intents=None,
                parse_error="Could not detect intent. Groq settings are missing and local matcher found nothing.",
                parse_note=None,
                cache_hit=False,
            )

        system_prompt = (
            "You are an intent classifier for an educational knowledge app. "
            "Return strict JSON only."
        )
        user_prompt = (
            "Classify the user message into one or more intents from this exact list:\n"
            '["topic", "mindmap", "flashcards", "data table", "quiz", "slideshow", "video", "audio_overview", "report"]\n\n'
            "Rules:\n"
            "- Return only intents from the list above.\n"
            "- If multiple intents are present, include all relevant intents.\n"
            "- If the message is general conversation (greeting, thanks, chitchat, clarification without asset request), return an empty list.\n\n"
            "Return JSON only in this schema:\n"
            '{ "intents": ["topic"] }\n\n'
            f"User message:\n{message.strip()}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw_text, cache_hit = self._llm_service.call(
            settings=settings,
            messages=messages,
            task="intent_detect",
            label=f"Intent Detect: {message.strip()[:72]}",
            topic=message.strip()[:120],
        )

        intents, parse_error, parse_note = self._parser.parse(raw_text)
        if intents is not None:
            if intents and normalized_mode == self.MODE_LLM_DRIVEN:
                parse_note = (
                    f"{parse_note} Intent detected by LLM-driven mode.".strip()
                    if parse_note
                    else "Intent detected by LLM-driven mode."
                )
            if not intents:
                parse_note = (
                    f"{parse_note} No asset intent detected."
                    if parse_note
                    else "No asset intent detected."
                )
            return IntentDetectionResult(
                raw_text=raw_text,
                intents=intents,
                parse_error=None,
                parse_note=parse_note,
                cache_hit=cache_hit,
            )

        fallback_intents = self._parser.fallback_from_user_message(message)
        if fallback_intents:
            fallback_note = "LLM output parsing failed; fallback local intent matching was used."
            parse_note = f"{parse_note} {fallback_note}".strip() if parse_note else fallback_note
            return IntentDetectionResult(
                raw_text=raw_text,
                intents=fallback_intents,
                parse_error=None,
                parse_note=parse_note,
                cache_hit=cache_hit,
            )

        return IntentDetectionResult(
            raw_text=raw_text,
            intents=None,
            parse_error=parse_error or "Could not detect intent.",
            parse_note=parse_note,
            cache_hit=cache_hit,
        )
