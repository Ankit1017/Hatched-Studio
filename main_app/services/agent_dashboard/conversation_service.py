from __future__ import annotations

from main_app.contracts import ChatHistory
from main_app.models import GroqSettings
from main_app.services.intent import IntentRouterService


class AgentDashboardConversationService:
    def __init__(self, intent_router: IntentRouterService) -> None:
        self._intent_router = intent_router

    def generate_general_chat_reply(
        self,
        *,
        message: str,
        history: ChatHistory,
        active_topic: str,
        settings: GroqSettings,
    ) -> tuple[str | None, list[str], str | None, bool, str]:
        notes: list[str] = ["Handled as normal chat (no asset intent detected)."]
        candidate_topic = self._intent_router.infer_topic_from_message_local(message)
        if not self._intent_router.is_valid_topic(candidate_topic):
            candidate_topic = ""
        topic_cache_hit = True

        if not candidate_topic:
            extracted_topic, topic_note, _, topic_cache_hit = self._intent_router.extract_topic_from_message(
                message=message,
                settings=settings,
            )
            if topic_note:
                notes.append(topic_note)
            if extracted_topic and self._intent_router.is_valid_topic(extracted_topic):
                candidate_topic = extracted_topic

        if not settings.has_api_key() or not settings.has_model():
            return (
                None,
                notes,
                "No asset intent detected. Please set Groq API key and model for normal chat replies.",
                False,
                candidate_topic,
            )

        reply_text, cache_hit = self._intent_router.generate_general_chat_reply(
            message=message,
            history=history,
            active_topic=active_topic,
            settings=settings,
        )
        return reply_text, notes, None, (cache_hit and topic_cache_hit), candidate_topic

    def generate_followup_suggestions(
        self,
        *,
        last_user_message: str,
        history: ChatHistory,
        active_topic: str,
        settings: GroqSettings,
    ) -> tuple[list[str], list[str], str | None, bool]:
        if not settings.has_api_key() or not settings.has_model():
            return [], [], "Follow-up suggestion skipped: Groq API key/model not configured.", True

        suggestions, intent_targets, cache_hit, error = self._intent_router.suggest_next_asks(
            last_user_message=last_user_message,
            history=history,
            active_topic=active_topic,
            settings=settings,
        )
        if error:
            return suggestions, intent_targets, error, cache_hit
        return suggestions, intent_targets, None, cache_hit
