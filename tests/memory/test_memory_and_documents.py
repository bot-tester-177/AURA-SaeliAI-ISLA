from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from ISLA.memory.document_store import DocumentStore
from ISLA.memory.memory_store import MemoryItem, MemoryStore


class MemoryAndDocumentTests(TestCase):
    def test_memory_store_persists_and_searches(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = MemoryStore(store_path=Path(tmpdir) / "memory")
            store.save(MemoryItem(key="favorite_color", value="blue", layer="preference"))

            self.assertEqual(store.get("favorite_color").value, "blue")
            self.assertEqual(store.recent(limit=1)[0].key, "favorite_color")
            self.assertEqual(store.search("blue")[0].key, "favorite_color")

    def test_document_store_indexes_files_and_searches_content(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs = root / "docs"
            docs.mkdir()
            note = docs / "notes.txt"
            note.write_text("Isla can remember facts and search local documents.", encoding="utf-8")

            store = DocumentStore(store_path=root / "documents")
            read_result = store.read(str(docs))
            search_result = store.search("remember facts")

            self.assertEqual(read_result["count"], 1)
            self.assertEqual(read_result["indexed_files"], [str(note.resolve())])
            self.assertGreaterEqual(len(search_result), 1)
            self.assertIn("remember facts", search_result[0]["text"].lower())