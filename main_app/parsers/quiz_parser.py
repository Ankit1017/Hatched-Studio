from __future__ import annotations

import json
from typing import Any

from main_app.models import GroqSettings
from main_app.parsers.json_utils import extract_json_text, repair_json_text_locally
from main_app.services.cached_llm_service import CachedLLMService


class QuizParser:
    def __init__(self, llm_service: CachedLLMService) -> None:
        self._llm_service = llm_service

    def parse(
        self,
        raw_text: str,
        *,
        settings: GroqSettings,
        min_questions: int,
        max_questions: int,
        repair_use_cache: bool,
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        json_text = extract_json_text(raw_text)
        if not json_text:
            return None, "Model response did not contain quiz JSON.", None

        parse_errors: list[str] = []

        try:
            parsed = json.loads(json_text)
            normalized, schema_error = self._normalize_parsed(
                parsed,
                min_questions=min_questions,
                max_questions=max_questions,
            )
            if schema_error:
                return None, schema_error, None
            return normalized, None, None
        except json.JSONDecodeError as exc:
            parse_errors.append(f"original parse: {exc}")

        locally_repaired_json = repair_json_text_locally(json_text)
        if locally_repaired_json != json_text:
            try:
                parsed = json.loads(locally_repaired_json)
                normalized, schema_error = self._normalize_parsed(
                    parsed,
                    min_questions=min_questions,
                    max_questions=max_questions,
                )
                if schema_error:
                    return None, schema_error, None
                return normalized, None, "Quiz JSON had minor syntax issues and was auto-repaired locally."
            except json.JSONDecodeError as exc:
                parse_errors.append(f"local repair parse: {exc}")

        if settings.has_api_key() and settings.has_model():
            try:
                llm_repaired_text, repair_cache_hit = self._repair_json_with_llm(
                    raw_json_text=json_text,
                    settings=settings,
                    use_cache=repair_use_cache,
                )
                llm_json_text = extract_json_text(llm_repaired_text) or llm_repaired_text
                parsed = json.loads(llm_json_text)
                normalized, schema_error = self._normalize_parsed(
                    parsed,
                    min_questions=min_questions,
                    max_questions=max_questions,
                )
                if schema_error:
                    return None, schema_error, None
                repair_note = "Quiz JSON was repaired using LLM."
                if repair_cache_hit:
                    repair_note += " Repair result was served from cache."
                return normalized, None, repair_note
            except (
                AttributeError,
                OSError,
                RuntimeError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                parse_errors.append(f"LLM repair parse: {exc}")

        return None, "Could not parse quiz JSON: " + " | ".join(parse_errors), None

    def normalize_payload(
        self,
        payload: Any,
        *,
        min_questions: int = 1,
        max_questions: int = 100,
    ) -> tuple[dict[str, Any] | None, str | None]:
        return self._normalize_parsed(
            payload,
            min_questions=min_questions,
            max_questions=max_questions,
        )

    def _repair_json_with_llm(
        self,
        *,
        raw_json_text: str,
        settings: GroqSettings,
        use_cache: bool,
    ) -> tuple[str, bool]:
        repair_system_prompt = (
            "You repair malformed JSON. "
            "Return strictly valid JSON only. Do not explain, do not add markdown."
        )
        repair_user_prompt = (
            "The following quiz JSON is invalid. Repair it while preserving structure and meaning.\n\n"
            f"{raw_json_text}"
        )
        repair_messages = [
            {"role": "system", "content": repair_system_prompt},
            {"role": "user", "content": repair_user_prompt},
        ]

        return self._llm_service.call(
            settings=settings,
            messages=repair_messages,
            task="quiz_json_repair",
            label="Quiz JSON Repair",
            topic="quiz_json_repair",
            temperature_override=0.0,
            max_tokens_override=min(int(settings.max_tokens), 2048),
            use_cache=use_cache,
        )

    def _normalize_parsed(
        self,
        parsed: Any,
        *,
        min_questions: int,
        max_questions: int,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(parsed, dict):
            return None, "Quiz JSON must be an object with a `questions` list."

        topic = str(parsed.get("topic", "")).strip()
        raw_questions = parsed.get("questions")
        if not isinstance(raw_questions, list):
            return None, "Quiz JSON missing `questions` list."

        normalized_questions: list[dict[str, Any]] = []
        seen_questions: set[str] = set()

        for item in raw_questions:
            normalized = self._normalize_question(item)
            if normalized is None:
                continue
            key = normalized["question"].lower()
            if key in seen_questions:
                continue
            seen_questions.add(key)
            normalized_questions.append(normalized)

        if len(normalized_questions) < min_questions:
            return None, f"Need at least {min_questions} valid quiz questions."

        return {
            "topic": topic,
            "questions": normalized_questions[:max_questions],
        }, None

    def _normalize_question(self, raw: Any) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None

        question = raw.get("question") or raw.get("prompt") or raw.get("q")
        if question is None:
            return None
        question_text = " ".join(str(question).split()).strip()
        if not question_text:
            return None

        raw_options = raw.get("options") or raw.get("choices")
        if not isinstance(raw_options, list):
            return None

        options: list[str] = []
        for opt in raw_options:
            if isinstance(opt, dict):
                opt = opt.get("text") or opt.get("option")
            if opt is None:
                continue
            opt_text = " ".join(str(opt).split()).strip()
            if opt_text:
                options.append(opt_text)

        if len(options) < 4:
            return None
        options = options[:6]

        correct_index = self._extract_correct_index(raw, options)
        if correct_index is None or correct_index < 0 or correct_index >= len(options):
            return None

        return {
            "question": question_text,
            "options": options,
            "correct_index": int(correct_index),
        }

    @staticmethod
    def _extract_correct_index(raw: dict[str, Any], options: list[str]) -> int | None:
        for key in ["correct_option_index", "correct_index", "answer_index"]:
            value = raw.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.strip().isdigit():
                return int(value.strip())

        for key in ["correct_answer", "correct_option", "answer"]:
            value = raw.get(key)
            if not isinstance(value, str):
                continue
            text = value.strip()
            if not text:
                continue

            # Accept letters like A/B/C/D.
            if len(text) == 1 and text.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                return ord(text.upper()) - ord("A")

            text_lower = text.lower()
            for idx, option in enumerate(options):
                if option.lower() == text_lower:
                    return idx

        return None
