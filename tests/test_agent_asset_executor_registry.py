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

from main_app.models import AgentAssetResult, GroqSettings
from main_app.services.agent_dashboard.asset_executor_registry import (
    AgentAssetExecutorRegistry,
    AssetExecutorRegistration,
)


class TestAgentAssetExecutorRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = GroqSettings(
            api_key="test-key",
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=256,
        )

    def test_execute_registered_intent(self) -> None:
        registry = AgentAssetExecutorRegistry()

        def topic_executor(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            return AgentAssetResult(
                intent="topic",
                status="success",
                payload=payload,
                content=f"Explained: {payload.get('topic', '')}",
            )

        registry.register("topic", topic_executor)
        result = registry.execute(intent="topic", payload={"topic": "CDC Pipeline"}, settings=self.settings)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.intent, "topic")
        self.assertEqual(result.payload["topic"], "CDC Pipeline")

    def test_execute_unsupported_intent(self) -> None:
        registry = AgentAssetExecutorRegistry()
        result = registry.execute(intent="unknown", payload={"topic": "X"}, settings=self.settings)

        self.assertEqual(result.status, "error")
        self.assertIn("Unsupported intent", result.error)

    def test_execute_catches_executor_exception(self) -> None:
        registry = AgentAssetExecutorRegistry()

        def broken_executor(_payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            raise RuntimeError("boom")

        registry.register("topic", broken_executor)
        result = registry.execute(intent="topic", payload={"topic": "X"}, settings=self.settings)

        self.assertEqual(result.status, "error")
        self.assertIn("Generation failed", result.error)

    def test_register_many_registers_multiple_executors(self) -> None:
        registry = AgentAssetExecutorRegistry()

        def topic_executor(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            return AgentAssetResult(intent="topic", status="success", payload=payload, content="topic ok")

        def report_executor(payload: dict[str, object], _settings: GroqSettings) -> AgentAssetResult:
            return AgentAssetResult(intent="report", status="success", payload=payload, content="report ok")

        registry.register_many(
            [
                AssetExecutorRegistration(intent="topic", executor=topic_executor),
                AssetExecutorRegistration(intent="report", executor=report_executor),
            ]
        )

        topic_result = registry.execute(intent="topic", payload={"topic": "CDC"}, settings=self.settings)
        report_result = registry.execute(intent="report", payload={"topic": "CDC"}, settings=self.settings)

        self.assertEqual(topic_result.status, "success")
        self.assertEqual(report_result.status, "success")


if __name__ == "__main__":
    unittest.main()
