from __future__ import annotations

import unittest

from main_app.services.pptx_export_service import PptxExportService


class TestPptxExportService(unittest.TestCase):
    @staticmethod
    def _representation_slides() -> list[dict[str, object]]:
        return [
            {"title": "Bullet", "representation": "bullet", "layout_payload": {"items": ["A", "B"]}, "bullets": ["A", "B"]},
            {
                "title": "Two Column",
                "representation": "two_column",
                "layout_payload": {
                    "left_title": "Left",
                    "left_items": ["L1", "L2"],
                    "right_title": "Right",
                    "right_items": ["R1", "R2"],
                },
                "bullets": ["L1", "R1"],
            },
            {
                "title": "Timeline",
                "representation": "timeline",
                "layout_payload": {"events": [{"label": "T1", "detail": "Kickoff"}]},
                "bullets": ["T1 kickoff"],
            },
            {
                "title": "Comparison",
                "representation": "comparison",
                "layout_payload": {
                    "left_title": "A",
                    "left_points": ["A1"],
                    "right_title": "B",
                    "right_points": ["B1"],
                },
                "bullets": ["A1", "B1"],
            },
            {
                "title": "Process",
                "representation": "process_flow",
                "layout_payload": {"steps": [{"title": "Plan", "detail": "Define scope"}]},
                "bullets": ["Plan scope"],
            },
            {
                "title": "Metrics",
                "representation": "metric_cards",
                "layout_payload": {"cards": [{"label": "Latency", "value": "120ms", "context": "p95"}]},
                "bullets": ["Latency 120ms"],
            },
        ]

    def test_list_templates_has_entries(self) -> None:
        service = PptxExportService()
        templates = service.list_templates()
        self.assertGreaterEqual(len(templates), 1)
        self.assertTrue(all("key" in item for item in templates))

    def test_build_pptx_returns_bytes_or_dependency_error(self) -> None:
        service = PptxExportService()
        pptx_bytes, error = service.build_pptx(
            topic="CDC Pipeline",
            slides=[{"title": "Intro", "bullets": ["What is CDC?"], "speaker_notes": "start"}],
            template_key="clean_light",
        )

        if pptx_bytes is not None:
            self.assertIsNone(error)
            self.assertTrue(pptx_bytes.startswith(b"PK"))
        else:
            self.assertIsNotNone(error)
            self.assertIn("python-pptx", str(error).lower())

    def test_build_pdf_returns_pdf_bytes_or_dependency_error(self) -> None:
        service = PptxExportService()
        pdf_bytes, error = service.build_pdf(
            topic="CDC Pipeline",
            slides=[{"title": "Intro", "bullets": ["What is CDC?"], "speaker_notes": "start"}],
            template_key="clean_light",
        )

        if pdf_bytes is not None:
            self.assertIsNone(error)
            self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        else:
            self.assertIsNotNone(error)
            self.assertIn("reportlab", str(error).lower())

    def test_build_pptx_supports_all_representations_or_dependency_error(self) -> None:
        service = PptxExportService()
        pptx_bytes, error = service.build_pptx(
            topic="Representations",
            slides=self._representation_slides(),
            template_key="clean_light",
        )
        if pptx_bytes is not None:
            self.assertIsNone(error)
            self.assertTrue(pptx_bytes.startswith(b"PK"))
        else:
            self.assertIsNotNone(error)
            self.assertIn("python-pptx", str(error).lower())

    def test_build_pdf_unknown_representation_falls_back_or_dependency_error(self) -> None:
        service = PptxExportService()
        pdf_bytes, error = service.build_pdf(
            topic="Fallback",
            slides=[
                {
                    "title": "Unknown",
                    "representation": "unknown_layout",
                    "layout_payload": {"x": 1},
                    "bullets": ["Fallback bullet one", "Fallback bullet two"],
                }
            ],
            template_key="clean_light",
        )
        if pdf_bytes is not None:
            self.assertIsNone(error)
            self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        else:
            self.assertIsNotNone(error)
            self.assertIn("reportlab", str(error).lower())

    def test_prepare_code_payload_extracts_fenced_code(self) -> None:
        service = PptxExportService()
        code, language = service._prepare_code_payload(
            code_snippet="```python\nprint('hello')\n```",
            code_language="",
        )
        self.assertEqual(language, "python")
        self.assertEqual(code, "print('hello')")


if __name__ == "__main__":
    unittest.main()
