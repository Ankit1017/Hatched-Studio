from __future__ import annotations

import unittest

from main_app.models import AgentAssetResult, AgentPlan


class TestAgentModels(unittest.TestCase):
    def test_agent_plan_round_trip(self) -> None:
        plan = AgentPlan(
            source_message="Create a quiz on CDC Pipeline",
            planner_mode="local_first",
            intents=["quiz", "mindmap"],
            payloads={
                "quiz": {"topic": "CDC Pipeline", "difficulty": "Advanced"},
                "mindmap": {"topic": "CDC Pipeline", "max_depth": 4},
            },
            missing_mandatory={"quiz": [], "mindmap": []},
            missing_optional={"quiz": ["constraints"], "mindmap": ["constraints"]},
        )

        plan_dict = plan.to_dict()
        restored = AgentPlan.from_dict(plan_dict)

        self.assertEqual(restored.source_message, plan.source_message)
        self.assertEqual(restored.planner_mode, plan.planner_mode)
        self.assertEqual(restored.intents, plan.intents)
        self.assertEqual(restored.payloads, plan.payloads)
        self.assertEqual(restored.missing_mandatory, plan.missing_mandatory)
        self.assertEqual(restored.missing_optional, plan.missing_optional)

    def test_agent_asset_result_round_trip_including_bytes(self) -> None:
        result = AgentAssetResult(
            intent="audio_overview",
            status="success",
            payload={"topic": "Segment Tree"},
            title="Audio Overview: Segment Tree",
            content={"summary": "A short summary"},
            parse_note="Parsed successfully.",
            raw_text="{...}",
            cache_hit=True,
            audio_bytes=b"abc123",
            audio_error="",
        )

        as_dict = result.to_dict()
        restored = AgentAssetResult.from_dict(as_dict)

        self.assertEqual(restored.intent, "audio_overview")
        self.assertEqual(restored.status, "success")
        self.assertEqual(restored.payload["topic"], "Segment Tree")
        self.assertEqual(restored.audio_bytes, b"abc123")
        self.assertTrue(restored.cache_hit)


if __name__ == "__main__":
    unittest.main()
