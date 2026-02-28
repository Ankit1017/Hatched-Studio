from __future__ import annotations

import os
import threading
import time
import unittest

from main_app.models import AgentAssetResult, AgentPlan, GroqSettings
from main_app.services.agent_dashboard.asset_executor_registry import AgentAssetExecutorRegistry
from main_app.services.agent_dashboard.asset_service import AgentDashboardAssetService
from main_app.services.agent_dashboard.tool_registry import AgentToolDefinition, AgentToolRegistry
from main_app.services.agent_dashboard.workflow_registry import AgentWorkflowRegistry


class _FakeIntentRouter:
    def evaluate_requirements(self, *, intent: str, payload: dict[str, object]):
        del intent, payload
        return [], []

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


class TestAssetServiceScheduler(unittest.TestCase):
    def test_parallel_scheduler_respects_max_parallel(self) -> None:
        old_parallel = os.environ.get("ENABLE_PARALLEL_DAG")
        old_max = os.environ.get("MAX_PARALLEL_TOOLS")
        os.environ["ENABLE_PARALLEL_DAG"] = "true"
        os.environ["MAX_PARALLEL_TOOLS"] = "2"
        try:
            registry = AgentAssetExecutorRegistry()
            lock = threading.Lock()
            state = {"active": 0, "max": 0}

            def _executor(intent: str):
                def _run(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
                    del payload
                    with lock:
                        state["active"] += 1
                        state["max"] = max(state["max"], state["active"])
                    time.sleep(0.03)
                    with lock:
                        state["active"] -= 1
                    return AgentAssetResult(
                        intent=intent,
                        status="success",
                        payload={"topic": "CDC"},
                        content="This is a sufficiently long text output for verification checks.",
                    )

                return _run

            for intent in ["alpha", "beta", "gamma"]:
                registry.register(intent, _executor(intent))

            tool_registry = AgentToolRegistry(
                tools=[
                    AgentToolDefinition(key="alpha", intent="alpha", title="Alpha", description=""),
                    AgentToolDefinition(key="beta", intent="beta", title="Beta", description=""),
                    AgentToolDefinition(key="gamma", intent="gamma", title="Gamma", description=""),
                ]
            )
            workflow_registry = AgentWorkflowRegistry()
            service = AgentDashboardAssetService(
                intent_router=_FakeIntentRouter(),  # type: ignore[arg-type]
                asset_executor_registry=registry,
                mind_map_service=_NoopService(),  # type: ignore[arg-type]
                flashcards_service=_NoopService(),  # type: ignore[arg-type]
                quiz_service=_NoopService(),  # type: ignore[arg-type]
                tool_registry=tool_registry,
                workflow_registry=workflow_registry,
            )
            plan = AgentPlan(
                source_message="make assets",
                planner_mode="local_first",
                intents=["alpha", "beta", "gamma"],
                payloads={"alpha": {}, "beta": {}, "gamma": {}},
                missing_mandatory={"alpha": [], "beta": [], "gamma": []},
                missing_optional={"alpha": [], "beta": [], "gamma": []},
            )
            assets, notes = service.generate_assets_from_plan(
                plan=plan,
                settings=GroqSettings(api_key="k", model="m", temperature=0.2, max_tokens=128),
            )
            self.assertEqual(len(assets), 3)
            self.assertLessEqual(state["max"], 2)
            self.assertEqual(sum(1 for note in notes if note.startswith("run_id=")), 1)
        finally:
            if old_parallel is None:
                os.environ.pop("ENABLE_PARALLEL_DAG", None)
            else:
                os.environ["ENABLE_PARALLEL_DAG"] = old_parallel
            if old_max is None:
                os.environ.pop("MAX_PARALLEL_TOOLS", None)
            else:
                os.environ["MAX_PARALLEL_TOOLS"] = old_max


if __name__ == "__main__":
    unittest.main()
