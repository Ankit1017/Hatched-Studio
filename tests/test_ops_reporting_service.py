from __future__ import annotations

import unittest

from main_app.models import AssetHistoryRecord
from main_app.services.agent_dashboard.ops_reporting_service import OpsReportingService


class TestOpsReportingService(unittest.TestCase):
    def test_build_summary_returns_expected_shape(self) -> None:
        service = OpsReportingService()
        records = [
            AssetHistoryRecord(
                id="1",
                asset_type="topic",
                topic="CDC",
                title="Detailed Description: CDC",
                created_at="2026-01-01T00:00:00+00:00",
                model="m1",
                request_payload={"topic": "CDC"},
                result_payload={
                    "artifact": {
                        "metrics": {"total_duration_ms": 100},
                        "provenance": {"verification": {"status": "passed", "issues": []}},
                    }
                },
                status="success",
                cache_hit=False,
            ),
            AssetHistoryRecord(
                id="2",
                asset_type="topic",
                topic="CDC",
                title="Detailed Description: CDC",
                created_at="2026-01-01T00:00:01+00:00",
                model="m1",
                request_payload={"topic": "CDC"},
                result_payload={
                    "artifact": {
                        "metrics": {"total_duration_ms": 200},
                        "provenance": {
                            "verification": {
                                "status": "failed",
                                "issues": [{"code": "E_VERIFY_FAILED", "severity": "error"}],
                            }
                        },
                    }
                },
                status="error",
                cache_hit=False,
            ),
        ]
        summary = service.build_summary(records)
        self.assertEqual(summary["total_runs"], 2)
        self.assertIn("topic", summary["success_rate_by_intent"])
        self.assertIn("topic", summary["verify_failure_rate_by_intent"])
        self.assertTrue(isinstance(summary["top_error_codes"], list))
        self.assertTrue(isinstance(summary["stage_duration_ms"], dict))


if __name__ == "__main__":
    unittest.main()
