"""Core identity and orchestration for Isla."""

from __future__ import annotations

import json
import os
import subprocess
import webbrowser
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote_plus
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency
    yaml = None

from ..memory.memory_store import MemoryItem, MemoryStore
from ..memory.document_store import DocumentStore
from ..tools.tool_router import ToolCall, ToolRouter
from ..avatar.emotion_tagger import tag_emotion
from ..avatar.vtube_bridge import VTubeBridge


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
        self.document_store = DocumentStore()
        self.tool_router = tool_router or ToolRouter()
        self.ollama_model = os.environ.get("ISLA_OLLAMA_MODEL", "mistral").strip() or "mistral"
        self.system_prompt_path = system_prompt_path or Path(__file__).resolve().parents[1] / "prompts" / "system_prompt.md"
        self.conversation_history: list[dict[str, str]] = []
        self.max_history_messages = 24
        self.vtube_bridge = VTubeBridge()
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
        self.tool_router.register("file.read", self.document_store.read)
        self.tool_router.register("file.search", self.document_store.search)
        self.tool_router.register("time.now", self.get_current_time)
        self.tool_router.register("web.search", self.search_web)
        self.tool_router.register("app.open", self.open_app)

    def _ollama_tool_specs(self) -> list[dict[str, object]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "time.now",
                    "description": "Return the current local date and time in a human-readable string.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web.search",
                    "description": "Open a web search for the given query in the default browser.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search terms to look up on the web.",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "file.read",
                    "description": "Read a local file or directory and index supported documents in Isla's local document store.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Absolute or workspace-relative path to a file or directory.",
                            }
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "file.search",
                    "description": "Search the local document index for passages relevant to the given query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The question or topic to search for in indexed documents.",
                            },
                            "path": {
                                "type": "string",
                                "description": "Optional file or directory path to restrict the search.",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of passages to return.",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "app.open",
                    "description": "Open a macOS application by name.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app": {
                                "type": "string",
                                "description": "The app name to open, such as Safari or Calculator.",
                            }
                        },
                        "required": ["app"],
                    },
                },
            },
        ]

    def _ollama_chat(self, messages: list[dict[str, object]]) -> Any:
        import ollama

        return ollama.chat(
            model=self.ollama_model,
            messages=messages,
            tools=self._ollama_tool_specs(),
        )

    def _stringify_tool_result(self, result: object) -> str:
        if isinstance(result, str):
            return result

        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, indent=2, default=str)

        return str(result)

    def _run_model_with_tools(self, user_text: str) -> str:
        messages: list[dict[str, object]] = [
            {"role": "system", "content": self._build_system_prompt(user_text)},
            *self.conversation_history,
            {"role": "user", "content": user_text},
        ]

        final_text = ""
        for _ in range(3):
            response = self._ollama_chat(messages)
            message = response["message"]
            final_text = str(message.get("content") or "").strip()
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                return final_text

            assistant_message = {
                "role": message.get("role", "assistant"),
                "content": message.get("content"),
                "tool_calls": [
                    {
                        "function": {
                            "name": tool_call["function"]["name"],
                            "arguments": tool_call["function"]["arguments"],
                        }
                    }
                    for tool_call in tool_calls
                ],
            }
            messages.append(assistant_message)

            for tool_call in tool_calls:
                tool_name = str(tool_call["function"]["name"])
                arguments = dict(tool_call["function"].get("arguments") or {})
                tool_result = self.tool_router.execute(ToolCall(name=tool_name, arguments=arguments))
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": self._stringify_tool_result(tool_result),
                    }
                )

        return final_text

    def get_current_time(self) -> str:
        """Return the current local date and time."""

        now = datetime.now().astimezone()
        return now.strftime("%A, %B %d, %Y %I:%M:%S %p %Z")

    def search_web(self, query: str | None = None, text: str | None = None) -> str:
        """Open a web search in the default browser."""

        search_query = (query or text or "").strip()
        if not search_query:
            raise ValueError("A search query is required.")

        search_url = f"https://duckduckgo.com/?q={quote_plus(search_query)}"
        webbrowser.open(search_url, new=2)
        return f"Opened web search for {search_query!r}."

    def open_app(self, app: str | None = None, text: str | None = None) -> str:
        """Open a macOS application by name."""

        app_name = (app or text or "").strip()
        if not app_name:
            raise ValueError("An app name is required.")

        subprocess.run(["open", "-a", app_name], check=True, capture_output=True, text=True)
        return f"Opened {app_name!r}."

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

    def _format_document_context(self, query: str | None = None) -> str:
        if not query:
            return "No local document query was provided."

        matches = self.document_store.search(query, limit=6)
        if not matches:
            return "No local documents matched this question yet."

        lines = []
        for match in matches:
            source_path = str(match.get("source_path", ""))
            chunk_index = int(match.get("chunk_index", 0)) + 1
            total_chunks = int(match.get("total_chunks", 0))
            text = str(match.get("text", "")).strip()
            snippet = text[:500].rstrip()
            if len(text) > 500:
                snippet += "..."

            lines.append(f"- {source_path} [{chunk_index}/{total_chunks}]: {snippet}")

        return "Relevant local document passages:\n" + "\n".join(lines)

    def _build_system_prompt(self, user_input: str | None = None) -> str:
        parts = [self._load_system_prompt(), self._format_manifest_context()]
        parts.append(f"Relevant memory context from prior sessions:\n{self._format_memory_context(user_input)}")
        parts.append(f"Relevant local document context:\n{self._format_document_context(user_input)}")
        return "\n\n".join(part for part in parts if part.strip())

    def _finalize_turn(self, user_text: str, response: Any) -> Any:
        self._remember_utterance(user_text)
        self._record_turn(user_text, response if isinstance(response, str) else str(response))
        emotion = tag_emotion(response if isinstance(response, str) else str(response))
        self.vtube_bridge.send_emotion(emotion)
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

        return self._finalize_turn(text, self._run_model_with_tools(text))