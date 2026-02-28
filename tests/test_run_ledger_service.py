from __future__ import annotations

import unittest
from datetime import datetime, timezone

from main_app.services.agent_dashboard.run_ledger_service import RunLedgerService


class TestRunLedgerService(unittest.TestCase):
    def test_record_and_query_runs(self) -> None:
        service = RunLedgerService()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        service.record_run(
            {
                "run_id": "r1",
                "workflow_key": "plan_selected_assets",
                "planner_mode": "local_first",
                "status": "success",
                "started_at": now.isoformat(),
                "ended_at": now.isoformat(),
                "tool_summaries": [{"intent": "topic", "status": "success"}],
                "error_counts": {},
            }
        )
        all_runs = service.list_runs()
        self.assertEqual(len(all_runs), 1)
        self.assertEqual(all_runs[0]["run_id"], "r1")
        filtered = service.query_runs(intent="topic")
        self.assertEqual(len(filtered), 1)


if __name__ == "__main__":
    unittest.main()
