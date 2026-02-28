from __future__ import annotations

import json
from typing import Any

from main_app.parsers.json_utils import extract_json_text, repair_json_text_locally


class IntentParser:
    _ALLOWED_INTENTS = [
        "topic",
        "mindmap",
        "flashcards",
        "data table",
        "quiz",
        "slideshow",
        "video",
        "audio_overview",
        "report",
    ]

    _ALIASES = {
        "topic": "topic",
        "explain": "topic",
        "explanation": "topic",
        "describe": "topic",
        "description": "topic",
        "detailed description": "topic",
        "explainer": "topic",
        "mindmap": "mindmap",
        "mind map": "mindmap",
        "flashcard": "flashcards",
        "flashcards": "flashcards",
        "data table": "data table",
        "datatable": "data table",
        "data_table": "data table",
        "table": "data table",
        "quiz": "quiz",
        "slideshow": "slideshow",
        "slide show": "slideshow",
        "slides": "slideshow",
        "video": "video",
        "video builder": "video",
        "narrated video": "video",
        "video asset": "video",
        "video overview": "video",
        "narrated slideshow": "video",
        "audio_overview": "audio_overview",
        "audio overview": "audio_overview",
        "podcast": "audio_overview",
        "report": "report",
        "briefing doc": "report",
        "study guide": "report",
        "blog post": "report",
    }

    def parse(self, raw_text: str) -> tuple[list[str] | None, str | None, str | None]:
        json_text = extract_json_text(raw_text)
        if not json_text:
            inferred = self.fallback_from_text(raw_text)
            if inferred:
                return inferred, None, "Intent inferred from plain text response."
            return None, "Model response did not contain intent JSON.", None

        parse_errors: list[str] = []

        try:
            parsed = json.loads(json_text)
            intents = self._extract_intents(parsed)
            if intents:
                return intents, None, None
            if self._has_explicit_empty_intents(parsed):
                return [], None, "No asset intent detected."
            parse_errors.append("parsed JSON but no valid intents found")
        except json.JSONDecodeError as exc:
            parse_errors.append(f"original parse: {exc}")

        locally_repaired_json = repair_json_text_locally(json_text)
        if locally_repaired_json != json_text:
            try:
                parsed = json.loads(locally_repaired_json)
                intents = self._extract_intents(parsed)
                if intents:
                    return intents, None, "Intent JSON had minor syntax issues and was auto-repaired locally."
                if self._has_explicit_empty_intents(parsed):
                    return [], None, "No asset intent detected (repaired JSON)."
                parse_errors.append("local repair parse succeeded but no valid intents found")
            except json.JSONDecodeError as exc:
                parse_errors.append(f"local repair parse: {exc}")

        inferred = self.fallback_from_text(raw_text)
        if inferred:
            return inferred, None, "Intent inferred from fallback text matching."

        return None, "Could not parse intent JSON: " + " | ".join(parse_errors), None

    def fallback_from_text(self, text: str) -> list[str]:
        lowered = str(text).lower()
        found: list[str] = []
        for alias, canonical in self._ALIASES.items():
            if alias in lowered and canonical not in found:
                found.append(canonical)
        return found

    def fallback_from_user_message(self, message: str) -> list[str]:
        return self.fallback_from_text(message)

    def _extract_intents(self, parsed: Any) -> list[str]:
        raw_intents: list[Any] = []
        if isinstance(parsed, dict):
            raw_value = parsed.get("intents")
            if raw_value is None:
                raw_value = parsed.get("intent")
            if isinstance(raw_value, list):
                raw_intents = raw_value
            elif isinstance(raw_value, str):
                raw_intents = [part.strip() for part in raw_value.split(",")]
        elif isinstance(parsed, list):
            raw_intents = parsed
        elif isinstance(parsed, str):
            raw_intents = [part.strip() for part in parsed.split(",")]

        normalized: list[str] = []
        for item in raw_intents:
            canonical = self._normalize_intent(item)
            if canonical and canonical not in normalized:
                normalized.append(canonical)

        return normalized

    def _has_explicit_empty_intents(self, parsed: Any) -> bool:
        if not isinstance(parsed, dict):
            return False
        if "intents" in parsed and isinstance(parsed.get("intents"), list) and len(parsed.get("intents", [])) == 0:
            return True
        if "intent" in parsed and isinstance(parsed.get("intent"), str):
            return not str(parsed.get("intent", "")).strip()
        return False

    def _normalize_intent(self, value: Any) -> str | None:
        key = " ".join(str(value).strip().lower().split())
        if not key:
            return None
        if key in self._ALIASES:
            mapped = self._ALIASES[key]
            return mapped if mapped in self._ALLOWED_INTENTS else None
        return key if key in self._ALLOWED_INTENTS else None
