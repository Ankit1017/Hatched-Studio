from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from main_app.infrastructure.mongo_base import MongoCollectionConfig, MongoCollectionProvider


class CacheStore(Protocol):
    def load(self) -> dict[str, Any]:
        ...

    def save(self, cache_data: dict[str, Any]) -> None:
        ...


class JsonFileCacheStore:
    def __init__(self, cache_file: Path) -> None:
        self._cache_file = cache_file

    def load(self) -> dict[str, Any]:
        if not self._cache_file.exists():
            return {}
        try:
            cache_data = json.loads(self._cache_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return cache_data if isinstance(cache_data, dict) else {}

    def save(self, cache_data: dict[str, Any]) -> None:
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache_file.write_text(
            json.dumps(cache_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class MongoCacheStore:
    def __init__(
        self,
        *,
        uri: str,
        db_name: str,
        collection_name: str = "llm_cache",
    ) -> None:
        self._provider = MongoCollectionProvider(
            MongoCollectionConfig(
                uri=uri,
                db_name=db_name,
                collection_name=collection_name,
            )
        )

    @property
    def description(self) -> str:
        return self._provider.description

    def load(self) -> dict[str, Any]:
        collection = self._provider.collection()
        cache_data: dict[str, Any] = {}
        for item in collection.find({}, {"_id": 1, "value": 1}):
            cache_key = str(item.get("_id", "")).strip()
            if not cache_key:
                continue
            cache_data[cache_key] = item.get("value")
        return cache_data

    def save(self, cache_data: dict[str, Any]) -> None:
        collection = self._provider.collection()
        collection.delete_many({})
        documents = [
            {"_id": str(cache_key), "value": value}
            for cache_key, value in cache_data.items()
            if str(cache_key).strip()
        ]
        if documents:
            collection.insert_many(documents, ordered=False)
