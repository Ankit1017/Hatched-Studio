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

from main_app.services.agent_dashboard.tool_registry import build_default_agent_tool_registry


class TestToolRegistryExecutionSpecs(unittest.TestCase):
    def test_default_tools_include_execution_specs(self) -> None:
        registry = build_default_agent_tool_registry()
        tools = registry.list_tools()
        self.assertTrue(tools)

        for tool in tools:
            with self.subTest(tool=tool.key):
                spec = tool.execution_spec
                self.assertEqual(spec.get("intent"), tool.intent)
                self.assertEqual(spec.get("tool_key"), tool.key)
                self.assertTrue(str(spec.get("requirements_schema_key", "")).strip())
                self.assertTrue(str(spec.get("verify_profile", "")).strip())
                self.assertTrue(bool(spec.get("verify_required", False)))
                execution_policy = spec.get("execution_policy", {})
                self.assertIsInstance(execution_policy, dict)
                self.assertIn("max_retries", execution_policy)
                self.assertIn("fail_policy", execution_policy)
                dependency = spec.get("dependency", {})
                self.assertIsInstance(dependency.get("requires_artifacts", []), list)
                self.assertIsInstance(dependency.get("produces_artifacts", []), list)
                self.assertIsInstance(dependency.get("optional_requires", []), list)
                self.assertTrue(str(tool.schema_ref.get("version", "")).strip())
        plugin_specs = registry.list_plugin_specs()
        self.assertEqual(len(plugin_specs), len(tools))
        for spec in plugin_specs:
            with self.subTest(plugin=spec.get("plugin_key", "")):
                self.assertTrue(isinstance(spec.get("capabilities", []), list))


if __name__ == "__main__":
    unittest.main()
