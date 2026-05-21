"""Memory storage primitives for Isla."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import os


def _default_store_path() -> Path:
    env_path = os.getenv("ISLA_MEMORY_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser().resolve()

    # Keep memory in a stable repo-root location across runs.
    return Path(__file__).resolve().parents[2] / ".isla_memory.jsonl"


@dataclass(slots=True)
class MemoryItem:
    key: str
    value: str
    layer: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    flagged: bool = False


@dataclass(slots=True)
class MemoryStore:
    """Stores structured facts and prepares the path to longer-term retrieval."""

    store_path: Path = field(default_factory=_default_store_path)

    def recent(self, limit: int = 8) -> list[MemoryItem]:
        if limit <= 0:
            return []

        return sorted(self._load_items(), key=lambda item: item.created_at, reverse=True)[:limit]

    def _load_items(self) -> list[MemoryItem]:
        if not self.store_path.exists():
            return []

        items: list[MemoryItem] = []
        with self.store_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                record = json.loads(stripped)
                created_at = datetime.fromisoformat(record["created_at"])
                items.append(
                    MemoryItem(
                        key=record["key"],
                        value=record["value"],
                        layer=record["layer"],
                        created_at=created_at,
                        flagged=bool(record.get("flagged", False)),
                    )
                )
        return items

    def _serialize_item(self, item: MemoryItem) -> dict[str, object]:
        return {
            "key": item.key,
            "value": item.value,
            "layer": item.layer,
            "created_at": item.created_at.isoformat(),
            "flagged": item.flagged,
        }

    def save(self, item: MemoryItem) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.store_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._serialize_item(item), ensure_ascii=True))
            handle.write("\n")

    def get(self, key: str) -> MemoryItem | None:
        for item in reversed(self._load_items()):
            if item.key == key:
                return item
        return None

    def search(self, query: str) -> list[MemoryItem]:
        lowered_query = query.lower().strip()
        if not lowered_query:
            return []

        matches = [
            item
            for item in self._load_items()
            if lowered_query in item.key.lower()
            or lowered_query in item.value.lower()
            or lowered_query in item.layer.lower()
        ]
        return sorted(matches, key=lambda item: item.created_at, reverse=True)