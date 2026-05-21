"""Memory storage primitives for Isla."""

from __future__ import annotations

import hashlib
import json
import importlib
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    chromadb = importlib.import_module("chromadb")
except Exception:  # pragma: no cover - optional dependency
    chromadb = None


def _normalize_memory_root(path: Path) -> Path:
    if path.suffix and not path.is_dir():
        return path.parent / path.stem

    return path


def _default_store_path() -> Path:
    env_root = os.getenv("ISLA_MEMORY_ROOT", "").strip()
    env_path = os.getenv("ISLA_MEMORY_PATH", "").strip()

    if env_root:
        return _normalize_memory_root(Path(env_root).expanduser().resolve())

    if env_path:
        return _normalize_memory_root(Path(env_path).expanduser().resolve())

    # Keep memory in a stable repo-root location across runs.
    return Path(__file__).resolve().parents[2] / ".isla_memory"


class LocalHashEmbeddingFunction:
    """Low-cost local embedding function for ChromaDB persistence."""

    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in input]

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[a-z0-9']+", text.lower())

        if not tokens and text.strip():
            tokens = [text.lower().strip()]

        for token in tokens:
            index_seed = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(index_seed[:4], "big") % self.dimension
            vector[index] += 1.0

        norm = sum(value * value for value in vector) ** 0.5
        if norm:
            vector = [value / norm for value in vector]

        return vector


@dataclass(slots=True)
class MemoryItem:
    key: str
    value: str
    layer: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    flagged: bool = False


@dataclass(slots=True)
class MemoryStore:
    """Stores structured facts in SQLite and semantic text in ChromaDB."""

    store_path: Path = field(default_factory=_default_store_path)
    _sqlite_connection: sqlite3.Connection | None = field(init=False, default=None, repr=False)
    _collection: Any | None = field(init=False, default=None, repr=False)
    _legacy_migrated: bool = field(init=False, default=False, repr=False)

    def __post_init__(self) -> None:
        self.store_path = _normalize_memory_root(self.store_path.expanduser().resolve())

    def _ensure_root(self) -> None:
        self.store_path.mkdir(parents=True, exist_ok=True)

    def _sqlite_path(self) -> Path:
        return self.store_path / "memory.sqlite3"

    def _legacy_jsonl_path(self) -> Path:
        return self.store_path.with_suffix(".jsonl")

    def _ensure_sqlite(self) -> sqlite3.Connection:
        if self._sqlite_connection is not None:
            return self._sqlite_connection

        self._ensure_root()
        connection = sqlite3.connect(self._sqlite_path())
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_key TEXT NOT NULL,
                value TEXT NOT NULL,
                layer TEXT NOT NULL,
                created_at TEXT NOT NULL,
                flagged INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_key_created_at ON memories(memory_key, created_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC)"
        )
        connection.commit()
        self._sqlite_connection = connection
        self._migrate_legacy_jsonl_if_needed(connection)
        return connection

    def _ensure_collection(self) -> Any | None:
        if self._collection is not None:
            return self._collection

        if chromadb is None:  # pragma: no cover - optional dependency
            return None

        self._ensure_root()
        client = chromadb.PersistentClient(path=str(self.store_path / "chroma"))
        self._collection = client.get_or_create_collection(
            name="isla_memory",
            embedding_function=LocalHashEmbeddingFunction(),
        )
        return self._collection

    def _serialize_item(self, item: MemoryItem) -> dict[str, object]:
        return {
            "key": item.key,
            "value": item.value,
            "layer": item.layer,
            "created_at": item.created_at.isoformat(),
            "flagged": item.flagged,
        }

    def _deserialize_row(self, row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            key=str(row["memory_key"]),
            value=str(row["value"]),
            layer=str(row["layer"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            flagged=bool(row["flagged"]),
        )

    def _store_in_sqlite(self, item: MemoryItem, connection: sqlite3.Connection | None = None) -> None:
        sqlite_connection = connection or self._ensure_sqlite()
        sqlite_connection.execute(
            """
            INSERT INTO memories (memory_key, value, layer, created_at, flagged)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item.key, item.value, item.layer, item.created_at.isoformat(), int(item.flagged)),
        )
        sqlite_connection.commit()

    def _store_in_chroma(self, item: MemoryItem) -> None:
        collection = self._ensure_collection()
        if collection is None:
            return

        collection.add(
            ids=[f"{item.created_at.isoformat(timespec='microseconds')}-{uuid.uuid4().hex}"],
            documents=[f"key: {item.key}\nlayer: {item.layer}\nvalue: {item.value}"],
            metadatas=[
                {
                    "key": item.key,
                    "value": item.value,
                    "layer": item.layer,
                    "created_at": item.created_at.isoformat(),
                    "flagged": int(item.flagged),
                }
            ],
        )

    def _migrate_legacy_jsonl_if_needed(self, connection: sqlite3.Connection) -> None:
        if self._legacy_migrated:
            return

        legacy_path = self._legacy_jsonl_path()
        if not legacy_path.exists():
            self._legacy_migrated = True
            return

        row = connection.execute("SELECT COUNT(*) AS count FROM memories").fetchone()
        if row is not None and int(row["count"]) > 0:
            self._legacy_migrated = True
            return

        with legacy_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue

                record = json.loads(stripped)
                item = MemoryItem(
                    key=str(record["key"]),
                    value=str(record["value"]),
                    layer=str(record["layer"]),
                    created_at=datetime.fromisoformat(str(record["created_at"])),
                    flagged=bool(record.get("flagged", False)),
                )
                self._store_in_sqlite(item, connection=connection)
                self._store_in_chroma(item)

        self._legacy_migrated = True

    def _recent_rows(self, limit: int) -> list[sqlite3.Row]:
        connection = self._ensure_sqlite()
        return list(
            connection.execute(
                """
                SELECT memory_key, value, layer, created_at, flagged
                FROM memories
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (limit,),
            )
        )

    def _keyword_rows(self, query: str, limit: int) -> list[sqlite3.Row]:
        connection = self._ensure_sqlite()
        return list(
            connection.execute(
                """
                SELECT memory_key, value, layer, created_at, flagged
                FROM memories
                WHERE lower(memory_key) LIKE ?
                   OR lower(value) LIKE ?
                   OR lower(layer) LIKE ?
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            )
        )

    def _semantic_items(self, query: str, limit: int) -> list[MemoryItem]:
        collection = self._ensure_collection()
        if collection is None:
            return []

        try:
            result = collection.query(
                query_texts=[query],
                n_results=max(limit * 2, limit),
                include=["documents", "metadatas", "distances"],
            )
        except Exception:  # pragma: no cover - chroma optional / backend-dependent
            return []

        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        items: list[MemoryItem] = []

        for index, metadata_group in enumerate(metadatas):
            document_group = documents[index] if index < len(documents) else []
            for item_index, metadata in enumerate(metadata_group):
                if not isinstance(metadata, dict):
                    continue

                value = str(metadata.get("value") or (document_group[item_index] if item_index < len(document_group) else ""))
                if not value:
                    continue

                created_at_text = str(metadata.get("created_at") or datetime.utcnow().isoformat())
                items.append(
                    MemoryItem(
                        key=str(metadata.get("key", "")),
                        value=value,
                        layer=str(metadata.get("layer", "short_term")),
                        created_at=datetime.fromisoformat(created_at_text),
                        flagged=bool(metadata.get("flagged", False)),
                    )
                )

        return items

    def _merge_items(self, groups: list[list[MemoryItem]], limit: int) -> list[MemoryItem]:
        combined: list[MemoryItem] = []
        seen: set[tuple[str, str, str, str, bool]] = set()

        for group in groups:
            for item in group:
                signature = (item.key, item.value, item.layer, item.created_at.isoformat(), item.flagged)
                if signature in seen:
                    continue
                seen.add(signature)
                combined.append(item)
                if len(combined) >= limit:
                    return combined

        return combined

    def recent(self, limit: int = 8) -> list[MemoryItem]:
        if limit <= 0:
            return []

        return [self._deserialize_row(row) for row in self._recent_rows(limit)]

    def save(self, item: MemoryItem) -> None:
        self._store_in_sqlite(item)
        self._store_in_chroma(item)

    def get(self, key: str) -> MemoryItem | None:
        connection = self._ensure_sqlite()
        row = connection.execute(
            """
            SELECT memory_key, value, layer, created_at, flagged
            FROM memories
            WHERE memory_key = ?
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """,
            (key,),
        ).fetchone()
        if row is None:
            return None

        return self._deserialize_row(row)

    def search(self, query: str, limit: int = 8) -> list[MemoryItem]:
        lowered_query = query.lower().strip()
        if not lowered_query or limit <= 0:
            return []

        semantic_items = self._semantic_items(lowered_query, limit)
        keyword_items = [self._deserialize_row(row) for row in self._keyword_rows(lowered_query, limit * 2)]

        return self._merge_items([semantic_items, keyword_items], limit)