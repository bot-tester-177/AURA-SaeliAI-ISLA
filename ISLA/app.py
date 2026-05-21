"""Application wiring for Isla."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .brain.saeliai_core import SaeliAICore
from .memory.memory_store import MemoryStore
from .tools.tool_router import ToolRouter
from .voice.voice_loop import VoiceLoop


@dataclass(slots=True)
class IslaApp:
    """Connects manifest, memory, tools, and voice into one local loop."""

    manifest_path: Path
    core: SaeliAICore = field(init=False)
    voice_loop: VoiceLoop = field(default_factory=VoiceLoop)

    def __post_init__(self) -> None:
        memory_store = MemoryStore()
        tool_router = ToolRouter()
        self.core = SaeliAICore(self.manifest_path, memory_store=memory_store, tool_router=tool_router)

    def run_once(self) -> str:
        return self.voice_loop.run_once(self.core.route_input)

    def run_forever(self) -> None:
        while True:
            user_text = self.voice_loop.listen()
            if not user_text:
                continue

            lowered = user_text.lower().strip()
            if lowered in {"exit", "quit", "bye"}:
                self.voice_loop.speak("Goodbye for now.")
                break

            response = self.core.route_input(user_text)
            self.voice_loop.speak(str(response))