"""Core identity and orchestration for Isla."""

from __future__ import annotations

import json
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency
    yaml = None

from ..memory.memory_store import MemoryItem, MemoryStore
from ..tools.tool_router import ToolCall, ToolRouter


@dataclass(slots=True)
class IslaManifest:
    name: str
    core_purpose: str
    values: list[str] = field(default_factory=list)
    emotional_range: str = ""
    limits: str = ""
    memory_rules: str = ""


class SaeliAICore:
    """Loads the manifest and coordinates the top-level Isla state."""

    def __init__(
        self,
        manifest_path: Path,
        memory_store: MemoryStore | None = None,
        tool_router: ToolRouter | None = None,
    ) -> None:
        self.manifest_path = manifest_path
        self.manifest = self._load_manifest(manifest_path)
        self.memory_store = memory_store or MemoryStore()
        self.tool_router = tool_router or ToolRouter()
        self._register_default_tools()

    def _load_manifest(self, manifest_path: Path) -> IslaManifest:
        raw_text = manifest_path.read_text(encoding="utf-8")

        if yaml is not None:
            loaded = yaml.safe_load(raw_text)
        else:
            loaded = self._parse_manifest_text(raw_text)

        if not isinstance(loaded, dict):
            raise ValueError(f"Manifest at {manifest_path} did not decode to a mapping.")

        return IslaManifest(
            name=str(loaded.get("name", "Isla")),
            core_purpose=str(loaded.get("core_purpose", "")),
            values=[str(value) for value in loaded.get("values", [])],
            emotional_range=str(loaded.get("emotional_range", "")),
            limits=str(loaded.get("limits", "")),
            memory_rules=str(loaded.get("memory_rules", "")),
        )

    def _parse_manifest_text(self, raw_text: str) -> dict[str, object]:
        data: dict[str, object] = {}
        current_key: str | None = None
        block_lines: list[str] = []
        list_key: str | None = None

        for raw_line in raw_text.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip(" "))

            if current_key is not None and block_lines:
                if indent >= 2:
                    block_lines.append(stripped)
                    continue

                data[current_key] = " ".join(block_lines).strip()
                current_key = None
                block_lines = []
                list_key = None

            if list_key is not None and indent >= 2 and stripped.startswith("- "):
                values = data.setdefault(list_key, [])
                if isinstance(values, list):
                    values.append(stripped[2:].strip())
                continue

            if ":" not in stripped:
                continue

            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()

            if not value:
                data[key] = []
                list_key = key
                current_key = None
                block_lines = []
                continue

            if value in {">", ">-", "|", "|-"}:
                current_key = key
                block_lines = []
                list_key = None
                continue

            data[key] = value
            current_key = None
            block_lines = []
            list_key = None

        if current_key is not None and block_lines:
            data[current_key] = " ".join(block_lines).strip()

        return data

    def _register_default_tools(self) -> None:
        self.tool_router.register("identity", self.get_identity)
        self.tool_router.register("memory.get", self.memory_store.get)
        self.tool_router.register("memory.search", self.memory_store.search)

    def _remember_utterance(self, user_input: str) -> None:
        item = MemoryItem(
            key=f"utterance-{datetime.utcnow().isoformat(timespec='seconds')}",
            value=user_input,
            layer="short_term",
        )
        self.memory_store.save(item)

    def get_identity(self) -> IslaManifest:
        return self.manifest

    def route_input(self, user_input: str) -> Any:
        text = user_input.strip()
        if not text:
            return "I did not catch that."

        lowered = text.lower()
        self._remember_utterance(text)

        if lowered.startswith("remember "):
            payload = text[len("remember "):].strip()
            if "=" in payload:
                key, value = payload.split("=", 1)
            elif ":" in payload:
                key, value = payload.split(":", 1)
            else:
                key, value = "note", payload

            item = MemoryItem(key=key.strip(), value=value.strip(), layer="long_term")
            self.memory_store.save(item)
            return f"I remembered {item.key}."

        if lowered.startswith("recall "):
            key = text[len("recall "):].strip()
            memory_item = self.memory_store.get(key)
            if memory_item is None:
                return f"I do not have a memory for {key}."
            return memory_item.value

        if lowered.startswith("search "):
            query = text[len("search "):].strip()
            matches = self.memory_store.search(query)
            if not matches:
                return f"I found no memories for {query}."
            return "\n".join(f"{item.key}: {item.value}" for item in matches)

        if lowered.startswith("tool "):
            payload = text[len("tool "):].strip()
            if not payload:
                return "Specify a tool name."

            tool_name, _, raw_arguments = payload.partition(" ")
            arguments: dict[str, object]
            raw_arguments = raw_arguments.strip()

            if raw_arguments:
                try:
                    loaded_arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    loaded_arguments = {"text": raw_arguments}
                if isinstance(loaded_arguments, dict):
                    arguments = loaded_arguments
                else:
                    arguments = {"value": loaded_arguments}
            else:
                arguments = {}

            return self.tool_router.execute(ToolCall(name=tool_name, arguments=arguments))

        import ollama

        result = ollama.chat(
            model="llama3.2",
            messages=[
                {"role": "system", "content": self.manifest.core_purpose},
                {"role": "user", "content": text},
            ],
        )
        return result["message"]["content"]