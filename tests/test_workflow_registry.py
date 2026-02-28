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
from main_app.services.agent_dashboard.workflow_registry import (
    AgentWorkflowDefinition,
    AgentWorkflowRegistry,
    build_default_agent_workflow_registry,
)


class TestWorkflowRegistryDag(unittest.TestCase):
    def test_plan_selected_workflow_resolves_video_after_slideshow(self) -> None:
        tool_registry = build_default_agent_tool_registry()
        workflow_registry = build_default_agent_workflow_registry()
        selected_tools = [tool_registry.get_by_intent("video"), tool_registry.get_by_intent("slideshow")]
        selected_tools = [tool for tool in selected_tools if tool is not None]
        workflow = workflow_registry.build_plan_selected_workflow(tools=selected_tools)
        ordered_tools, notes = workflow_registry.resolve_workflow_tools_dag(
            workflow=workflow,
            tool_registry=tool_registry,
        )
        self.assertFalse(notes)
        self.assertEqual([tool.intent for tool in ordered_tools], ["slideshow", "video"])

    def test_cycle_is_reported(self) -> None:
        tool_registry = build_default_agent_tool_registry()
        registry = AgentWorkflowRegistry(
            workflows=[
                AgentWorkflowDefinition(
                    key="cycle_test",
                    title="Cycle Test",
                    description="Cycle",
                    tool_keys=["topic", "quiz"],
                    tool_dependencies={"topic": ["quiz"], "quiz": ["topic"]},
                )
            ]
        )
        workflow = registry.get("cycle_test")
        assert workflow is not None
        ordered_tools, notes = registry.resolve_workflow_tools_dag(
            workflow=workflow,
            tool_registry=tool_registry,
        )
        self.assertEqual({tool.intent for tool in ordered_tools}, {"topic", "quiz"})
        self.assertTrue(any("cycle" in note.lower() for note in notes))


if __name__ == "__main__":
    unittest.main()
