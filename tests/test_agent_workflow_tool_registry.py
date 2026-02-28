from __future__ import annotations

import unittest

from main_app.services.agent_dashboard.tool_registry import build_default_agent_tool_registry
from main_app.services.agent_dashboard.workflow_registry import build_default_agent_workflow_registry


class TestAgentWorkflowAndToolRegistry(unittest.TestCase):
    def test_default_tool_registry_covers_all_asset_intents(self) -> None:
        registry = build_default_agent_tool_registry()
        tools = registry.list_tools()
        intents = {tool.intent for tool in tools}
        self.assertIn("topic", intents)
        self.assertIn("video", intents)
        self.assertIn("audio_overview", intents)
        self.assertIn("report", intents)

    def test_resolve_tools_for_intents_reports_unresolved(self) -> None:
        registry = build_default_agent_tool_registry()
        resolved, unresolved = registry.resolve_tools_for_intents(["topic", "unknown_intent", "video"])
        self.assertEqual([tool.intent for tool in resolved], ["topic", "video"])
        self.assertEqual(unresolved, ["unknown_intent"])

    def test_default_workflow_registry_includes_core_workflows(self) -> None:
        registry = build_default_agent_workflow_registry()
        keys = {item.key for item in registry.list_workflows()}
        self.assertIn("core_learning_assets", keys)
        self.assertIn("media_production_assets", keys)
        self.assertIn("full_asset_suite", keys)


if __name__ == "__main__":
    unittest.main()
