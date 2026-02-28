from __future__ import annotations

import sys
import types

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(choices=[])))

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

import unittest

from main_app.models import AgentPlan, GroqSettings
from main_app.services.agent_dashboard.asset_executor_registry import AgentAssetExecutorRegistry
from main_app.services.agent_dashboard import AgentDashboardService


class _FakeIntentRouter:
    MODE_LOCAL_FIRST = "local_first"

    def detect_intent(self, **_kwargs):
        raise AssertionError("detect_intent not needed in this unit test")

    def prepare_requirements(self, **_kwargs):
        raise AssertionError("prepare_requirements not needed in this unit test")

    def evaluate_requirements(self, *, intent: str, payload: dict[str, object]):
        if str(payload.get("topic", "")).strip():
            return [], []
        return ["topic"], []

    def is_valid_topic(self, topic: str) -> bool:
        return bool(str(topic).strip())


class _NoopService:
    pass


class TestAgentDashboardService(unittest.TestCase):
    def _service(self) -> AgentDashboardService:
        registry = AgentAssetExecutorRegistry()

        def topic_executor(payload: dict[str, object], _settings: GroqSettings):
            from main_app.models import AgentAssetResult

            return AgentAssetResult(
                intent="topic",
                status="success",
                payload=payload,
                content="CDC pipeline enables reliable low-latency change propagation across systems.",
            )

        registry.register("topic", topic_executor)

        return AgentDashboardService(
            intent_router=_FakeIntentRouter(),
            explainer_service=_NoopService(),
            mind_map_service=_NoopService(),
            flashcards_service=_NoopService(),
            data_table_service=_NoopService(),
            quiz_service=_NoopService(),
            slideshow_service=_NoopService(),
            audio_overview_service=_NoopService(),
            report_service=_NoopService(),
            asset_executor_registry=registry,
        )

    def test_generate_assets_from_plan_uses_typed_results(self) -> None:
        service = self._service()
        settings = GroqSettings(api_key="k", model="m", temperature=0.2, max_tokens=128)
        plan = AgentPlan(
            source_message="Explain CDC",
            planner_mode="local_first",
            intents=["topic"],
            payloads={"topic": {"topic": "CDC Pipeline"}},
            missing_mandatory={"topic": []},
            missing_optional={"topic": []},
        )

        assets, notes = service.generate_assets_from_plan(plan=plan, settings=settings)

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].status, "success")
        self.assertEqual(assets[0].intent, "topic")
        self.assertTrue(any("Generated 1/1 assets" in note for note in notes))
        self.assertTrue(any("verify_result" in note for note in notes))
        self.assertTrue(any(note.startswith("run_id=") for note in notes))
        self.assertEqual(sum(1 for note in notes if note.startswith("run_id=")), 1)
        self.assertTrue(any("duration_ms=" in note for note in notes))

    def test_generate_assets_from_plan_marks_missing_mandatory(self) -> None:
        service = self._service()
        settings = GroqSettings(api_key="k", model="m", temperature=0.2, max_tokens=128)
        plan = AgentPlan(
            source_message="Explain",
            planner_mode="local_first",
            intents=["topic"],
            payloads={"topic": {}},
            missing_mandatory={"topic": ["topic"]},
            missing_optional={"topic": []},
        )

        assets, _ = service.generate_assets_from_plan(plan=plan, settings=settings)

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].status, "error")
        self.assertIn("Mandatory requirements missing", assets[0].error)

    def test_service_exposes_tools_and_workflows(self) -> None:
        service = self._service()
        tools = service.list_registered_tools()
        workflows = service.list_registered_workflows()
        stage_sequences = service.list_tool_stage_sequences()

        self.assertTrue(any(tool.intent == "topic" for tool in tools))
        self.assertTrue(any(workflow.key == "plan_selected_assets" for workflow in workflows))
        self.assertIn("topic", stage_sequences)


if __name__ == "__main__":
    unittest.main()
