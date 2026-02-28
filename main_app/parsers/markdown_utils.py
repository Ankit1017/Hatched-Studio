from __future__ import annotations

import json
import re


def normalize_markdown_text(raw_text: str) -> str:
    text = str(raw_text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    # If model wrapped markdown in a single fenced block, unwrap it.
    fenced_match = re.fullmatch(r"```(?:markdown|md)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1).strip()

    # If model returned a JSON-escaped string, decode it.
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        decoded = _try_decode_json_string(text)
        if decoded is not None:
            text = decoded.strip()
        else:
            text = text[1:-1].strip()

    # Recover common escaped content from cached/session payloads.
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\n", "\n")
    if '\\"' in text:
        text = text.replace('\\"', '"')
    if "\\'" in text:
        text = text.replace("\\'", "'")

    # Remove accidental surrounding quotes left after partial decoding.
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()

    text = _demote_numbered_headings(text)

    return text.strip()


def _try_decode_json_string(value: str) -> str | None:
    try:
        decoded = json.loads(value)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(decoded, str):
        return decoded
    return None


def _demote_numbered_headings(text: str) -> str:
    # Streamlit adds anchor UI for markdown headings; convert numbered heading lines
    # like "### 1. ..." into regular ordered-list lines for cleaner report visuals.
    return re.sub(
        r"(?m)^[ \t]{0,3}#{1,6}[ \t]+(\d+\.\s+.+?)[ \t]*$",
        r"\1",
        text,
    )
