from __future__ import annotations

import unittest

from main_app.models import AgentAssetResult, AgentPlan, GroqSettings
from main_app.services.agent_dashboard.asset_executor_registry import AgentAssetExecutorRegistry
from main_app.services.agent_dashboard.asset_service import AgentDashboardAssetService
from main_app.services.agent_dashboard.stage_ledger_service import StageLedgerService
from main_app.services.agent_dashboard.tool_registry import build_default_agent_tool_registry
from main_app.services.agent_dashboard.workflow_registry import build_default_agent_workflow_registry


class _FakeIntentRouter:
    def evaluate_requirements(self, *, intent: str, payload: dict[str, object]):
        del intent
        if str(payload.get("topic", "")).strip():
            return [], []
        return ["topic"], []

    def is_valid_topic(self, topic: str) -> bool:
        return bool(str(topic).strip())


class _NoopService:
    def explain_node(self, **_kwargs):
        return "", False

    def explain_card(self, **_kwargs):
        return "", False

    def get_hint(self, **_kwargs):
        return "", False

    def get_attempt_feedback(self, **_kwargs):
        return {}, False

    def explain_attempt(self, **_kwargs):
        return "", False


class TestAssetResumeFlow(unittest.TestCase):
    def test_resume_skips_completed_nodes_before_resume_key(self) -> None:
        stage_ledger = StageLedgerService()
        registry = AgentAssetExecutorRegistry()
        call_count = {"topic": 0, "report": 0}

        def _topic(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            call_count["topic"] += 1
            return AgentAssetResult(
                intent="topic",
                status="success",
                payload=payload,
                content="This is a sufficiently long topic explanation for validation and verification.",
            )

        def _report(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            call_count["report"] += 1
            return AgentAssetResult(
                intent="report",
                status="success",
                payload=payload,
                content="## Report\n\nThis report body is long enough for checks.",
            )

        registry.register("topic", _topic)
        registry.register("report", _report)
        service = AgentDashboardAssetService(
            intent_router=_FakeIntentRouter(),  # type: ignore[arg-type]
            asset_executor_registry=registry,
            mind_map_service=_NoopService(),  # type: ignore[arg-type]
            flashcards_service=_NoopService(),  # type: ignore[arg-type]
            quiz_service=_NoopService(),  # type: ignore[arg-type]
            tool_registry=build_default_agent_tool_registry(),
            workflow_registry=build_default_agent_workflow_registry(),
            stage_ledger_service=stage_ledger,
        )
        plan = AgentPlan(
            source_message="create assets",
            planner_mode="local_first",
            intents=["topic", "report"],
            payloads={"topic": {"topic": "CDC"}, "report": {"topic": "CDC", "format_key": "briefing_doc"}},
            missing_mandatory={"topic": [], "report": []},
            missing_optional={"topic": [], "report": []},
        )
        _, notes = service.generate_assets_from_plan(
            plan=plan,
            settings=GroqSettings(api_key="k", model="m", temperature=0.2, max_tokens=256),
        )
        run_id = next(note.split("=", 1)[1] for note in notes if note.startswith("run_id="))
        self.assertEqual(call_count["topic"], 1)
        self.assertEqual(call_count["report"], 1)

        service.generate_assets_from_plan(
            plan=plan,
            settings=GroqSettings(api_key="k", model="m", temperature=0.2, max_tokens=256),
            resume_from_run_id=run_id,
            resume_from_tool_key="report",
        )
        self.assertEqual(call_count["topic"], 1)
        self.assertEqual(call_count["report"], 2)


if __name__ == "__main__":
    unittest.main()
