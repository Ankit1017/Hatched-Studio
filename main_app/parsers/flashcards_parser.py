from __future__ import annotations

import json
from typing import Any

from main_app.models import GroqSettings
from main_app.parsers.json_utils import extract_json_text, repair_json_text_locally
from main_app.services.cached_llm_service import CachedLLMService


class FlashcardsParser:
    def __init__(self, llm_service: CachedLLMService) -> None:
        self._llm_service = llm_service

    def parse(
        self,
        raw_text: str,
        *,
        max_cards: int,
        settings: GroqSettings,
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        json_text = extract_json_text(raw_text)
        if not json_text:
            return None, "Model response did not contain a JSON object/array for flashcards.", None

        parse_errors: list[str] = []

        try:
            parsed = json.loads(json_text)
            normalized, schema_error = self._normalize_parsed(parsed, max_cards=max_cards)
            if schema_error:
                return None, schema_error, None
            return normalized, None, None
        except json.JSONDecodeError as exc:
            parse_errors.append(f"original parse: {exc}")

        locally_repaired_json = repair_json_text_locally(json_text)
        if locally_repaired_json != json_text:
            try:
                parsed = json.loads(locally_repaired_json)
                normalized, schema_error = self._normalize_parsed(parsed, max_cards=max_cards)
                if schema_error:
                    return None, schema_error, None
                return normalized, None, "Flashcards JSON had minor syntax issues and was auto-repaired locally."
            except json.JSONDecodeError as exc:
                parse_errors.append(f"local repair parse: {exc}")

        if settings.has_api_key() and settings.has_model():
            try:
                llm_repaired_text, repair_cache_hit = self._repair_json_with_llm(
                    raw_json_text=json_text,
                    settings=settings,
                )
                llm_json_text = extract_json_text(llm_repaired_text) or llm_repaired_text
                parsed = json.loads(llm_json_text)
                normalized, schema_error = self._normalize_parsed(parsed, max_cards=max_cards)
                if schema_error:
                    return None, schema_error, None
                repair_note = "Flashcards JSON was repaired using LLM."
                if repair_cache_hit:
                    repair_note += " Repair result was served from cache."
                return normalized, None, repair_note
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"LLM repair parse: {exc}")

        return None, "Could not parse flashcards JSON: " + " | ".join(parse_errors), None

    def _repair_json_with_llm(self, *, raw_json_text: str, settings: GroqSettings) -> tuple[str, bool]:
        repair_system_prompt = (
            "You repair malformed JSON. "
            "Return strictly valid JSON only. Do not explain, do not add markdown."
        )
        repair_user_prompt = (
            "The following flashcards JSON is invalid. Repair it while preserving structure and meaning.\n\n"
            f"{raw_json_text}"
        )
        repair_messages = [
            {"role": "system", "content": repair_system_prompt},
            {"role": "user", "content": repair_user_prompt},
        ]

        return self._llm_service.call(
            settings=settings,
            messages=repair_messages,
            task="flashcards_json_repair",
            label="Flashcards JSON Repair",
            topic="flashcards_json_repair",
            temperature_override=0.0,
            max_tokens_override=min(int(settings.max_tokens), 2048),
        )

    def _normalize_parsed(
        self,
        parsed: Any,
        *,
        max_cards: int,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if isinstance(parsed, dict):
            raw_cards = parsed.get("cards")
            topic = str(parsed.get("topic", "")).strip()
        elif isinstance(parsed, list):
            raw_cards = parsed
            topic = ""
        else:
            return None, "Flashcards JSON must be an object with `cards` or a direct array of cards."

        if not isinstance(raw_cards, list):
            return None, "Flashcards JSON missing `cards` list."

        normalized_cards: list[dict[str, str]] = []
        for card in raw_cards:
            if not isinstance(card, dict):
                continue

            question = card.get("question") or card.get("q") or card.get("prompt")
            short_answer = card.get("short_answer") or card.get("shortAnswer") or card.get("answer") or card.get("a")

            if question is None or short_answer is None:
                continue

            question_text = " ".join(str(question).split()).strip()
            answer_text = " ".join(str(short_answer).split()).strip()
            if not question_text or not answer_text:
                continue

            normalized_cards.append(
                {
                    "question": question_text,
                    "short_answer": answer_text,
                }
            )

        if not normalized_cards:
            return None, "No valid flashcards found in model response."

        max_cards = max(1, min(int(max_cards), 100))
        return {"topic": topic, "cards": normalized_cards[:max_cards]}, None
