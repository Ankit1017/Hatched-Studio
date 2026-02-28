from __future__ import annotations

import sys
import types
import unittest
from typing import Any

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")

    class _GroqStub:
        def __init__(self, *args, **kwargs):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(choices=[])))

    groq_stub.Groq = _GroqStub
    sys.modules["groq"] = groq_stub

from main_app.ui.agent_dashboard.session_manager import AgentDashboardSessionManager


class _InMemorySessionStore:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def list_sessions(self) -> list[dict[str, Any]]:
        return sorted(self._records.values(), key=lambda item: str(item.get("updated_at", "")), reverse=True)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return self._records.get(session_id)

    def upsert_session(self, session_record: dict[str, Any]) -> None:
        session_id = str(session_record.get("id", "")).strip()
        if not session_id:
            return
        self._records[session_id] = dict(session_record)

    def delete_session(self, session_id: str) -> None:
        self._records.pop(session_id, None)


class _StateGateway:
    def __init__(self, seed: dict[str, Any] | None = None) -> None:
        self.data: dict[str, Any] = dict(seed or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def setdefault(self, key: str, default: Any) -> Any:
        return self.data.setdefault(key, default)


class AgentDashboardSessionManagerTests(unittest.TestCase):
    def test_start_fresh_session_sets_expected_defaults(self) -> None:
        store = _InMemorySessionStore()
        state = _StateGateway()
        manager = AgentDashboardSessionManager(store, state=state)

        manager.start_fresh_session()

        self.assertIsInstance(state.get("agent_dashboard_session_id"), str)
        self.assertEqual(len(state.get("agent_dashboard_session_id")), 16)
        self.assertEqual(state.get("agent_dashboard_history"), [])
        self.assertIsNone(state.get("agent_dashboard_pending_plan"))
        self.assertEqual(state.get("agent_dashboard_active_topic"), "")
        self.assertEqual(state.get("agent_dashboard_recent_topics"), [])
        self.assertTrue(state.get("agent_dashboard_force_sync_saved_selector"))
        self.assertTrue(state.get("agent_dashboard_force_sync_planner_selector"))

    def test_restore_resolves_active_topic_from_history_payloads(self) -> None:
        store = _InMemorySessionStore()
        state = _StateGateway({"agent_dashboard_planner_mode": "Local First (No LLM if possible)"})
        manager = AgentDashboardSessionManager(store, state=state)

        record = {
            "id": "abc123session",
            "created_at": "2026-02-14T00:00:00+00:00",
            "updated_at": "2026-02-14T00:00:01+00:00",
            "title": "Agent Session",
            "planner_mode": "invalid",
            "active_topic": "topic",
            "recent_topics": ["quiz"],
            "history": [
                {
                    "role": "assistant",
                    "payloads": {
                        "mindmap": {"topic": "CDC Pipeline"},
                    },
                }
            ],
        }

        manager.restore_session_from_store_record(record)

        self.assertEqual(state.get("agent_dashboard_session_id"), "abc123session")
        self.assertEqual(state.get("agent_dashboard_active_topic"), "CDC Pipeline")
        self.assertEqual(state.get("agent_dashboard_selected_saved_session_id"), "abc123session")
        self.assertEqual(state.get("agent_dashboard_planner_mode"), "Local First (No LLM if possible)")

    def test_persist_current_session_upserts_record_and_tracks_selection(self) -> None:
        store = _InMemorySessionStore()
        session_id = "persist1234567890"[:16]
        state = _StateGateway(
            {
                "agent_dashboard_history": [{"role": "user", "text": "Explain CDC"}],
                "agent_dashboard_pending_plan": None,
                "agent_dashboard_active_topic": "CDC Pipeline",
                "agent_dashboard_recent_topics": ["CDC Pipeline"],
                "agent_dashboard_session_id": session_id,
                "agent_dashboard_session_created_at": "2026-02-14T00:00:00+00:00",
                "agent_dashboard_planner_mode": "Local First (No LLM if possible)",
            }
        )
        manager = AgentDashboardSessionManager(store, state=state)

        manager.persist_current_session()

        record = store.get_session(session_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.get("active_topic"), "CDC Pipeline")
        self.assertEqual(record.get("title"), "CDC Pipeline")
        self.assertEqual(state.get("agent_dashboard_selected_saved_session_id"), session_id)


if __name__ == "__main__":
    unittest.main()
