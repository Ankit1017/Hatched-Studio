from __future__ import annotations

import json
import re
from typing import Any

from main_app.models import GroqSettings
from main_app.parsers.json_utils import extract_json_text, repair_json_text_locally
from main_app.services.cached_llm_service import CachedLLMService


class AudioOverviewParser:
    def __init__(self, llm_service: CachedLLMService) -> None:
        self._llm_service = llm_service

    def parse(
        self,
        raw_text: str,
        *,
        settings: GroqSettings,
        min_speakers: int,
        max_speakers: int,
        min_turns: int,
        max_turns: int,
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        json_text = extract_json_text(raw_text)
        if not json_text:
            return None, "Model response did not contain audio overview JSON.", None

        parse_errors: list[str] = []

        try:
            parsed = json.loads(json_text)
            normalized, schema_error = self._normalize_payload(
                parsed,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
                min_turns=min_turns,
                max_turns=max_turns,
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
                normalized, schema_error = self._normalize_payload(
                    parsed,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers,
                    min_turns=min_turns,
                    max_turns=max_turns,
                )
                if schema_error:
                    return None, schema_error, None
                return normalized, None, "Audio overview JSON had minor syntax issues and was auto-repaired locally."
            except json.JSONDecodeError as exc:
                parse_errors.append(f"local repair parse: {exc}")

        if settings.has_api_key() and settings.has_model():
            try:
                repair_seed = locally_repaired_json if locally_repaired_json != json_text else json_text
                llm_repaired_text, repair_cache_hit = self._repair_json_with_llm(
                    raw_json_text=repair_seed,
                    settings=settings,
                )
                llm_json_text = extract_json_text(llm_repaired_text) or llm_repaired_text
                try:
                    parsed = json.loads(llm_json_text)
                    normalized, schema_error = self._normalize_payload(
                        parsed,
                        min_speakers=min_speakers,
                        max_speakers=max_speakers,
                        min_turns=min_turns,
                        max_turns=max_turns,
                    )
                    if schema_error:
                        return None, schema_error, None
                    repair_note = "Audio overview JSON was repaired using LLM."
                    if repair_cache_hit:
                        repair_note += " Repair result was served from cache."
                    return normalized, None, repair_note
                except json.JSONDecodeError:
                    final_local_repair = repair_json_text_locally(llm_json_text)
                    parsed = json.loads(final_local_repair)
                    normalized, schema_error = self._normalize_payload(
                        parsed,
                        min_speakers=min_speakers,
                        max_speakers=max_speakers,
                        min_turns=min_turns,
                        max_turns=max_turns,
                    )
                    if schema_error:
                        return None, schema_error, None
                    repair_note = "Audio overview JSON was repaired using LLM and final local sanitization."
                    if repair_cache_hit:
                        repair_note += " Repair result was served from cache."
                    return normalized, None, repair_note
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"LLM repair parse: {exc}")

        return None, "Could not parse audio overview JSON: " + " | ".join(parse_errors), None

    def _repair_json_with_llm(
        self,
        *,
        raw_json_text: str,
        settings: GroqSettings,
    ) -> tuple[str, bool]:
        repair_system_prompt = (
            "You repair malformed JSON. "
            "Return strictly valid JSON only. Do not explain, do not add markdown."
        )
        repair_user_prompt = (
            "The following JSON is invalid. Repair it while preserving structure and meaning.\n\n"
            f"{raw_json_text}"
        )
        repair_messages = [
            {"role": "system", "content": repair_system_prompt},
            {"role": "user", "content": repair_user_prompt},
        ]

        return self._llm_service.call(
            settings=settings,
            messages=repair_messages,
            task="audio_overview_json_repair",
            label="Audio Overview JSON Repair",
            topic="audio_overview_json_repair",
            temperature_override=0.0,
            max_tokens_override=min(int(settings.max_tokens), 2048),
        )

    def _normalize_payload(
        self,
        parsed: Any,
        *,
        min_speakers: int,
        max_speakers: int,
        min_turns: int,
        max_turns: int,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(parsed, dict):
            return None, "Audio overview JSON must be an object with speakers and dialogue."

        topic = " ".join(str(parsed.get("topic", "")).split()).strip()
        title = " ".join(str(parsed.get("title", "")).split()).strip()
        if not title:
            title = f"{topic} Audio Overview" if topic else "Audio Overview"

        speakers, speaker_error = self._normalize_speakers(
            parsed.get("speakers") or parsed.get("participants") or parsed.get("hosts"),
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
        if speaker_error:
            return None, speaker_error

        dialogue, dialogue_error = self._normalize_dialogue(
            parsed.get("dialogue") or parsed.get("conversation") or parsed.get("turns"),
            known_speakers=[speaker["name"] for speaker in speakers],
            min_turns=min_turns,
            max_turns=max_turns,
        )
        if dialogue_error:
            return None, dialogue_error

        summary = " ".join(str(parsed.get("summary", "")).split()).strip()

        return {
            "topic": topic,
            "title": title,
            "speakers": speakers,
            "dialogue": dialogue,
            "summary": summary,
        }, None

    @staticmethod
    def _normalize_speakers(
        raw_speakers: Any,
        *,
        min_speakers: int,
        max_speakers: int,
    ) -> tuple[list[dict[str, str]], str | None]:
        if not isinstance(raw_speakers, list):
            return [], "Audio overview JSON missing `speakers` list."

        speakers: list[dict[str, str]] = []
        seen_names: set[str] = set()

        for item in raw_speakers:
            if isinstance(item, str):
                name = " ".join(item.split()).strip()
                role = ""
            elif isinstance(item, dict):
                raw_name = item.get("name") or item.get("speaker") or item.get("host") or item.get("participant")
                raw_role = item.get("role") or item.get("persona") or item.get("style") or ""
                name = " ".join(str(raw_name).split()).strip() if raw_name is not None else ""
                role = " ".join(str(raw_role).split()).strip() if raw_role is not None else ""
            else:
                continue

            if not name:
                continue
            normalized_key = name.lower()
            if normalized_key in seen_names:
                continue

            seen_names.add(normalized_key)
            speakers.append({"name": name, "role": role})
            if len(speakers) >= max_speakers:
                break

        if len(speakers) < min_speakers:
            return [], f"Need at least {min_speakers} speakers in audio overview."

        return speakers, None

    @staticmethod
    def _normalize_dialogue(
        raw_dialogue: Any,
        *,
        known_speakers: list[str],
        min_turns: int,
        max_turns: int,
    ) -> tuple[list[dict[str, str]], str | None]:
        if not isinstance(raw_dialogue, list):
            return [], "Audio overview JSON missing `dialogue` list."

        known_map = {name.lower(): name for name in known_speakers}
        dialogue: list[dict[str, str]] = []

        for item in raw_dialogue:
            speaker = ""
            text = ""
            if isinstance(item, dict):
                raw_speaker = item.get("speaker") or item.get("name") or item.get("host")
                raw_text = item.get("text") or item.get("line") or item.get("message")
                speaker = " ".join(str(raw_speaker).split()).strip() if raw_speaker is not None else ""
                text = " ".join(str(raw_text).split()).strip() if raw_text is not None else ""
            elif isinstance(item, str):
                text_line = item.strip()
                match = re.match(r"^\s*([^:]{1,80})\s*:\s*(.+)$", text_line)
                if match:
                    speaker = " ".join(match.group(1).split()).strip()
                    text = " ".join(match.group(2).split()).strip()
                else:
                    text = " ".join(text_line.split()).strip()

            if not text:
                continue

            if not speaker:
                speaker = known_speakers[len(dialogue) % len(known_speakers)]
            else:
                speaker = known_map.get(speaker.lower(), speaker)

            dialogue.append({"speaker": speaker, "text": text})
            if len(dialogue) >= max_turns:
                break

        if len(dialogue) < min_turns:
            return [], f"Need at least {min_turns} dialogue turns in audio overview."

        return dialogue, None
