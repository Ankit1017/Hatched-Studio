from __future__ import annotations

from main_app.services.report_export.models import (
    REPORT_TEMPLATES,
    ReportTemplateStyle,
    list_template_summaries,
    resolve_template,
)
from main_app.services.report_export.pdf_renderer import ReportPdfRenderer


class ReportExportService:
    _TEMPLATES: tuple[ReportTemplateStyle, ...] = REPORT_TEMPLATES

    def list_templates(self) -> list[dict[str, str]]:
        return list_template_summaries()

    def build_pdf(
        self,
        *,
        topic: str,
        format_title: str,
        markdown_content: str,
        template_key: str,
    ) -> tuple[bytes | None, str | None]:
        try:
            style = self._resolve_template(template_key)
            renderer = ReportPdfRenderer(style=style)
            return renderer.build(
                topic=topic,
                format_title=format_title,
                markdown_content=markdown_content,
            ), None
        except (ImportError, ModuleNotFoundError):
            return None, "reportlab is not installed. Install dependencies to enable report PDF export."
        except (OSError, ValueError, TypeError, AttributeError, RuntimeError) as exc:
            return None, f"Failed to generate report PDF: {exc}"

    @staticmethod
    def _resolve_template(template_key: str) -> ReportTemplateStyle:
        return resolve_template(template_key)
