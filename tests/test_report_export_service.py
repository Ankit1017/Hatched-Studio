from __future__ import annotations

import unittest

from main_app.services.report_export_service import ReportExportService


class TestReportExportService(unittest.TestCase):
    def test_list_templates_has_entries(self) -> None:
        service = ReportExportService()
        templates = service.list_templates()
        self.assertGreaterEqual(len(templates), 1)
        self.assertTrue(all("key" in item for item in templates))

    def test_build_pdf_returns_pdf_bytes_or_dependency_error(self) -> None:
        service = ReportExportService()
        pdf_bytes, error = service.build_pdf(
            topic="CDC Pipeline",
            format_title="Study Guide",
            markdown_content=(
                "# CDC Pipeline\n\n"
                "## Core Concepts\n"
                "- Change data capture\n"
                "- Stream processing\n\n"
                "```python\nprint('hello')\n```"
            ),
            template_key="clean_light",
        )

        if pdf_bytes is not None:
            self.assertIsNone(error)
            self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        else:
            self.assertIsNotNone(error)
            self.assertIn("reportlab", str(error).lower())


if __name__ == "__main__":
    unittest.main()
