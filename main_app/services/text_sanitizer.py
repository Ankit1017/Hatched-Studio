from __future__ import annotations

import re


_CITATION_PATTERN = re.compile(r"\s*\[S\d+\]")
_BAD_CHAR_MAP = {
    "\u00a0": " ",
    "\u200b": "",
    "\u200c": "",
    "\u200d": "",
    "\ufeff": "",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u2264": "<=",
    "\u2265": ">=",
    "\u2260": "!=",
    "\u2248": "~=",
    "\u00b7": "*",
    "\u2219": "*",
    "\u2022": "-",
    "\u2080": "0",
    "\u2081": "1",
    "\u2082": "2",
    "\u2083": "3",
    "\u2084": "4",
    "\u2085": "5",
    "\u2086": "6",
    "\u2087": "7",
    "\u2088": "8",
    "\u2089": "9",
    "\u25a0": " ",
    "\u25aa": " ",
    "\u25ab": " ",
    "\ufffd": "",
}


def sanitize_text(value: object, *, keep_citations: bool = False, preserve_newlines: bool = False) -> str:
    text = str(value or "")
    text = text.replace("⌈", "ceil(").replace("⌉", ")")
    text = text.replace("⌊", "floor(").replace("⌋", ")")
    for src, dest in _BAD_CHAR_MAP.items():
        text = text.replace(src, dest)

    cleaned_chars: list[str] = []
    for ch in text:
        code = ord(ch)
        if ch in {"\n", "\t"}:
            cleaned_chars.append(ch)
            continue
        if code < 32 or code == 127:
            cleaned_chars.append(" ")
            continue
        cleaned_chars.append(ch)
    text = "".join(cleaned_chars)

    if not keep_citations:
        text = _CITATION_PATTERN.sub("", text)

    if preserve_newlines:
        lines = [" ".join(line.split()).strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        return "\n".join(line for line in lines if line)
    return " ".join(text.split()).strip()
