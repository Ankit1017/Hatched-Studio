from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MongoCollectionConfig:
    uri: str
    db_name: str
    collection_name: str
    connect_timeout_ms: int = 3000


class MongoCollectionProvider:
    def __init__(self, config: MongoCollectionConfig) -> None:
        self._config = config
        self._client: Any | None = None
        self._collection: Any | None = None

    @property
    def description(self) -> str:
        return f"mongodb://{self._config.db_name}.{self._config.collection_name}"

    def collection(self) -> Any:
        if self._collection is not None:
            return self._collection

        try:
            from pymongo import MongoClient  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "MongoDB storage requires `pymongo`. Install dependencies and retry."
            ) from exc

        self._client = MongoClient(
            self._config.uri,
            serverSelectionTimeoutMS=int(self._config.connect_timeout_ms),
        )
        self._collection = self._client[self._config.db_name][self._config.collection_name]
        return self._collection
