from __future__ import annotations

import sys
import types
import unittest
import os
import time

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(choices=[])))

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

from main_app.models import AgentAssetResult, GroqSettings
from main_app.services.agent_dashboard.asset_executor_registry import AgentAssetExecutorRegistry
from main_app.services.agent_dashboard.tool_registry import build_default_agent_tool_registry
from main_app.services.agent_dashboard.tool_stage_service import (
    AgentToolStageOrchestrator,
    build_default_tool_stage_catalog,
)


class _FakeIntentRouter:
    def evaluate_requirements(self, *, intent: str, payload: dict[str, object]):
        del intent
        if str(payload.get("topic", "")).strip():
            return [], []
        return ["topic"], []


class TestToolStageService(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = GroqSettings(
            api_key="k",
            model="m",
            temperature=0.2,
            max_tokens=128,
        )

    def test_default_catalog_assigns_stage_sequence_for_all_tools(self) -> None:
        tool_registry = build_default_agent_tool_registry()
        stage_catalog = build_default_tool_stage_catalog(tool_registry=tool_registry)
        stage_workflows = stage_catalog.list_workflows()
        self.assertEqual(len(stage_workflows), len(tool_registry.list_tools()))
        for workflow in stage_workflows:
            self.assertGreaterEqual(len(workflow.stage_keys), 1)

    def test_each_stage_has_requirements(self) -> None:
        orchestrator = AgentToolStageOrchestrator()
        stage_map = orchestrator._build_stage_definitions()  # noqa: SLF001
        for stage in stage_map.values():
            self.assertGreaterEqual(len(stage.requirements), 1)
        self.assertIn("resolve_dependencies", stage_map)
        self.assertIn("normalize_artifact", stage_map)
        self.assertIn("validate_schema", stage_map)
        self.assertIn("verify_result", stage_map)
        self.assertIn("policy_gate_result", stage_map)

    def test_orchestrator_returns_error_when_payload_missing_topic(self) -> None:
        tool_registry = build_default_agent_tool_registry()
        tool = tool_registry.get_by_intent("topic")
        assert tool is not None

        registry = AgentAssetExecutorRegistry()

        def _executor(_payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            return AgentAssetResult(intent="topic", status="success", payload={"topic": "ok"}, content="ok")

        registry.register("topic", _executor)
        orchestrator = AgentToolStageOrchestrator(
            stage_catalog=build_default_tool_stage_catalog(tool_registry=tool_registry)
        )
        result, stage_results = orchestrator.execute_tool(
            tool=tool,
            payload={},
            settings=self.settings,
            intent_router=_FakeIntentRouter(),  # type: ignore[arg-type]
            executor_registry=registry,
        )
        self.assertEqual(result.status, "error")
        self.assertTrue(any(stage.status == "error" for stage in stage_results))

    def test_strict_verify_failure_converts_success_to_error(self) -> None:
        tool_registry = build_default_agent_tool_registry()
        tool = tool_registry.get_by_intent("topic")
        assert tool is not None

        registry = AgentAssetExecutorRegistry()

        def _executor(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            return AgentAssetResult(intent="topic", status="success", payload=payload, content="short")

        registry.register("topic", _executor)
        orchestrator = AgentToolStageOrchestrator(
            stage_catalog=build_default_tool_stage_catalog(tool_registry=tool_registry)
        )
        result, stage_results = orchestrator.execute_tool(
            tool=tool,
            payload={"topic": "CDC Pipeline"},
            settings=self.settings,
            intent_router=_FakeIntentRouter(),  # type: ignore[arg-type]
            executor_registry=registry,
        )
        self.assertEqual(result.status, "error")
        self.assertIn("Verification failed", result.error)
        self.assertTrue(any(stage.stage_key == "verify_result" and stage.status == "error" for stage in stage_results))
        artifact = result.artifact if isinstance(result.artifact, dict) else {}
        provenance = artifact.get("provenance", {}) if isinstance(artifact.get("provenance"), dict) else {}
        self.assertTrue(isinstance(provenance.get("verification"), dict))

    def test_stage_durations_are_recorded(self) -> None:
        tool_registry = build_default_agent_tool_registry()
        tool = tool_registry.get_by_intent("topic")
        assert tool is not None
        registry = AgentAssetExecutorRegistry()

        def _executor(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            del payload
            time.sleep(0.001)
            return AgentAssetResult(
                intent="topic",
                status="success",
                payload={"topic": "ok"},
                content="This is a long enough topic explanation for verification stage.",
            )

        registry.register("topic", _executor)
        orchestrator = AgentToolStageOrchestrator(
            stage_catalog=build_default_tool_stage_catalog(tool_registry=tool_registry)
        )
        result, stage_results = orchestrator.execute_tool(
            tool=tool,
            payload={"topic": "CDC Pipeline"},
            settings=self.settings,
            intent_router=_FakeIntentRouter(),  # type: ignore[arg-type]
            executor_registry=registry,
        )
        self.assertEqual(result.status, "success")
        self.assertTrue(all(stage.duration_ms >= 0 for stage in stage_results))
        self.assertTrue(all(bool(stage.started_at) and bool(stage.ended_at) for stage in stage_results))
        self.assertTrue(any(stage.stage_key == "policy_gate_result" for stage in stage_results))

    def test_execute_stage_retry_and_timeout(self) -> None:
        old_retry = os.environ.get("EXECUTE_RETRY_COUNT")
        old_timeout = os.environ.get("EXECUTE_STAGE_TIMEOUT_MS")
        os.environ["EXECUTE_RETRY_COUNT"] = "1"
        os.environ["EXECUTE_STAGE_TIMEOUT_MS"] = "1"
        try:
            tool_registry = build_default_agent_tool_registry()
            tool = tool_registry.get_by_intent("topic")
            assert tool is not None
            registry = AgentAssetExecutorRegistry()
            state = {"count": 0}

            def _executor(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
                state["count"] += 1
                if state["count"] == 1:
                    return AgentAssetResult(intent="topic", status="error", payload=payload, error="temporary failure")
                time.sleep(0.003)
                return AgentAssetResult(
                    intent="topic",
                    status="success",
                    payload=payload,
                    content="This is a long enough topic explanation for verification stage.",
                )

            registry.register("topic", _executor)
            orchestrator = AgentToolStageOrchestrator(
                stage_catalog=build_default_tool_stage_catalog(tool_registry=tool_registry)
            )
            result, stage_results = orchestrator.execute_tool(
                tool=tool,
                payload={"topic": "CDC Pipeline"},
                settings=self.settings,
                intent_router=_FakeIntentRouter(),  # type: ignore[arg-type]
                executor_registry=registry,
            )
            self.assertEqual(result.status, "error")
            execute_stages = [stage for stage in stage_results if stage.stage_key == "execute_tool"]
            self.assertGreaterEqual(len(execute_stages), 1)
            self.assertTrue(any(stage.attempt > 1 or stage.error_code for stage in execute_stages))
            self.assertTrue(any(stage.error_code in {"E_EXECUTOR_FAILED", "E_STAGE_TIMEOUT"} for stage in execute_stages))
        finally:
            if old_retry is None:
                os.environ.pop("EXECUTE_RETRY_COUNT", None)
            else:
                os.environ["EXECUTE_RETRY_COUNT"] = old_retry
            if old_timeout is None:
                os.environ.pop("EXECUTE_STAGE_TIMEOUT_MS", None)
            else:
                os.environ["EXECUTE_STAGE_TIMEOUT_MS"] = old_timeout

    def test_schema_validation_failure_blocks_verify(self) -> None:
        tool_registry = build_default_agent_tool_registry()
        tool = tool_registry.get_by_intent("topic")
        assert tool is not None
        registry = AgentAssetExecutorRegistry()

        def _executor(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            return AgentAssetResult(intent="topic", status="success", payload=payload, content={"bad": "shape"})

        registry.register("topic", _executor)
        orchestrator = AgentToolStageOrchestrator(
            stage_catalog=build_default_tool_stage_catalog(tool_registry=tool_registry)
        )
        result, stage_results = orchestrator.execute_tool(
            tool=tool,
            payload={"topic": "CDC Pipeline"},
            settings=self.settings,
            intent_router=_FakeIntentRouter(),  # type: ignore[arg-type]
            executor_registry=registry,
        )
        self.assertEqual(result.status, "error")
        self.assertIn("Schema validation failed", result.error)
        self.assertTrue(any(stage.stage_key == "validate_schema" and stage.status == "error" for stage in stage_results))


if __name__ == "__main__":
    unittest.main()
