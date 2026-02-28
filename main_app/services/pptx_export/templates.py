from __future__ import annotations

from main_app.services.pptx_export.models import PptxTemplateStyle
from main_app.services.pptx_export.text_utils import normalize_text

PPTX_TEMPLATES: tuple[PptxTemplateStyle, ...] = (
    PptxTemplateStyle(
        key="clean_light",
        title="Clean Light",
        description="Bright and minimal with sharp contrast.",
        font_name="Calibri",
        background_color=(248, 250, 252),
        accent_color=(37, 99, 235),
        title_color=(15, 23, 42),
        body_color=(30, 41, 59),
        section_chip_color=(219, 234, 254),
        section_chip_text_color=(30, 64, 175),
        code_panel_color=(17, 24, 39),
        code_text_color=(224, 231, 255),
    ),
    PptxTemplateStyle(
        key="ocean_blue",
        title="Ocean Blue",
        description="Cool blue palette for technical walkthroughs.",
        font_name="Calibri",
        background_color=(239, 246, 255),
        accent_color=(2, 132, 199),
        title_color=(8, 47, 73),
        body_color=(12, 74, 110),
        section_chip_color=(186, 230, 253),
        section_chip_text_color=(7, 89, 133),
        code_panel_color=(15, 23, 42),
        code_text_color=(186, 230, 253),
    ),
    PptxTemplateStyle(
        key="graphite_dark",
        title="Graphite Dark",
        description="Dark professional deck with vivid accents.",
        font_name="Calibri",
        background_color=(15, 23, 42),
        accent_color=(56, 189, 248),
        title_color=(241, 245, 249),
        body_color=(203, 213, 225),
        section_chip_color=(30, 41, 59),
        section_chip_text_color=(125, 211, 252),
        code_panel_color=(2, 6, 23),
        code_text_color=(186, 230, 253),
    ),
    PptxTemplateStyle(
        key="sage_modern",
        title="Sage Modern",
        description="Balanced modern style with soft green accents.",
        font_name="Calibri",
        background_color=(240, 253, 244),
        accent_color=(22, 163, 74),
        title_color=(20, 83, 45),
        body_color=(22, 101, 52),
        section_chip_color=(220, 252, 231),
        section_chip_text_color=(22, 101, 52),
        code_panel_color=(20, 83, 45),
        code_text_color=(220, 252, 231),
    ),
    PptxTemplateStyle(
        key="sunset_amber",
        title="Sunset Amber",
        description="Warm amber accent palette for storytelling decks.",
        font_name="Calibri",
        background_color=(255, 251, 235),
        accent_color=(217, 119, 6),
        title_color=(120, 53, 15),
        body_color=(146, 64, 14),
        section_chip_color=(254, 243, 199),
        section_chip_text_color=(146, 64, 14),
        code_panel_color=(124, 45, 18),
        code_text_color=(254, 243, 199),
    ),
)


def list_template_summaries() -> list[dict[str, str]]:
    return [
        {
            "key": template.key,
            "title": template.title,
            "description": template.description,
        }
        for template in PPTX_TEMPLATES
    ]


def resolve_template(template_key: str) -> PptxTemplateStyle:
    requested = normalize_text(template_key).lower()
    for template in PPTX_TEMPLATES:
        if template.key == requested:
            return template
    return PPTX_TEMPLATES[0]
