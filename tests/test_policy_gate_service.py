from __future__ import annotations

import unittest

from main_app.models import AgentAssetResult
from main_app.services.agent_dashboard.policy_gate_service import (
    evaluate_policy_gate,
    policy_gate_passed,
)
from main_app.services.agent_dashboard.tool_registry import AgentToolDefinition


class TestPolicyGateService(unittest.TestCase):
    def test_text_policy_passes_for_valid_topic(self) -> None:
        tool = AgentToolDefinition(
            key="topic",
            intent="topic",
            title="Topic",
            description="",
            execution_spec={"execution_policy": {"profile": "text_policy_gate"}},
        )
        result = AgentAssetResult(
            intent="topic",
            status="success",
            payload={"topic": "CDC"},
            artifact={
                "sections": [
                    {"key": "artifact.topic.text", "data": "A sufficiently descriptive topic explanation."}
                ]
            },
        )
        summary = evaluate_policy_gate(result=result, tool=tool)
        self.assertTrue(policy_gate_passed(summary))

    def test_text_policy_fails_for_empty_text(self) -> None:
        tool = AgentToolDefinition(
            key="topic",
            intent="topic",
            title="Topic",
            description="",
            execution_spec={"execution_policy": {"profile": "text_policy_gate"}},
        )
        result = AgentAssetResult(
            intent="topic",
            status="success",
            payload={"topic": "CDC"},
            artifact={"sections": [{"key": "artifact.topic.text", "data": ""}]},
        )
        summary = evaluate_policy_gate(result=result, tool=tool)
        self.assertEqual(summary.get("status"), "failed")


if __name__ == "__main__":
    unittest.main()
