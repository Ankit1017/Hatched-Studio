from __future__ import annotations

import unittest

from main_app.domains.topic.parser.topic_prompt_builder import build_topic_prompts


class TestTopicPromptBuilder(unittest.TestCase):
    def test_default_prompt_shape(self) -> None:
        system_prompt, user_prompt = build_topic_prompts(
            topic="Binary Search",
            additional_instructions="Add one practical example.",
        )
        self.assertIn("expert educator and technical writer", system_prompt)
        self.assertIn("Topic: Binary Search", user_prompt)
        self.assertIn("Additional instructions from user", user_prompt)
        self.assertNotIn("Citation requirement", user_prompt)

    def test_grounded_prompt_without_required_citations(self) -> None:
        system_prompt, user_prompt = build_topic_prompts(
            topic="CDC",
            additional_instructions="",
            grounding_context="[S1] doc\nCDC captures changes.",
            require_citations=False,
        )
        self.assertIn("Source-grounded mode is enabled", system_prompt)
        self.assertIn("Use only the following sources as grounding context", user_prompt)
        self.assertIn("[S1]", user_prompt)
        self.assertNotIn("Citation requirement", user_prompt)

    def test_grounded_prompt_with_required_citations(self) -> None:
        _, user_prompt = build_topic_prompts(
            topic="CDC",
            additional_instructions="",
            grounding_context="[S1] doc\nCDC captures changes.",
            require_citations=True,
        )
        self.assertIn("Citation requirement", user_prompt)
        self.assertIn("Do not invent source IDs", user_prompt)


if __name__ == "__main__":
    unittest.main()
