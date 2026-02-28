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

from main_app.services.agent_dashboard.plugin_sdk import (
    normalize_tool_plugin_spec,
    plugin_spec_fix_hints,
    default_capabilities_for_intent,
    validate_tool_plugin_spec,
    validate_workflow_plugin_spec,
)


class TestPluginSDK(unittest.TestCase):
    def test_invalid_tool_plugin_spec_rejected(self) -> None:
        result = validate_tool_plugin_spec({"plugin_key": "", "intent": "topic"})
        self.assertFalse(result.ok)

    def test_workflow_plugin_spec_validates(self) -> None:
        result = validate_workflow_plugin_spec(
            {"workflow_key": "w1", "tool_keys": ["topic"], "tool_dependencies": {}}
        )
        self.assertTrue(result.ok)

    def test_normalization_adds_defaults(self) -> None:
        normalized = normalize_tool_plugin_spec({"intent": "topic"})
        self.assertEqual(normalized.get("plugin_key"), "topic")
        self.assertTrue(isinstance(normalized.get("capabilities"), list))

    def test_fix_hints_for_incomplete_spec(self) -> None:
        hints = plugin_spec_fix_hints({"intent": ""})
        self.assertTrue(hints)
        self.assertTrue(any("plugin_key" in hint for hint in hints))

    def test_default_capabilities(self) -> None:
        self.assertIn("media", default_capabilities_for_intent("video"))


if __name__ == "__main__":
    unittest.main()
