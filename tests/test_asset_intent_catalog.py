from __future__ import annotations

import unittest

from main_app.services.agent_dashboard import ASSET_INTENTS, normalize_intent, ordered_asset_intents
from main_app.services.intent.intent_requirement_spec import INTENT_ORDER


class TestAssetIntentCatalog(unittest.TestCase):
    def test_catalog_order_matches_intent_order(self) -> None:
        self.assertEqual(list(ASSET_INTENTS), INTENT_ORDER)

    def test_ordered_asset_intents_normalizes_and_orders(self) -> None:
        intents = ordered_asset_intents(["  QUIZ  ", "mind map", "video"])
        self.assertEqual(intents, ["quiz", "video"])

    def test_normalize_intent(self) -> None:
        self.assertEqual(normalize_intent("  data   table "), "data table")


if __name__ == "__main__":
    unittest.main()
