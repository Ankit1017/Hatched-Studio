from __future__ import annotations

import sys
import types
import unittest

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(choices=[])))

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

from main_app.models import GroqSettings
from main_app.services.agent_dashboard.executor_plugins.parsed_asset_result import (
    build_artifact_result,
)
from tests.test_integration_full_flows import (  # type: ignore[attr-defined]
    _asset_payloads,
    _build_harness,
    _ScriptedLLMService,
    _valid_responses_by_task,
)


class TestExecutorPluginsGenericResult(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = GroqSettings(
            api_key="test-key",
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=512,
        )

    def test_build_artifact_result_sets_artifact(self) -> None:
        result = build_artifact_result(
            intent="topic",
            payload={"topic": "CDC"},
            status="success",
            title="Detailed Description: CDC",
            content="CDC means change data capture.",
        )
        self.assertIsInstance(result.artifact, dict)
        assert result.artifact is not None
        self.assertEqual(result.artifact.get("intent"), "topic")
        self.assertTrue(isinstance(result.artifact.get("sections"), list))
        metrics = result.artifact.get("metrics", {})
        self.assertTrue(isinstance(metrics, dict))
        self.assertIn("cache_hit", metrics)

    def test_all_default_executors_emit_artifact(self) -> None:
        llm = _ScriptedLLMService(responses_by_task=_valid_responses_by_task())
        harness = _build_harness(llm)
        for intent, payload in _asset_payloads().items():
            with self.subTest(intent=intent):
                result = harness.registry.execute(intent=intent, payload=payload, settings=self.settings)
                self.assertEqual(result.status, "success")
                self.assertIsInstance(result.artifact, dict)
                assert result.artifact is not None
                self.assertTrue(isinstance(result.artifact.get("sections"), list))
                self.assertIn("metrics", result.artifact)


if __name__ == "__main__":
    unittest.main()
