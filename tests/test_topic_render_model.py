from __future__ import annotations

import unittest

from main_app.domains.topic.renderer.topic_render_model import extract_topic_markdown


class TestTopicRenderModel(unittest.TestCase):
    def test_extracts_from_direct_content_first(self) -> None:
        value = extract_topic_markdown(
            content="Topic markdown",
            result_payload={"content": "other"},
            artifact={"sections": [{"key": "artifact.topic.text", "data": "from artifact"}]},
        )
        self.assertEqual(value, "Topic markdown")

    def test_extracts_from_payload_when_content_is_none(self) -> None:
        value = extract_topic_markdown(
            content=None,
            result_payload={"content": "Payload topic markdown"},
        )
        self.assertEqual(value, "Payload topic markdown")

    def test_extracts_from_artifact_section_when_payload_missing(self) -> None:
        value = extract_topic_markdown(
            content=None,
            result_payload={},
            artifact={
                "sections": [
                    {"key": "artifact.quiz.data", "data": {"ignored": True}},
                    {"key": "artifact.topic.text", "data": "Topic from artifact"},
                ]
            },
        )
        self.assertEqual(value, "Topic from artifact")

    def test_returns_empty_when_no_topic_data_available(self) -> None:
        value = extract_topic_markdown(content=None, result_payload={}, artifact={})
        self.assertEqual(value, "")


if __name__ == "__main__":
    unittest.main()
