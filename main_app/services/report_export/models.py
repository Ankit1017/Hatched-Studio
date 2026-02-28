from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportTemplateStyle:
    key: str
    title: str
    description: str
    page_background: tuple[int, int, int]
    accent: tuple[int, int, int]
    title_color: tuple[int, int, int]
    heading_color: tuple[int, int, int]
    body_color: tuple[int, int, int]
    code_background: tuple[int, int, int]
    code_text_color: tuple[int, int, int]


REPORT_TEMPLATES: tuple[ReportTemplateStyle, ...] = (
    ReportTemplateStyle(
        key="clean_light",
        title="Clean Light",
        description="Minimal layout with strong readability.",
        page_background=(251, 252, 254),
        accent=(37, 99, 235),
        title_color=(15, 23, 42),
        heading_color=(30, 64, 175),
        body_color=(31, 41, 55),
        code_background=(17, 24, 39),
        code_text_color=(224, 231, 255),
    ),
    ReportTemplateStyle(
        key="paper_beige",
        title="Paper Beige",
        description="Warm editorial style for long-form reading.",
        page_background=(255, 252, 245),
        accent=(180, 83, 9),
        title_color=(120, 53, 15),
        heading_color=(146, 64, 14),
        body_color=(68, 64, 60),
        code_background=(41, 37, 36),
        code_text_color=(254, 243, 199),
    ),
    ReportTemplateStyle(
        key="graphite_navy",
        title="Graphite Navy",
        description="Professional dark-accent technical report look.",
        page_background=(245, 248, 252),
        accent=(30, 58, 138),
        title_color=(15, 23, 42),
        heading_color=(30, 64, 175),
        body_color=(51, 65, 85),
        code_background=(15, 23, 42),
        code_text_color=(191, 219, 254),
    ),
    ReportTemplateStyle(
        key="forest_sage",
        title="Forest Sage",
        description="Soft green theme with clear section contrast.",
        page_background=(245, 253, 247),
        accent=(21, 128, 61),
        title_color=(20, 83, 45),
        heading_color=(22, 101, 52),
        body_color=(31, 55, 43),
        code_background=(20, 83, 45),
        code_text_color=(220, 252, 231),
    ),
)


def list_template_summaries() -> list[dict[str, str]]:
    return [
        {
            "key": template.key,
            "title": template.title,
            "description": template.description,
        }
        for template in REPORT_TEMPLATES
    ]


def resolve_template(template_key: str) -> ReportTemplateStyle:
    key = " ".join(str(template_key).strip().split()).lower()
    for template in REPORT_TEMPLATES:
        if template.key == key:
            return template
    return REPORT_TEMPLATES[0]
