from __future__ import annotations

from io import BytesIO
from typing import Any

from main_app.services.report_export.markdown_renderer import ReportMarkdownRenderer
from main_app.services.report_export.models import ReportTemplateStyle


class ReportPdfRenderer:
    def __init__(self, style: ReportTemplateStyle) -> None:
        self._style = style
        self._markdown_renderer = ReportMarkdownRenderer()

    def build(
        self,
        *,
        topic: str,
        format_title: str,
        markdown_content: str,
    ) -> bytes:
        from reportlab.lib import colors  # type: ignore
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore
        from reportlab.lib.units import inch  # type: ignore
        from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore

        color = lambda rgb: colors.Color(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
        style = self._style
        margin = 0.68 * inch
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=0.9 * inch,
            bottomMargin=0.75 * inch,
            title=(topic.strip() or "Report"),
            author="Knowledge App",
        )

        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=color(style.body_color),
            spaceAfter=7,
        )
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            textColor=color(style.title_color),
            spaceAfter=8,
        )
        meta_style = ParagraphStyle(
            "MetaStyle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=color(style.heading_color),
            spaceAfter=5,
        )
        heading_styles: dict[int, Any] = {
            1: ParagraphStyle(
                "Heading1Style",
                parent=styles["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=18,
                leading=24,
                textColor=color(style.heading_color),
                spaceAfter=10,
                spaceBefore=10,
            ),
            2: ParagraphStyle(
                "Heading2Style",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=15,
                leading=21,
                textColor=color(style.heading_color),
                spaceAfter=8,
                spaceBefore=8,
            ),
            3: ParagraphStyle(
                "Heading3Style",
                parent=styles["Heading3"],
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=18,
                textColor=color(style.heading_color),
                spaceAfter=6,
                spaceBefore=6,
            ),
            4: ParagraphStyle(
                "Heading4Style",
                parent=styles["Heading4"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=16,
                textColor=color(style.heading_color),
                spaceAfter=6,
                spaceBefore=6,
            ),
        }
        code_label_style = ParagraphStyle(
            "CodeLabelStyle",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=color(style.code_text_color),
            spaceAfter=4,
        )
        code_style = ParagraphStyle(
            "CodeStyle",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=8.8,
            leading=11,
            textColor=color(style.code_text_color),
            leftIndent=0,
            rightIndent=0,
            spaceAfter=0,
        )

        content = str(markdown_content or "").strip()
        story: list[Any] = []
        story.append(Paragraph(self._markdown_renderer.escape_inline_markup(topic.strip() or "Generated Report"), title_style))
        story.append(
            Paragraph(
                f"Format: {self._markdown_renderer.escape_inline_markup(format_title.strip() or 'Report')}",
                meta_style,
            )
        )
        story.append(Spacer(1, 8))

        story.extend(
            self._markdown_renderer.render_to_flowables(
                markdown_text=content,
                body_style=body_style,
                heading_styles=heading_styles,
                code_style=code_style,
                code_label_style=code_label_style,
                code_background=color(style.code_background),
                max_content_width=document.width,
                Paragraph=Paragraph,
                Preformatted=Preformatted,
                Spacer=Spacer,
                Table=Table,
                TableStyle=TableStyle,
            )
        )

        def on_page(pdf_canvas: Any, doc: Any) -> None:
            self._draw_page_chrome(
                pdf_canvas=pdf_canvas,
                doc=doc,
                page_background_color=color(style.page_background),
                accent_color=color(style.accent),
                heading_color=color(style.heading_color),
            )

        document.build(
            story,
            onFirstPage=on_page,
            onLaterPages=on_page,
        )
        return output.getvalue()

    def _draw_page_chrome(
        self,
        *,
        pdf_canvas: Any,
        doc: Any,
        page_background_color: Any,
        accent_color: Any,
        heading_color: Any,
    ) -> None:
        width, height = doc.pagesize
        pdf_canvas.saveState()
        pdf_canvas.setFillColor(page_background_color)
        pdf_canvas.rect(0, 0, width, height, fill=1, stroke=0)
        pdf_canvas.setFillColor(accent_color)
        pdf_canvas.rect(0, height - 14, width, 14, fill=1, stroke=0)
        pdf_canvas.setStrokeColor(heading_color)
        pdf_canvas.setLineWidth(0.7)
        pdf_canvas.line(doc.leftMargin, height - 33, width - doc.rightMargin, height - 33)
        pdf_canvas.setFillColor(heading_color)
        pdf_canvas.setFont("Helvetica", 8.5)
        pdf_canvas.drawRightString(width - doc.rightMargin, 18, f"Page {doc.page}")
        pdf_canvas.drawString(doc.leftMargin, 18, self._style.title)
        pdf_canvas.restoreState()
