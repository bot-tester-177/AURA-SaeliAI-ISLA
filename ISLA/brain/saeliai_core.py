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
        system_prompt_path: Path | None = None,
    ) -> None:
        self.manifest_path = manifest_path
        self.manifest = self._load_manifest(manifest_path)
        self.memory_store = memory_store or MemoryStore()
        self.tool_router = tool_router or ToolRouter()
        self.system_prompt_path = system_prompt_path or Path(__file__).resolve().parents[1] / "prompts" / "system_prompt.md"
        self.conversation_history: list[dict[str, str]] = []
        self.max_history_messages = 24
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

    def _append_history(self, role: str, content: str) -> None:
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > self.max_history_messages:
            self.conversation_history = self.conversation_history[-self.max_history_messages :]

    def _record_turn(self, user_text: str, assistant_text: str) -> None:
        self._append_history("user", user_text)
        self._append_history("assistant", assistant_text)

    def _load_system_prompt(self) -> str:
        try:
            return self.system_prompt_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return ""

    def _format_manifest_context(self) -> str:
        values = "\n".join(f"- {value}" for value in self.manifest.values) or "- (none)"
        return (
            f"Identity manifest:\n"
            f"- name: {self.manifest.name}\n"
            f"- core_purpose: {self.manifest.core_purpose}\n"
            f"- values:\n{values}\n"
            f"- emotional_range: {self.manifest.emotional_range}\n"
            f"- limits: {self.manifest.limits}\n"
            f"- memory_rules: {self.manifest.memory_rules}"
        )

    def _format_memory_context(self, query: str | None = None) -> str:
        recent_items = self.memory_store.recent(limit=8)
        relevant_items = self.memory_store.search(query, limit=8) if query else []

        def format_items(items: list[MemoryItem]) -> str:
            if not items:
                return "- (none)"

            return "\n".join(
                f"- [{item.layer}] {item.key}: {item.value}"
                for item in items
            )

        sections: list[str] = []
        if relevant_items:
            sections.append(f"Semantic recall:\n{format_items(relevant_items)}")

        if recent_items:
            sections.append(f"Recent memory:\n{format_items(recent_items)}")

        if not sections:
            return "No stored memories available yet."

        return "\n\n".join(sections)

    def _build_system_prompt(self, user_input: str | None = None) -> str:
        parts = [self._load_system_prompt(), self._format_manifest_context()]
        parts.append(f"Relevant memory context from prior sessions:\n{self._format_memory_context(user_input)}")
        return "\n\n".join(part for part in parts if part.strip())

    def _finalize_turn(self, user_text: str, response: Any) -> Any:
        self._remember_utterance(user_text)
        self._record_turn(user_text, response if isinstance(response, str) else str(response))
        return response

    def get_identity(self) -> IslaManifest:
        return self.manifest

    def route_input(self, user_input: str) -> Any:
        text = user_input.strip()
        if not text:
            return "I did not catch that."

        lowered = text.lower()

        if lowered.startswith("remember "):
            payload = text[len("remember "):].strip()
            layer = "long_term"

            for prefix, candidate_layer in (("fact ", "structured_fact"), ("preference ", "preference"), ("memory ", "long_term"), ("note ", "long_term")):
                if payload.lower().startswith(prefix):
                    payload = payload[len(prefix):].strip()
                    layer = candidate_layer
                    break

            if "=" in payload:
                key, value = payload.split("=", 1)
            elif ":" in payload:
                key, value = payload.split(":", 1)
            else:
                key, value = "note", payload

            item = MemoryItem(key=key.strip(), value=value.strip(), layer=layer)
            self.memory_store.save(item)
            return self._finalize_turn(text, f"I remembered {item.key}.")

        if lowered.startswith("recall "):
            key = text[len("recall "):].strip()
            memory_item = self.memory_store.get(key)
            if memory_item is None:
                return self._finalize_turn(text, f"I do not have a memory for {key}.")
            return self._finalize_turn(text, memory_item.value)

        if lowered.startswith("search "):
            query = text[len("search "):].strip()
            matches = self.memory_store.search(query)
            if not matches:
                return self._finalize_turn(text, f"I found no memories for {query}.")
            return self._finalize_turn(text, "\n".join(f"{item.key}: {item.value}" for item in matches))

        if lowered.startswith("tool "):
            payload = text[len("tool "):].strip()
            if not payload:
                return self._finalize_turn(text, "Specify a tool name.")

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

            return self._finalize_turn(text, self.tool_router.execute(ToolCall(name=tool_name, arguments=arguments)))

        import ollama

        result = ollama.chat(
            model="llama3.2",
            messages=[
                {"role": "system", "content": self._build_system_prompt(text)},
                *self.conversation_history,
                {"role": "user", "content": text},
            ],
        )
        return self._finalize_turn(text, result["message"]["content"])