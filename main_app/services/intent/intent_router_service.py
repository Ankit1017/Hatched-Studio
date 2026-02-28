from __future__ import annotations

from main_app.contracts import (
    ChatHistory,
    IntentPayload,
    IntentPayloadMap,
    RequirementFieldSpec,
)
from main_app.models import GroqSettings, IntentDetectionResult
from main_app.parsers.intent_parser import IntentParser
from main_app.services.cached_llm_service import CachedLLMService
from main_app.services.intent.intent_conversation_service import IntentConversationService
from main_app.services.intent.intent_detection_service import IntentDetectionService
from main_app.services.intent.intent_requirement_service import IntentRequirementService
from main_app.services.intent.intent_requirement_spec import INTENT_ALIASES, INTENT_ORDER, REQUIREMENT_SPEC
from main_app.services.intent.intent_router_payload_utils import IntentRouterPayloadUtils
from main_app.services.intent.intent_router_text_utils import IntentRouterTextUtils
from main_app.services.intent.intent_topic_service import IntentTopicService


class IntentRouterService:
    MODE_LOCAL_FIRST = IntentDetectionService.MODE_LOCAL_FIRST
    MODE_LLM_DRIVEN = IntentDetectionService.MODE_LLM_DRIVEN
    _INTENT_ORDER = INTENT_ORDER
    _INTENT_ALIASES = INTENT_ALIASES
    _REQUIREMENT_SPEC = REQUIREMENT_SPEC

    def __init__(
        self,
        llm_service: CachedLLMService,
        parser: IntentParser,
        *,
        detection_service: IntentDetectionService | None = None,
        requirement_service: IntentRequirementService | None = None,
        topic_service: IntentTopicService | None = None,
        conversation_service: IntentConversationService | None = None,
    ) -> None:
        text_utils = IntentRouterTextUtils()
        payload_utils = IntentRouterPayloadUtils(
            intent_aliases=self._INTENT_ALIASES,
            intent_order=self._INTENT_ORDER,
        )

        self._detection_service = detection_service or IntentDetectionService(
            llm_service=llm_service,
            parser=parser,
            payload_utils=payload_utils,
            text_utils=text_utils,
        )
        self._requirement_service = requirement_service or IntentRequirementService(
            llm_service=llm_service,
            payload_utils=payload_utils,
            text_utils=text_utils,
            requirement_spec=self._REQUIREMENT_SPEC,
        )
        self._topic_service = topic_service or IntentTopicService(
            llm_service=llm_service,
            payload_utils=payload_utils,
            text_utils=text_utils,
        )
        self._conversation_service = conversation_service or IntentConversationService(
            llm_service=llm_service,
            payload_utils=payload_utils,
            text_utils=text_utils,
            requirement_spec=self._REQUIREMENT_SPEC,
        )

    def detect_intent(
        self,
        *,
        message: str,
        settings: GroqSettings,
        mode: str = MODE_LOCAL_FIRST,
    ) -> IntentDetectionResult:
        return self._detection_service.detect_intent(
            message=message,
            settings=settings,
            mode=mode,
        )

    def generate_general_chat_reply(
        self,
        *,
        message: str,
        history: ChatHistory,
        active_topic: str,
        settings: GroqSettings,
    ) -> tuple[str, bool]:
        return self._conversation_service.generate_general_chat_reply(
            message=message,
            history=history,
            active_topic=active_topic,
            settings=settings,
        )

    def suggest_next_asks(
        self,
        *,
        last_user_message: str,
        history: ChatHistory,
        active_topic: str,
        settings: GroqSettings,
    ) -> tuple[list[str], list[str], bool, str | None]:
        return self._conversation_service.suggest_next_asks(
            last_user_message=last_user_message,
            history=history,
            active_topic=active_topic,
            settings=settings,
        )

    def prepare_requirements(
        self,
        *,
        message: str,
        intents: list[str],
        settings: GroqSettings,
        mode: str = MODE_LOCAL_FIRST,
    ) -> tuple[IntentPayloadMap, str | None, bool]:
        return self._requirement_service.prepare_requirements(
            message=message,
            intents=intents,
            settings=settings,
            mode=mode,
        )

    def evaluate_requirements(self, *, intent: str, payload: IntentPayload) -> tuple[list[str], list[str]]:
        return self._requirement_service.evaluate_requirements(intent=intent, payload=payload)

    def optional_field_definitions(self, intent: str) -> dict[str, RequirementFieldSpec]:
        return self._requirement_service.optional_field_definitions(intent)

    def apply_default_optionals(
        self,
        *,
        intent: str,
        payload: IntentPayload,
        missing_optional: list[str],
    ) -> IntentPayload:
        return self._requirement_service.apply_default_optionals(
            intent=intent,
            payload=payload,
            missing_optional=missing_optional,
        )

    def apply_user_optionals(
        self,
        *,
        intent: str,
        payload: IntentPayload,
        user_values: IntentPayload,
        missing_optional: list[str],
    ) -> IntentPayload:
        return self._requirement_service.apply_user_optionals(
            intent=intent,
            payload=payload,
            user_values=user_values,
            missing_optional=missing_optional,
        )

    def fill_optional_with_llm(
        self,
        *,
        intent: str,
        message: str,
        payload: IntentPayload,
        missing_optional: list[str],
        settings: GroqSettings,
    ) -> tuple[IntentPayload, str | None, str | None, bool]:
        return self._requirement_service.fill_optional_with_llm(
            intent=intent,
            message=message,
            payload=payload,
            missing_optional=missing_optional,
            settings=settings,
        )

    def extract_topic_from_message(
        self,
        *,
        message: str,
        settings: GroqSettings,
    ) -> tuple[str | None, str | None, str | None, bool]:
        return self._topic_service.extract_topic_from_message(
            message=message,
            settings=settings,
        )

    def infer_topic_from_message_local(self, message: str) -> str:
        return self._topic_service.infer_topic_from_message_local(message)

    @staticmethod
    def is_valid_topic(topic: str) -> bool:
        return IntentTopicService.is_valid_topic(topic)

    @staticmethod
    def is_followup_reference_message(message: str) -> bool:
        return IntentTopicService.is_followup_reference_message(message)
