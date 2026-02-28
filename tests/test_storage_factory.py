from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main_app.infrastructure.agent_dashboard_session_store import AgentDashboardSessionStore
from main_app.infrastructure.asset_history_store import AssetHistoryStore
from main_app.infrastructure.cache_store import JsonFileCacheStore
from main_app.infrastructure.quiz_history_store import QuizHistoryStore
from main_app.infrastructure.storage_factory import build_storage_bundle


class StorageFactoryTests(unittest.TestCase):
    def test_build_storage_bundle_json_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {"APP_STORE_BACKEND": "json"},
                clear=False,
            ):
                bundle = build_storage_bundle(
                    cache_file=Path(temp_dir) / "llm_cache.json",
                    asset_history_file=Path(temp_dir) / "asset_history.json",
                    quiz_history_file=Path(temp_dir) / "quiz_history.json",
                    agent_dashboard_sessions_file=Path(temp_dir) / "sessions.json",
                )

        self.assertIsInstance(bundle.cache_store, JsonFileCacheStore)
        self.assertIsInstance(bundle.asset_history_store, AssetHistoryStore)
        self.assertIsInstance(bundle.quiz_history_store, QuizHistoryStore)
        self.assertIsInstance(bundle.agent_dashboard_session_store, AgentDashboardSessionStore)

    def test_build_storage_bundle_auto_without_mongo_uri_uses_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_updates = {"APP_STORE_BACKEND": "auto", "MONGODB_URI": ""}
            with patch.dict(os.environ, env_updates, clear=False):
                bundle = build_storage_bundle(
                    cache_file=Path(temp_dir) / "llm_cache.json",
                    asset_history_file=Path(temp_dir) / "asset_history.json",
                    quiz_history_file=Path(temp_dir) / "quiz_history.json",
                    agent_dashboard_sessions_file=Path(temp_dir) / "sessions.json",
                )

        self.assertIsInstance(bundle.cache_store, JsonFileCacheStore)
        self.assertIsInstance(bundle.asset_history_store, AssetHistoryStore)
        self.assertIsInstance(bundle.quiz_history_store, QuizHistoryStore)
        self.assertIsInstance(bundle.agent_dashboard_session_store, AgentDashboardSessionStore)

    def test_build_storage_bundle_mongo_mode_requires_uri(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_updates = {"APP_STORE_BACKEND": "mongo", "MONGODB_URI": ""}
            with patch.dict(os.environ, env_updates, clear=False):
                with self.assertRaises(RuntimeError):
                    build_storage_bundle(
                        cache_file=Path(temp_dir) / "llm_cache.json",
                        asset_history_file=Path(temp_dir) / "asset_history.json",
                        quiz_history_file=Path(temp_dir) / "quiz_history.json",
                        agent_dashboard_sessions_file=Path(temp_dir) / "sessions.json",
                    )


if __name__ == "__main__":
    unittest.main()
