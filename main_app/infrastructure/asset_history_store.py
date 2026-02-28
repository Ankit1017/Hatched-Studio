from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from main_app.infrastructure.mongo_base import MongoCollectionConfig, MongoCollectionProvider


class AssetHistoryRepository(Protocol):
    def list_records(self) -> list[dict[str, Any]]:
        ...

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        ...

    def upsert_record(self, record_entry: dict[str, Any]) -> None:
        ...

    def save_records(self, records: list[dict[str, Any]]) -> None:
        ...


class AssetHistoryStore:
    def __init__(self, storage_file: Path) -> None:
        self._storage_file = storage_file

    def list_records(self) -> list[dict[str, Any]]:
        data = self._load_data()
        records = data.get("records", [])
        if not isinstance(records, list):
            return []
        normalized = [item for item in records if isinstance(item, dict)]
        return sorted(
            normalized,
            key=lambda item: str(item.get("created_at", "")),
            reverse=True,
        )

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        target = str(record_id).strip()
        if not target:
            return None
        for item in self.list_records():
            if str(item.get("id", "")).strip() == target:
                return item
        return None

    def upsert_record(self, record_entry: dict[str, Any]) -> None:
        record_id = str(record_entry.get("id", "")).strip()
        if not record_id:
            return

        records = self.list_records()
        replaced = False
        for idx, item in enumerate(records):
            if str(item.get("id", "")).strip() == record_id:
                records[idx] = record_entry
                replaced = True
                break

        if not replaced:
            records.append(record_entry)

        self.save_records(records)

    def save_records(self, records: list[dict[str, Any]]) -> None:
        payload = {"records": records}
        self._storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._storage_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_data(self) -> dict[str, Any]:
        if not self._storage_file.exists():
            return {"records": []}
        try:
            payload = json.loads(self._storage_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {"records": []}
        if not isinstance(payload, dict):
            return {"records": []}
        return payload


class MongoAssetHistoryStore:
    def __init__(
        self,
        *,
        uri: str,
        db_name: str,
        collection_name: str = "asset_history",
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

    def list_records(self) -> list[dict[str, Any]]:
        collection = self._provider.collection()
        records: list[dict[str, Any]] = []
        for item in collection.find({}, {"_id": 0, "record": 1}).sort("created_at_sort", -1):
            record = item.get("record")
            if isinstance(record, dict):
                records.append(record)
        return records

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        target = str(record_id).strip()
        if not target:
            return None
        collection = self._provider.collection()
        item = collection.find_one({"_id": target}, {"_id": 0, "record": 1})
        record = item.get("record") if isinstance(item, dict) else None
        return record if isinstance(record, dict) else None

    def upsert_record(self, record_entry: dict[str, Any]) -> None:
        record_id = str(record_entry.get("id", "")).strip()
        if not record_id:
            return
        collection = self._provider.collection()
        collection.replace_one(
            {"_id": record_id},
            {
                "_id": record_id,
                "created_at_sort": str(record_entry.get("created_at", "")),
                "record": dict(record_entry),
            },
            upsert=True,
        )

    def save_records(self, records: list[dict[str, Any]]) -> None:
        collection = self._provider.collection()
        collection.delete_many({})
        documents: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            record_id = str(record.get("id", "")).strip()
            if not record_id:
                continue
            documents.append(
                {
                    "_id": record_id,
                    "created_at_sort": str(record.get("created_at", "")),
                    "record": dict(record),
                }
            )
        if documents:
            collection.insert_many(documents, ordered=False)
