from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path

from main_app.infrastructure.agent_dashboard_session_store import (
    AgentDashboardSessionRepository,
    AgentDashboardSessionStore,
    MongoAgentDashboardSessionStore,
)
from main_app.infrastructure.asset_history_store import (
    AssetHistoryRepository,
    AssetHistoryStore,
    MongoAssetHistoryStore,
)
from main_app.infrastructure.cache_store import CacheStore, JsonFileCacheStore, MongoCacheStore
from main_app.infrastructure.quiz_history_store import (
    MongoQuizHistoryStore,
    QuizHistoryRepository,
    QuizHistoryStore,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StorageBundle:
    cache_store: CacheStore
    cache_label: str
    asset_history_store: AssetHistoryRepository
    quiz_history_store: QuizHistoryRepository
    agent_dashboard_session_store: AgentDashboardSessionRepository


def build_storage_bundle(
    *,
    cache_file: Path,
    asset_history_file: Path,
    quiz_history_file: Path,
    agent_dashboard_sessions_file: Path,
) -> StorageBundle:
    mode = _storage_mode()
    if mode == "json":
        return _build_json_bundle(
            cache_file=cache_file,
            asset_history_file=asset_history_file,
            quiz_history_file=quiz_history_file,
            agent_dashboard_sessions_file=agent_dashboard_sessions_file,
        )

    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        if mode == "mongo":
            raise RuntimeError("MONGODB_URI is required when APP_STORE_BACKEND is set to `mongo`.")
        return _build_json_bundle(
            cache_file=cache_file,
            asset_history_file=asset_history_file,
            quiz_history_file=quiz_history_file,
            agent_dashboard_sessions_file=agent_dashboard_sessions_file,
        )

    try:
        mongo_bundle = _build_mongo_bundle(uri=uri)
        _warm_up_mongo_bundle(mongo_bundle)
        _migrate_json_to_mongo_if_needed(
            mongo_bundle=mongo_bundle,
            cache_file=cache_file,
            asset_history_file=asset_history_file,
            quiz_history_file=quiz_history_file,
            agent_dashboard_sessions_file=agent_dashboard_sessions_file,
        )
        return mongo_bundle
    except Exception as exc:  # noqa: BLE001
        if mode == "mongo":
            raise
        logger.exception("MongoDB storage unavailable; falling back to JSON stores: %s", exc)
        return _build_json_bundle(
            cache_file=cache_file,
            asset_history_file=asset_history_file,
            quiz_history_file=quiz_history_file,
            agent_dashboard_sessions_file=agent_dashboard_sessions_file,
        )


def _storage_mode() -> str:
    raw_mode = " ".join(str(os.getenv("APP_STORE_BACKEND", "auto")).strip().lower().split())
    if raw_mode in {"json", "mongo"}:
        return raw_mode
    return "auto"


def _build_json_bundle(
    *,
    cache_file: Path,
    asset_history_file: Path,
    quiz_history_file: Path,
    agent_dashboard_sessions_file: Path,
) -> StorageBundle:
    return StorageBundle(
        cache_store=JsonFileCacheStore(cache_file),
        cache_label=str(cache_file),
        asset_history_store=AssetHistoryStore(asset_history_file),
        quiz_history_store=QuizHistoryStore(quiz_history_file),
        agent_dashboard_session_store=AgentDashboardSessionStore(agent_dashboard_sessions_file),
    )


def _build_mongo_bundle(*, uri: str) -> StorageBundle:
    db_name = str(os.getenv("MONGODB_DB", "knowledge_app")).strip() or "knowledge_app"
    cache_collection = str(os.getenv("MONGODB_COLLECTION_CACHE", "llm_cache")).strip() or "llm_cache"
    asset_collection = (
        str(os.getenv("MONGODB_COLLECTION_ASSET_HISTORY", "asset_history")).strip() or "asset_history"
    )
    quiz_collection = str(os.getenv("MONGODB_COLLECTION_QUIZ_HISTORY", "quiz_history")).strip() or "quiz_history"
    sessions_collection = (
        str(os.getenv("MONGODB_COLLECTION_AGENT_SESSIONS", "agent_dashboard_sessions")).strip()
        or "agent_dashboard_sessions"
    )

    cache_store = MongoCacheStore(
        uri=uri,
        db_name=db_name,
        collection_name=cache_collection,
    )
    return StorageBundle(
        cache_store=cache_store,
        cache_label=cache_store.description,
        asset_history_store=MongoAssetHistoryStore(
            uri=uri,
            db_name=db_name,
            collection_name=asset_collection,
        ),
        quiz_history_store=MongoQuizHistoryStore(
            uri=uri,
            db_name=db_name,
            collection_name=quiz_collection,
        ),
        agent_dashboard_session_store=MongoAgentDashboardSessionStore(
            uri=uri,
            db_name=db_name,
            collection_name=sessions_collection,
        ),
    )


def _warm_up_mongo_bundle(bundle: StorageBundle) -> None:
    bundle.cache_store.load()
    bundle.asset_history_store.list_records()
    bundle.quiz_history_store.list_quizzes()
    bundle.agent_dashboard_session_store.list_sessions()


def _migrate_json_to_mongo_if_needed(
    *,
    mongo_bundle: StorageBundle,
    cache_file: Path,
    asset_history_file: Path,
    quiz_history_file: Path,
    agent_dashboard_sessions_file: Path,
) -> None:
    json_bundle = _build_json_bundle(
        cache_file=cache_file,
        asset_history_file=asset_history_file,
        quiz_history_file=quiz_history_file,
        agent_dashboard_sessions_file=agent_dashboard_sessions_file,
    )

    target_cache = mongo_bundle.cache_store.load()
    source_cache = json_bundle.cache_store.load()
    if not target_cache and source_cache:
        mongo_bundle.cache_store.save(source_cache)
        logger.info("Migrated %s cache entries from JSON to MongoDB.", len(source_cache))

    target_assets = mongo_bundle.asset_history_store.list_records()
    source_assets = json_bundle.asset_history_store.list_records()
    if not target_assets and source_assets:
        mongo_bundle.asset_history_store.save_records(source_assets)
        logger.info("Migrated %s asset history records from JSON to MongoDB.", len(source_assets))

    target_quizzes = mongo_bundle.quiz_history_store.list_quizzes()
    source_quizzes = json_bundle.quiz_history_store.list_quizzes()
    if not target_quizzes and source_quizzes:
        mongo_bundle.quiz_history_store.save_quizzes(source_quizzes)
        logger.info("Migrated %s quiz history records from JSON to MongoDB.", len(source_quizzes))

    target_sessions = mongo_bundle.agent_dashboard_session_store.list_sessions()
    source_sessions = json_bundle.agent_dashboard_session_store.list_sessions()
    if not target_sessions and source_sessions:
        mongo_bundle.agent_dashboard_session_store.save_sessions(source_sessions)
        logger.info("Migrated %s agent dashboard sessions from JSON to MongoDB.", len(source_sessions))
