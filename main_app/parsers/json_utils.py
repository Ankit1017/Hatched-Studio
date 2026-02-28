from __future__ import annotations

import re


def extract_json_text(raw_text: str) -> str | None:
    text = raw_text.strip()
    fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fenced_match:
        fenced_content = fenced_match.group(1).strip()
        if (fenced_content.startswith("{") and fenced_content.endswith("}")) or (
            fenced_content.startswith("[") and fenced_content.endswith("]")
        ):
            return fenced_content

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    first_bracket = text.find("[")
    last_bracket = text.rfind("]")

    object_candidate = None
    array_candidate = None
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        object_candidate = text[first_brace : last_brace + 1]
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        array_candidate = text[first_bracket : last_bracket + 1]

    if object_candidate and array_candidate:
        return object_candidate if len(object_candidate) >= len(array_candidate) else array_candidate
    if object_candidate:
        return object_candidate
    if array_candidate:
        return array_candidate

    return None


def repair_json_text_locally(json_text: str) -> str:
    text = re.sub(r",(\s*[}\]])", r"\1", json_text.strip())

    repaired_chars: list[str] = []
    expected_closers: list[str] = []
    in_string = False
    escape_next = False

    for ch in text:
        if in_string:
            repaired_chars.append(ch)
            if escape_next:
                escape_next = False
            elif ch == "\\":
                escape_next = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            repaired_chars.append(ch)
            continue

        if ch == "{":
            expected_closers.append("}")
            repaired_chars.append(ch)
            continue

        if ch == "[":
            expected_closers.append("]")
            repaired_chars.append(ch)
            continue

        if ch in "}]":
            if not expected_closers:
                continue
            expected = expected_closers[-1]
            if ch == expected:
                expected_closers.pop()
                repaired_chars.append(ch)
            else:
                expected_closers.pop()
                repaired_chars.append(expected)
            continue

        repaired_chars.append(ch)

    while expected_closers:
        repaired_chars.append(expected_closers.pop())

    repaired_text = "".join(repaired_chars)
    repaired_text = re.sub(r",(\s*[}\]])", r"\1", repaired_text)
    repaired_text = _escape_invalid_control_chars_in_strings(repaired_text)
    return repaired_text


def _escape_invalid_control_chars_in_strings(json_text: str) -> str:
    repaired_chars: list[str] = []
    in_string = False
    escape_next = False

    for ch in json_text:
        if in_string:
            if escape_next:
                repaired_chars.append(ch)
                escape_next = False
                continue

            if ch == "\\":
                repaired_chars.append(ch)
                escape_next = True
                continue

            if ch == '"':
                repaired_chars.append(ch)
                in_string = False
                continue

            codepoint = ord(ch)
            if ch == "\n":
                repaired_chars.append("\\n")
                continue
            if ch == "\r":
                repaired_chars.append("\\r")
                continue
            if ch == "\t":
                repaired_chars.append("\\t")
                continue
            if codepoint < 0x20:
                repaired_chars.append(f"\\u{codepoint:04x}")
                continue

            repaired_chars.append(ch)
            continue

        repaired_chars.append(ch)
        if ch == '"':
            in_string = True
            escape_next = False

    return "".join(repaired_chars)
