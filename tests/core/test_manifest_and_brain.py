from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ISLA.brain.saeliai_core import SaeliAICore
from ISLA.memory.memory_store import MemoryStore
from ISLA.tools.tool_router import ToolRouter


class ManifestAndBrainTests(TestCase):
    def test_manifest_loads_and_identity_context_is_available(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        manifest_path = repo_root / "ISLA" / "manifest" / "isla.yaml"

        with TemporaryDirectory() as tmpdir:
            memory_store = MemoryStore(store_path=Path(tmpdir) / "memory")
            core = SaeliAICore(manifest_path, memory_store=memory_store, tool_router=ToolRouter())

            self.assertEqual(core.get_identity().name, "Isla")
            self.assertIn("loyalty", core.get_identity().values)
            self.assertIn("Identity manifest", core._format_manifest_context())

    def test_route_input_handles_memory_and_tool_commands(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        manifest_path = repo_root / "ISLA" / "manifest" / "isla.yaml"

        with TemporaryDirectory() as tmpdir:
            memory_store = MemoryStore(store_path=Path(tmpdir) / "memory")
            tool_router = ToolRouter()
            core = SaeliAICore(manifest_path, memory_store=memory_store, tool_router=tool_router)
            tool_router.register("echo", lambda text="": text)

            with patch.object(core, "_run_model_with_tools", return_value="model response"), patch.object(
                core.vtube_bridge, "send_emotion"
            ):
                remember_result = core.route_input("remember fact favorite_color=blue")
                recall_result = core.route_input("recall favorite_color")
                tool_result = core.route_input('tool echo {"text": "works"}')
                chat_result = core.route_input("hello there")

            self.assertEqual(remember_result, "I remembered favorite_color.")
            self.assertEqual(recall_result, "blue")
            self.assertEqual(tool_result, "works")
            self.assertEqual(chat_result, "model response")
            self.assertEqual(memory_store.get("favorite_color").value, "blue")

    def test_memory_item_is_recorded_with_core_turns(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        manifest_path = repo_root / "ISLA" / "manifest" / "isla.yaml"

        with TemporaryDirectory() as tmpdir:
            memory_store = MemoryStore(store_path=Path(tmpdir) / "memory")
            core = SaeliAICore(manifest_path, memory_store=memory_store, tool_router=ToolRouter())

            with patch.object(core, "_run_model_with_tools", return_value="fine"), patch.object(
                core.vtube_bridge, "send_emotion"
            ):
                core.route_input("hello")

            stored = memory_store.recent(limit=1)[0]
            self.assertTrue(stored.key.startswith("utterance-"))
            self.assertEqual(stored.layer, "short_term")
            self.assertEqual(stored.value, "hello")