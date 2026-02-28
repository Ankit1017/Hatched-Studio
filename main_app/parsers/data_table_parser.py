from __future__ import annotations

import json
from typing import Any

from main_app.models import GroqSettings
from main_app.parsers.json_utils import extract_json_text, repair_json_text_locally
from main_app.services.cached_llm_service import CachedLLMService


class DataTableParser:
    def __init__(self, llm_service: CachedLLMService) -> None:
        self._llm_service = llm_service

    def parse(
        self,
        raw_text: str,
        *,
        settings: GroqSettings,
        min_rows: int = 3,
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        json_text = extract_json_text(raw_text)
        if not json_text:
            return None, "Model response did not contain JSON for data table.", None

        parse_errors: list[str] = []

        try:
            parsed = json.loads(json_text)
            normalized, schema_error = self._normalize_parsed(parsed, min_rows=min_rows)
            if schema_error:
                return None, schema_error, None
            return normalized, None, None
        except json.JSONDecodeError as exc:
            parse_errors.append(f"original parse: {exc}")

        locally_repaired_json = repair_json_text_locally(json_text)
        if locally_repaired_json != json_text:
            try:
                parsed = json.loads(locally_repaired_json)
                normalized, schema_error = self._normalize_parsed(parsed, min_rows=min_rows)
                if schema_error:
                    return None, schema_error, None
                return normalized, None, "Data table JSON had minor syntax issues and was auto-repaired locally."
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
                normalized, schema_error = self._normalize_parsed(parsed, min_rows=min_rows)
                if schema_error:
                    return None, schema_error, None
                repair_note = "Data table JSON was repaired using LLM."
                if repair_cache_hit:
                    repair_note += " Repair result was served from cache."
                return normalized, None, repair_note
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"LLM repair parse: {exc}")

        return None, "Could not parse data table JSON: " + " | ".join(parse_errors), None

    def _repair_json_with_llm(self, *, raw_json_text: str, settings: GroqSettings) -> tuple[str, bool]:
        repair_system_prompt = (
            "You repair malformed JSON. "
            "Return strictly valid JSON only. Do not explain, do not add markdown."
        )
        repair_user_prompt = (
            "The following data table JSON is invalid. Repair it while preserving structure and meaning.\n\n"
            f"{raw_json_text}"
        )
        repair_messages = [
            {"role": "system", "content": repair_system_prompt},
            {"role": "user", "content": repair_user_prompt},
        ]

        return self._llm_service.call(
            settings=settings,
            messages=repair_messages,
            task="data_table_json_repair",
            label="Data Table JSON Repair",
            topic="data_table_json_repair",
            temperature_override=0.0,
            max_tokens_override=min(int(settings.max_tokens), 2048),
        )

    def _normalize_parsed(
        self,
        parsed: Any,
        *,
        min_rows: int,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(parsed, dict):
            return None, "Data table JSON must be an object with `columns` and `rows`."

        topic = str(parsed.get("topic", "")).strip()
        raw_rows = parsed.get("rows")
        if not isinstance(raw_rows, list):
            return None, "Data table JSON missing `rows` list."

        columns = self._normalize_columns(parsed.get("columns"), raw_rows)
        if len(columns) < 2:
            return None, "Need at least 2 table columns."

        normalized_rows: list[dict[str, str]] = []
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            cleaned_row: dict[str, str] = {}
            non_empty_count = 0
            for col in columns:
                value = self._pick_row_value(row, col)
                text = " ".join(str(value).split()).strip() if value is not None else ""
                cleaned_row[col] = text
                if text:
                    non_empty_count += 1
            if non_empty_count > 0:
                normalized_rows.append(cleaned_row)

        if len(normalized_rows) < min_rows:
            return None, f"Need at least {min_rows} valid rows in data table."

        return {
            "topic": topic,
            "columns": columns,
            "rows": normalized_rows,
        }, None

    @staticmethod
    def _normalize_columns(raw_columns: Any, raw_rows: list[Any]) -> list[str]:
        columns: list[str] = []

        if isinstance(raw_columns, list):
            for item in raw_columns:
                value = " ".join(str(item).split()).strip()
                if value and value not in columns:
                    columns.append(value)

        if not columns:
            for row in raw_rows:
                if not isinstance(row, dict):
                    continue
                for key in row.keys():
                    key_text = " ".join(str(key).split()).strip()
                    if key_text and key_text not in columns:
                        columns.append(key_text)

        if not columns:
            return []

        subtype_aliases = {"subtype", "type", "category", "sub-category", "sub type"}
        subtype_index = None
        for idx, col in enumerate(columns):
            if col.lower() in subtype_aliases:
                subtype_index = idx
                break
        if subtype_index is not None and subtype_index != 0:
            subtype_col = columns.pop(subtype_index)
            columns.insert(0, subtype_col)
        if subtype_index is None:
            columns.insert(0, "Subtype")

        return columns[:10]

    @staticmethod
    def _pick_row_value(row: dict[str, Any], column: str) -> Any:
        if column in row:
            return row[column]

        column_lower = column.lower()
        for key, value in row.items():
            if str(key).lower() == column_lower:
                return value

        if column == "Subtype":
            for alias in ["type", "category", "subtype", "sub-category", "sub type"]:
                for key, value in row.items():
                    if str(key).lower() == alias:
                        return value

        return None
