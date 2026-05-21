"""Local document ingestion and retrieval for Isla."""

from __future__ import annotations

import json
import hashlib
import importlib
import os
import sqlite3
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .memory_store import LocalHashEmbeddingFunction

try:  # pragma: no cover - optional dependency
    chromadb = importlib.import_module("chromadb")
except Exception:  # pragma: no cover - optional dependency
    chromadb = None


def _default_document_root() -> Path:
    env_root = os.getenv("ISLA_DOCUMENT_ROOT", "").strip()
    env_path = os.getenv("ISLA_DOCUMENT_PATH", "").strip()

    if env_root:
        return Path(env_root).expanduser().resolve()

    if env_path:
        return Path(env_path).expanduser().resolve()

    return Path(__file__).resolve().parents[2] / ".isla_documents"


def _is_text_extension(path: Path) -> bool:
    return path.suffix.lower() in {
        ".txt",
        ".md",
        ".rst",
        ".json",
        ".yaml",
        ".yml",
        ".py",
        ".csv",
        ".toml",
        ".ini",
    }


@dataclass(slots=True)
class DocumentChunk:
    source_path: str
    chunk_index: int
    total_chunks: int
    text: str
    title: str
    file_type: str
    indexed_at: str
    source_mtime: str
    content_hash: str


@dataclass(slots=True)
class DocumentStore:
    """Stores local document chunks in ChromaDB for semantic retrieval."""

    store_path: Path = field(default_factory=_default_document_root)
    collection_name: str = "isla_documents"
    _collection: Any | None = field(init=False, default=None, repr=False)
    _sqlite_connection: sqlite3.Connection | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        self.store_path = self.store_path.expanduser().resolve()

    def _ensure_root(self) -> None:
        self.store_path.mkdir(parents=True, exist_ok=True)

    def _sqlite_path(self) -> Path:
        return self.store_path / "documents.sqlite3"

    def _ensure_sqlite(self) -> sqlite3.Connection:
        if self._sqlite_connection is not None:
            return self._sqlite_connection

        self._ensure_root()
        connection = sqlite3.connect(self._sqlite_path())
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                total_chunks INTEGER NOT NULL,
                text TEXT NOT NULL,
                title TEXT NOT NULL,
                file_type TEXT NOT NULL,
                indexed_at TEXT NOT NULL,
                source_mtime TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedding TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_document_chunks_source_path ON document_chunks(source_path)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_document_chunks_content_hash ON document_chunks(content_hash)"
        )
        connection.commit()
        self._sqlite_connection = connection
        return connection

    def _ensure_collection(self) -> Any | None:
        if self._collection is not None:
            return self._collection

        if chromadb is None:  # pragma: no cover - optional dependency
            return None

        self._ensure_root()
        client = chromadb.PersistentClient(path=str(self.store_path / "chroma"))
        self._collection = client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=LocalHashEmbeddingFunction(),
        )
        return self._collection

    def _read_text_file(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")

    def _read_pdf_file(self, path: Path) -> str:
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Reading PDFs requires the pypdf package.") from exc

        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)

        return "\n\n".join(pages)

    def _extract_text(self, path: Path) -> str:
        if path.suffix.lower() == ".pdf":
            return self._read_pdf_file(path)

        if _is_text_extension(path):
            return self._read_text_file(path)

        try:
            return self._read_text_file(path)
        except Exception as exc:
            raise RuntimeError(f"Unsupported document type: {path.suffix or path.name}") from exc

    def _chunk_text(self, text: str, chunk_size: int = 1400, overlap: int = 200) -> list[str]:
        cleaned = re.sub(r"\r\n?", "\n", text).strip()
        if not cleaned:
            return []

        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n+", cleaned) if paragraph.strip()]
        if not paragraphs:
            paragraphs = [cleaned]

        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
            if len(candidate) <= chunk_size:
                current = candidate
                continue

            if current:
                chunks.append(current.strip())
                current = ""

            if len(paragraph) <= chunk_size:
                current = paragraph
                continue

            start = 0
            while start < len(paragraph):
                end = min(len(paragraph), start + chunk_size)
                chunks.append(paragraph[start:end].strip())
                if end >= len(paragraph):
                    break
                start = max(end - overlap, start + 1)

        if current:
            chunks.append(current.strip())

        return [chunk for chunk in chunks if chunk]

    def _content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    def _document_chunks(self, path: Path, text: str) -> list[DocumentChunk]:
        chunks = self._chunk_text(text)
        if not chunks:
            return []

        indexed_at = datetime.utcnow().isoformat()
        source_mtime = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        content_hash = self._content_hash(text)
        return [
            DocumentChunk(
                source_path=str(path),
                chunk_index=index,
                total_chunks=len(chunks),
                text=chunk,
                title=path.stem,
                file_type=path.suffix.lower().lstrip("."),
                indexed_at=indexed_at,
                source_mtime=source_mtime,
                content_hash=content_hash,
            )
            for index, chunk in enumerate(chunks)
        ]

    def _upsert_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return

        self._store_chunks_in_sqlite(chunks)

        collection = self._ensure_collection()
        if collection is None:
            return

        source_path = chunks[0].source_path
        try:
            collection.delete(where={"source_path": source_path})
        except Exception:
            pass

        collection.add(
            ids=[f"{chunk.source_path}::{chunk.content_hash}::{chunk.chunk_index}" for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {
                    "source_path": chunk.source_path,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "title": chunk.title,
                    "file_type": chunk.file_type,
                    "indexed_at": chunk.indexed_at,
                    "source_mtime": chunk.source_mtime,
                    "content_hash": chunk.content_hash,
                }
                for chunk in chunks
            ],
        )

    def _store_chunks_in_sqlite(self, chunks: list[DocumentChunk]) -> None:
        connection = self._ensure_sqlite()
        source_path = chunks[0].source_path
        connection.execute("DELETE FROM document_chunks WHERE source_path = ?", (source_path,))

        embedder = LocalHashEmbeddingFunction()
        for chunk in chunks:
            embedding = embedder([chunk.text])[0]
            connection.execute(
                """
                INSERT INTO document_chunks (
                    source_path, chunk_index, total_chunks, text, title,
                    file_type, indexed_at, source_mtime, content_hash, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.source_path,
                    chunk.chunk_index,
                    chunk.total_chunks,
                    chunk.text,
                    chunk.title,
                    chunk.file_type,
                    chunk.indexed_at,
                    chunk.source_mtime,
                    chunk.content_hash,
                    json.dumps(embedding),
                ),
            )

        connection.commit()

    def _index_file(self, path: Path) -> dict[str, object]:
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        if path.is_dir():
            indexed_files: list[str] = []
            for child in sorted(path.rglob("*")):
                if not child.is_file():
                    continue
                if child.suffix.lower() == ".pdf" or _is_text_extension(child):
                    self._index_file(child)
                    indexed_files.append(str(child))

            return {
                "path": str(path),
                "indexed_files": indexed_files,
                "count": len(indexed_files),
                "message": f"Indexed {len(indexed_files)} files from {path}.",
            }

        text = self._extract_text(path)
        chunks = self._document_chunks(path, text)
        self._upsert_chunks(chunks)

        preview = self._preview_text(text)
        return {
            "path": str(path),
            "title": path.stem,
            "file_type": path.suffix.lower().lstrip("."),
            "chunk_count": len(chunks),
            "content": preview,
            "truncated": len(preview) < len(text),
        }

    def _preview_text(self, text: str, limit: int = 8000) -> str:
        cleaned = text.strip()
        if len(cleaned) <= limit:
            return cleaned

        return cleaned[:limit].rstrip() + "\n\n[truncated]"

    def read(self, path: str) -> dict[str, object]:
        resolved_path = Path(path).expanduser().resolve()
        return self._index_file(resolved_path)

    def search(self, query: str, limit: int = 5, path: str | None = None) -> list[dict[str, object]]:
        lowered = query.lower().strip()
        if not lowered or limit <= 0:
            return []

        if self._collection is not None:
            matches = self._search_chroma(lowered, limit, path)
            if matches:
                return matches

        return self._search_sqlite(lowered, limit, path)

    def _search_chroma(self, query: str, limit: int, path: str | None = None) -> list[dict[str, object]]:
        collection = self._ensure_collection()
        if collection is None:
            return []

        where = {"source_path": str(Path(path).expanduser().resolve())} if path else None

        try:
            result = collection.query(
                query_texts=[query],
                n_results=max(limit * 2, limit),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []

        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        distances = result.get("distances") or []
        matches: list[dict[str, object]] = []

        for batch_index, metadata_batch in enumerate(metadatas):
            document_batch = documents[batch_index] if batch_index < len(documents) else []
            distance_batch = distances[batch_index] if batch_index < len(distances) else []

            for item_index, metadata in enumerate(metadata_batch):
                if not isinstance(metadata, dict):
                    continue

                text = str(document_batch[item_index] if item_index < len(document_batch) else "")
                if not text:
                    continue

                matches.append(
                    {
                        "source_path": metadata.get("source_path", ""),
                        "title": metadata.get("title", ""),
                        "file_type": metadata.get("file_type", ""),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "total_chunks": metadata.get("total_chunks", 0),
                        "indexed_at": metadata.get("indexed_at", ""),
                        "source_mtime": metadata.get("source_mtime", ""),
                        "distance": distance_batch[item_index] if item_index < len(distance_batch) else None,
                        "text": text,
                    }
                )

                if len(matches) >= limit:
                    return matches

        return matches

    def _search_sqlite(self, query: str, limit: int, path: str | None = None) -> list[dict[str, object]]:
        connection = self._ensure_sqlite()
        query_embedding = LocalHashEmbeddingFunction()([query])[0]
        query_norm = sum(value * value for value in query_embedding) ** 0.5 or 1.0

        base_query = (
            "SELECT source_path, chunk_index, total_chunks, text, title, file_type, "
            "indexed_at, source_mtime, content_hash, embedding FROM document_chunks"
        )
        params: tuple[object, ...] = ()
        if path:
            base_query += " WHERE source_path = ?"
            params = (str(Path(path).expanduser().resolve()),)

        rows = connection.execute(base_query, params).fetchall()

        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            try:
                embedding = json.loads(str(row["embedding"]))
            except Exception:
                continue

            dot_product = sum(float(a) * float(b) for a, b in zip(query_embedding, embedding))
            candidate_norm = sum(float(value) * float(value) for value in embedding) ** 0.5 or 1.0
            score = dot_product / (query_norm * candidate_norm)
            if score <= 0:
                continue
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)

        matches: list[dict[str, object]] = []
        for score, row in scored[:limit]:
            matches.append(
                {
                    "source_path": row["source_path"],
                    "title": row["title"],
                    "file_type": row["file_type"],
                    "chunk_index": row["chunk_index"],
                    "total_chunks": row["total_chunks"],
                    "indexed_at": row["indexed_at"],
                    "source_mtime": row["source_mtime"],
                    "distance": 1.0 - score,
                    "text": row["text"],
                }
            )

        return matches