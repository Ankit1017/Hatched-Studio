from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main_app.infrastructure.agent_dashboard_session_store import (
    AgentDashboardSessionStore,
    MongoAgentDashboardSessionStore,
)
from main_app.infrastructure.asset_history_store import AssetHistoryStore, MongoAssetHistoryStore
from main_app.infrastructure.cache_store import JsonFileCacheStore, MongoCacheStore
from main_app.infrastructure.quiz_history_store import MongoQuizHistoryStore, QuizHistoryStore


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export local JSON stores from `.cache/` to MongoDB.",
    )
    parser.add_argument(
        "--uri",
        default=os.getenv("MONGODB_URI", "").strip(),
        help="MongoDB URI. Defaults to env MONGODB_URI.",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("MONGODB_DB", "knowledge_app").strip() or "knowledge_app",
        help="MongoDB database name. Defaults to env MONGODB_DB or `knowledge_app`.",
    )
    parser.add_argument(
        "--cache-file",
        default=".cache/llm_cache.json",
        help="Path to JSON LLM cache file.",
    )
    parser.add_argument(
        "--asset-history-file",
        default=".cache/asset_history.json",
        help="Path to JSON asset history file.",
    )
    parser.add_argument(
        "--quiz-history-file",
        default=".cache/quiz_history.json",
        help="Path to JSON quiz history file.",
    )
    parser.add_argument(
        "--sessions-file",
        default=".cache/agent_dashboard_sessions.json",
        help="Path to JSON agent dashboard sessions file.",
    )
    parser.add_argument(
        "--cache-collection",
        default=os.getenv("MONGODB_COLLECTION_CACHE", "llm_cache").strip() or "llm_cache",
        help="MongoDB collection for cache metadata.",
    )
    parser.add_argument(
        "--asset-collection",
        default=(
            os.getenv("MONGODB_COLLECTION_ASSET_HISTORY", "asset_history").strip()
            or "asset_history"
        ),
        help="MongoDB collection for asset history.",
    )
    parser.add_argument(
        "--quiz-collection",
        default=(
            os.getenv("MONGODB_COLLECTION_QUIZ_HISTORY", "quiz_history").strip()
            or "quiz_history"
        ),
        help="MongoDB collection for quiz history.",
    )
    parser.add_argument(
        "--sessions-collection",
        default=(
            os.getenv("MONGODB_COLLECTION_AGENT_SESSIONS", "agent_dashboard_sessions").strip()
            or "agent_dashboard_sessions"
        ),
        help="MongoDB collection for agent dashboard sessions.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be exported, do not write to MongoDB.",
    )
    return parser


def _safe_path(value: str) -> Path:
    return Path(str(value).strip()).expanduser()


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    mongo_uri = str(args.uri).strip()
    if not mongo_uri:
        parser.error("MongoDB URI is required. Pass --uri or set MONGODB_URI.")

    cache_file = _safe_path(args.cache_file)
    asset_history_file = _safe_path(args.asset_history_file)
    quiz_history_file = _safe_path(args.quiz_history_file)
    sessions_file = _safe_path(args.sessions_file)

    json_cache_store = JsonFileCacheStore(cache_file)
    json_asset_store = AssetHistoryStore(asset_history_file)
    json_quiz_store = QuizHistoryStore(quiz_history_file)
    json_sessions_store = AgentDashboardSessionStore(sessions_file)

    source_cache = json_cache_store.load()
    source_assets = json_asset_store.list_records()
    source_quizzes = json_quiz_store.list_quizzes()
    source_sessions = json_sessions_store.list_sessions()

    print("JSON source summary")
    print(f"- cache entries: {len(source_cache)} ({cache_file})")
    print(f"- asset history records: {len(source_assets)} ({asset_history_file})")
    print(f"- quiz history records: {len(source_quizzes)} ({quiz_history_file})")
    print(f"- agent sessions: {len(source_sessions)} ({sessions_file})")

    if args.dry_run:
        print("\nDry run complete. No data was written to MongoDB.")
        return 0

    mongo_cache_store = MongoCacheStore(
        uri=mongo_uri,
        db_name=str(args.db),
        collection_name=str(args.cache_collection),
    )
    mongo_asset_store = MongoAssetHistoryStore(
        uri=mongo_uri,
        db_name=str(args.db),
        collection_name=str(args.asset_collection),
    )
    mongo_quiz_store = MongoQuizHistoryStore(
        uri=mongo_uri,
        db_name=str(args.db),
        collection_name=str(args.quiz_collection),
    )
    mongo_sessions_store = MongoAgentDashboardSessionStore(
        uri=mongo_uri,
        db_name=str(args.db),
        collection_name=str(args.sessions_collection),
    )

    # Merge cache to avoid dropping existing Mongo-only entries.
    merged_cache = dict(mongo_cache_store.load())
    merged_cache.update(source_cache)
    mongo_cache_store.save(merged_cache)

    for item in source_assets:
        if isinstance(item, dict):
            mongo_asset_store.upsert_record(item)
    for item in source_quizzes:
        if isinstance(item, dict):
            mongo_quiz_store.upsert_quiz(item)
    for item in source_sessions:
        if isinstance(item, dict):
            mongo_sessions_store.upsert_session(item)

    print("\nExport completed successfully.")
    print(f"- cache entries upserted: {len(source_cache)}")
    print(f"- asset history upserted: {len(source_assets)}")
    print(f"- quiz history upserted: {len(source_quizzes)}")
    print(f"- sessions upserted: {len(source_sessions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
