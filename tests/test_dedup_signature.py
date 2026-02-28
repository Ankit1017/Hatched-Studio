from __future__ import annotations

import unittest

from main_app.services.agent_dashboard.asset_service import AgentDashboardAssetService
from main_app.services.agent_dashboard.tool_registry import AgentToolDefinition


class TestDedupSignature(unittest.TestCase):
    def test_signature_stable_for_equivalent_payload_order(self) -> None:
        tool = AgentToolDefinition(
            key="video",
            intent="video",
            title="Video",
            description="",
            execution_spec={"dependency": {"requires_artifacts": ["artifact.slideshow.slides"]}},
        )
        payload_a = {"topic": "CDC", "slow_audio": False}
        payload_b = {"slow_audio": False, "topic": "CDC"}
        artifacts = {"artifact.slideshow.slides": {"slides": [{"title": "A"}]}}
        sig_a = AgentDashboardAssetService._tool_run_signature(  # noqa: SLF001
            tool=tool,
            payload=payload_a,
            available_artifacts=artifacts,
        )
        sig_b = AgentDashboardAssetService._tool_run_signature(  # noqa: SLF001
            tool=tool,
            payload=payload_b,
            available_artifacts=artifacts,
        )
        self.assertEqual(sig_a, sig_b)


if __name__ == "__main__":
    unittest.main()
