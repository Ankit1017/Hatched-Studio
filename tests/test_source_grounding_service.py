from __future__ import annotations

import unittest

from main_app.services.source_grounding_service import SourceGroundingService


class _UploadedFile:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


class TestSourceGroundingService(unittest.TestCase):
    def test_extract_sources_and_build_context(self) -> None:
        service = SourceGroundingService(
            max_sources=5,
            max_chars_per_source=500,
            max_total_chars=1000,
        )
        files = [
            _UploadedFile("alpha.txt", b"Alpha fact one.\nAlpha fact two."),
            _UploadedFile("beta.md", b"# Beta\n\nBeta detail A.\n\nBeta detail B."),
        ]

        sources, warnings = service.extract_sources(files)
        context = service.build_grounding_context(sources)
        manifest = service.build_source_manifest(sources)

        self.assertEqual(len(sources), 2)
        self.assertFalse(warnings)
        self.assertIn("[S1] alpha.txt", context)
        self.assertIn("[S2] beta.md", context)
        self.assertEqual(manifest[0]["source_id"], "S1")
        self.assertEqual(manifest[1]["source_id"], "S2")

    def test_extract_sources_applies_limits(self) -> None:
        service = SourceGroundingService(
            max_sources=1,
            max_chars_per_source=500,
            max_total_chars=600,
        )
        files = [
            _UploadedFile("long.txt", b"A" * 2000),
            _UploadedFile("ignored.txt", b"Should not be included"),
        ]
        sources, warnings = service.extract_sources(files)

        self.assertEqual(len(sources), 1)
        self.assertTrue(sources[0].truncated)
        self.assertLessEqual(sources[0].char_count, 500)
        self.assertTrue(any("first 1 sources" in item for item in warnings))


if __name__ == "__main__":
    unittest.main()
