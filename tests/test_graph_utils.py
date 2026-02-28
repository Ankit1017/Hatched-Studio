from __future__ import annotations

import unittest

from main_app.mindmap.graph_utils import render_dot_as_png


class TestGraphUtils(unittest.TestCase):
    def test_render_dot_as_png_rejects_empty_source(self) -> None:
        png_bytes, error = render_dot_as_png("")
        self.assertIsNone(png_bytes)
        self.assertIsNotNone(error)

    def test_render_dot_as_png_returns_bytes_or_error(self) -> None:
        png_bytes, error = render_dot_as_png("digraph G { a -> b; }")
        if png_bytes is not None:
            self.assertIsNone(error)
            self.assertTrue(png_bytes.startswith(b"\x89PNG"))
        else:
            self.assertIsNotNone(error)


if __name__ == "__main__":
    unittest.main()
