from __future__ import annotations

import unittest

from main_app.models import AgentPlan
from main_app.services.agent_dashboard.asset_executor_registry import AgentAssetExecutorRegistry
from main_app.services.agent_dashboard.asset_service import AgentDashboardAssetService
from main_app.services.agent_dashboard.tool_registry import build_default_agent_tool_registry
from main_app.services.agent_dashboard.workflow_registry import build_default_agent_workflow_registry


class _IntentRouterStub:
    def evaluate_requirements(self, *, intent: str, payload: dict[str, object]) -> tuple[list[str], list[str]]:
        del intent, payload
        return [], []

    def is_valid_topic(self, topic: str) -> bool:
        return bool(str(topic).strip())


class _NoopService:
    def explain_node(self, **_kwargs: object) -> tuple[str, bool]:
        return "", False

    def explain_card(self, **_kwargs: object) -> tuple[str, bool]:
        return "", False

    def get_hint(self, **_kwargs: object) -> tuple[str, bool]:
        return "", False

    def get_attempt_feedback(self, **_kwargs: object) -> tuple[dict[str, str], bool]:
        return {}, False

    def explain_attempt(self, **_kwargs: object) -> tuple[str, bool]:
        return "", False


class TestSimulationService(unittest.TestCase):
    def test_simulation_returns_expected_nodes_and_stages(self) -> None:
        service = AgentDashboardAssetService(
            intent_router=_IntentRouterStub(),  # type: ignore[arg-type]
            asset_executor_registry=AgentAssetExecutorRegistry(),
            mind_map_service=_NoopService(),  # type: ignore[arg-type]
            flashcards_service=_NoopService(),  # type: ignore[arg-type]
            quiz_service=_NoopService(),  # type: ignore[arg-type]
            tool_registry=build_default_agent_tool_registry(),
            workflow_registry=build_default_agent_workflow_registry(),
        )
        plan = AgentPlan(
            source_message="simulate",
            planner_mode="local_first",
            intents=["slideshow", "video"],
            payloads={"slideshow": {}, "video": {}},
            missing_mandatory={"slideshow": [], "video": []},
            missing_optional={"slideshow": [], "video": []},
        )
        report = service.simulate_plan_execution(plan)
        nodes = report.get("nodes", [])
        self.assertEqual(len(nodes), 2)
        by_intent = {str(node.get("intent", "")): node for node in nodes if isinstance(node, dict)}
        self.assertIn("slideshow", by_intent)
        self.assertIn("video", by_intent)
        self.assertIn("validate_schema", by_intent["video"].get("expected_stages", []))
        self.assertTrue(by_intent["video"].get("planned_state_path", [])[0] == "pending")


if __name__ == "__main__":
    unittest.main()
