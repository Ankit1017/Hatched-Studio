from __future__ import annotations

import unittest

from main_app.services.intent.intent_router_text_utils import IntentRouterTextUtils


class TestIntentRouterTextUtils(unittest.TestCase):
    def setUp(self) -> None:
        self.utils = IntentRouterTextUtils()

    def test_extract_field_from_message_uses_default_registry(self) -> None:
        value = self.utils.extract_field_from_message(
            message="Generate 15 questions on CDC Pipeline",
            field_name="question_count",
        )
        self.assertEqual(value, 15)

    def test_extract_field_from_message_supports_custom_extractor(self) -> None:
        field_name = "custom_test_field"

        def extractor(_text: str, lower: str) -> str | None:
            return "enabled" if "enable custom mode" in lower else None

        self.utils.register_field_extractor(field_name, extractor)
        value = self.utils.extract_field_from_message(
            message="Please enable custom mode for this run",
            field_name=field_name,
        )

        self.assertEqual(value, "enabled")

    def test_extract_constraint_field(self) -> None:
        value = self.utils.extract_field_from_message(
            message="Create flashcards on CDC. Focus on production trade-offs.",
            field_name="constraints",
        )
        self.assertEqual(value, "production trade-offs")

    def test_custom_extractor_is_instance_scoped(self) -> None:
        field_name = "custom_isolation_field"

        def extractor(_text: str, lower: str) -> str | None:
            return "ok" if "activate isolation" in lower else None

        self.utils.register_field_extractor(field_name, extractor)
        isolated_utils = IntentRouterTextUtils()

        self.assertEqual(
            self.utils.extract_field_from_message(
                message="Please activate isolation now",
                field_name=field_name,
            ),
            "ok",
        )
        self.assertIsNone(
            isolated_utils.extract_field_from_message(
                message="Please activate isolation now",
                field_name=field_name,
            )
        )


if __name__ == "__main__":
    unittest.main()
