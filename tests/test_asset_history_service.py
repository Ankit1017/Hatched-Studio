from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from main_app.infrastructure.asset_history_store import AssetHistoryStore
from main_app.services.asset_history_service import AssetHistoryService


class TestAssetHistoryService(unittest.TestCase):
    def test_record_and_list_and_get(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = AssetHistoryStore(Path(temp_dir) / "asset_history.json")
            service = AssetHistoryService(store)

            record_id = service.record_generation(
                asset_type="mindmap",
                topic="CDC Pipeline",
                title="Mind Map: CDC Pipeline",
                model="llama-3.1-8b-instant",
                request_payload={"topic": "CDC Pipeline", "max_depth": 4},
                result_payload={"name": "CDC Pipeline", "children": []},
                status="success",
                cache_hit=True,
            )

            self.assertIsNotNone(record_id)
            records = service.list_records()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].asset_type, "mindmap")
            self.assertEqual(records[0].topic, "CDC Pipeline")
            self.assertTrue(records[0].cache_hit)

            same_record = service.get_record(record_id or "")
            self.assertIsNotNone(same_record)
            self.assertEqual(same_record.id, record_id)
            self.assertEqual(same_record.title, "Mind Map: CDC Pipeline")

    def test_filter_by_asset_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = AssetHistoryStore(Path(temp_dir) / "asset_history.json")
            service = AssetHistoryService(store)

            service.record_generation(
                asset_type="topic",
                topic="Segment Trees",
                title="Detailed Description: Segment Trees",
                model="m1",
                request_payload={"topic": "Segment Trees"},
                result_payload={"content": "text"},
                status="success",
                cache_hit=False,
            )
            service.record_generation(
                asset_type="report",
                topic="Segment Trees",
                title="Report: Segment Trees",
                model="m1",
                request_payload={"topic": "Segment Trees"},
                result_payload={"content": "report"},
                status="success",
                cache_hit=False,
            )

            topic_records = service.list_records(asset_type="topic")
            self.assertEqual(len(topic_records), 1)
            self.assertEqual(topic_records[0].asset_type, "topic")

    def test_json_safe_payload_for_non_json_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = AssetHistoryStore(Path(temp_dir) / "asset_history.json")
            service = AssetHistoryService(store)

            service.record_generation(
                asset_type="audio_overview",
                topic="Blockchain",
                title="Audio Overview: Blockchain",
                model="m1",
                request_payload={"flags": {"x", "y"}},
                result_payload={"audio_bytes": b"abc", "turns": ({1, 2},)},
                status="success",
                cache_hit=False,
            )

            record = service.list_records()[0]
            self.assertEqual(record.result_payload.get("audio_bytes"), "<bytes:3>")
            self.assertIsInstance(record.request_payload.get("flags"), list)

    def test_record_preserves_artifact_envelope_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = AssetHistoryStore(Path(temp_dir) / "asset_history.json")
            service = AssetHistoryService(store)

            service.record_generation(
                asset_type="topic",
                topic="CDC",
                title="Detailed Description: CDC",
                model="m1",
                request_payload={"topic": "CDC"},
                result_payload={
                    "artifact": {
                        "intent": "topic",
                        "title": "Detailed Description: CDC",
                        "sections": [
                            {
                                "kind": "text",
                                "key": "artifact.topic.text",
                                "title": "Primary Content",
                                "data": "CDC summary",
                                "optional": False,
                            }
                        ],
                        "metrics": {"cache_hit": False},
                        "provenance": {
                            "verification": {
                                "status": "passed",
                                "issues": [],
                                "checks_run": ["primary_section_present"],
                            }
                        },
                    }
                },
                status="success",
                cache_hit=False,
            )

            record = service.list_records()[0]
            payload = record.result_payload if isinstance(record.result_payload, dict) else {}
            artifact = payload.get("artifact", {})
            self.assertEqual(artifact.get("intent"), "topic")
            self.assertTrue(isinstance(artifact.get("sections"), list))
            provenance = artifact.get("provenance", {})
            self.assertTrue(isinstance(provenance.get("verification"), dict))
            metrics = artifact.get("metrics", {})
            self.assertIn("stage_durations_ms", metrics)
            self.assertIn("total_duration_ms", metrics)
            self.assertIn("retry_count", metrics)
            self.assertIn("verification_issue_count", metrics)
            self.assertIn("queue_wait_ms", metrics)
            self.assertIn("attempt_durations_ms", metrics)
            self.assertIn("policy_enforced", metrics)


if __name__ == "__main__":
    unittest.main()
