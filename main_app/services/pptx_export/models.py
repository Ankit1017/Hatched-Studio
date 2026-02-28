from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PptxTemplateStyle:
    key: str
    title: str
    description: str
    font_name: str
    background_color: tuple[int, int, int]
    accent_color: tuple[int, int, int]
    title_color: tuple[int, int, int]
    body_color: tuple[int, int, int]
    section_chip_color: tuple[int, int, int]
    section_chip_text_color: tuple[int, int, int]
    code_panel_color: tuple[int, int, int]
    code_text_color: tuple[int, int, int]
