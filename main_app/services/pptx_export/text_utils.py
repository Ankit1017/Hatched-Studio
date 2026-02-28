from __future__ import annotations

import re
from typing import Any

from main_app.services.text_sanitizer import sanitize_text

def normalize_text(value: Any) -> str:
    return sanitize_text(value, keep_citations=True)


def split_line_for_slide(*, line: str, max_chars: int) -> list[str]:
    if len(line) <= max_chars:
        return [line]
    wrapped: list[str] = []
    remaining = line
    while len(remaining) > max_chars:
        split_at = max_chars
        split_candidates = [
            remaining.rfind(token, 0, max_chars)
            for token in (" ", ",", ")", "(", ".", ";", "=")
        ]
        best_candidate = max(split_candidates)
        if best_candidate >= max_chars // 2:
            split_at = best_candidate + 1
        wrapped.append(remaining[:split_at].rstrip() + " \\")
        remaining = "  " + remaining[split_at:].lstrip()
    wrapped.append(remaining)
    return wrapped


def trim_code_for_slide(code_snippet: str) -> list[str]:
    lines = [line.rstrip().replace("\t", "    ") for line in str(code_snippet).splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    trimmed: list[str] = []
    max_lines = 22
    max_chars = 78
    truncated = False
    for line in lines:
        segments = split_line_for_slide(line=line, max_chars=max_chars)
        for segment in segments:
            if len(trimmed) >= max_lines:
                truncated = True
                break
            trimmed.append(segment)
        if truncated:
            break
    if truncated and trimmed:
        trimmed[-1] = (trimmed[-1][: max_chars - 3] + "...") if len(trimmed[-1]) > max_chars - 3 else (trimmed[-1] + "...")
    return trimmed or ["# code snippet unavailable"]


def prepare_code_payload(*, code_snippet: str, code_language: str) -> tuple[str, str]:
    raw = sanitize_text(code_snippet or "", keep_citations=True, preserve_newlines=True).replace("\r\n", "\n").replace("\r", "\n")
    language = normalize_text(code_language).lower()
    detected_language = ""

    fenced_match = re.search(
        r"```([a-zA-Z0-9_+-]*)\s*\n([\s\S]*?)```",
        raw,
        flags=re.IGNORECASE,
    )
    if fenced_match:
        detected_language = normalize_text(fenced_match.group(1)).lower()
        raw = fenced_match.group(2)
    else:
        stripped = raw.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            raw = stripped[3:-3].strip("\n")
            first_newline = raw.find("\n")
            if first_newline > 0:
                possible_language = raw[:first_newline].strip()
                if re.fullmatch(r"[a-zA-Z0-9_+-]+", possible_language):
                    if not detected_language:
                        detected_language = possible_language.lower()
                    raw = raw[first_newline + 1 :]

    cleaned_lines: list[str] = []
    for line in raw.split("\n"):
        if line.strip().startswith("```"):
            continue
        normalized_line = "".join(ch if ch == "\t" or ch == "\n" or ord(ch) >= 32 else " " for ch in line)
        cleaned_lines.append(normalized_line.rstrip())

    cleaned_code = "\n".join(cleaned_lines).strip()
    normalized_language = language or detected_language or "text"
    return cleaned_code, normalized_language
