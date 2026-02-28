from __future__ import annotations

from main_app.models import GroqSettings
from main_app.services.cached_llm_service import CachedLLMService
from main_app.services.intent.intent_router_payload_utils import IntentRouterPayloadUtils
from main_app.services.intent.intent_router_text_utils import IntentRouterTextUtils


class IntentTopicService:
    def __init__(
        self,
        *,
        llm_service: CachedLLMService,
        payload_utils: IntentRouterPayloadUtils,
        text_utils: IntentRouterTextUtils,
    ) -> None:
        self._llm_service = llm_service
        self._payload_utils = payload_utils
        self._text_utils = text_utils

    def extract_topic_from_message(
        self,
        *,
        message: str,
        settings: GroqSettings,
    ) -> tuple[str | None, str | None, str | None, bool]:
        local_topic = self._text_utils.fallback_topic_from_message(message)
        if local_topic:
            return local_topic, "Topic extracted locally from user reply.", None, False

        if not settings.has_api_key() or not settings.has_model():
            return None, None, "Could not infer topic locally. Please provide topic more explicitly.", False

        system_prompt = "Extract only the topic from user text. Return strict JSON only."
        user_prompt = (
            "Return JSON in this schema:\n"
            '{ "topic": "clean topic or empty string" }\n\n'
            "Rules:\n"
            "- Extract only the central topic.\n"
            "- Keep it concise.\n"
            "- Return JSON only.\n\n"
            f"User message:\n{message.strip()}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        raw_text, cache_hit = self._llm_service.call(
            settings=settings,
            messages=messages,
            task="intent_extract_topic",
            label=f"Intent Topic Extract: {message.strip()[:72]}",
            topic=message.strip()[:120],
        )
        parsed_json, parse_error = self._payload_utils.parse_json_object(raw_text)
        if parse_error:
            return None, None, f"Topic extraction parse failed: {parse_error}", cache_hit

        topic = self._text_utils.clean_text(parsed_json.get("topic", ""))
        if not self.is_valid_topic(topic):
            return None, None, "Could not infer topic. Please provide topic clearly.", cache_hit

        return topic, "Topic extracted by LLM from user reply.", None, cache_hit

    def infer_topic_from_message_local(self, message: str) -> str:
        return self._text_utils.fallback_topic_from_message(message)

    @staticmethod
    def is_valid_topic(topic: str) -> bool:
        return IntentRouterTextUtils.is_valid_topic(topic)

    @staticmethod
    def is_followup_reference_message(message: str) -> bool:
        return IntentRouterTextUtils.is_followup_reference_message(message)
