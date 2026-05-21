"""Application wiring for Isla."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .brain.saeliai_core import SaeliAICore
from .memory.memory_store import MemoryStore
from .tools.tool_router import ToolRouter
from .voice.voice_loop import VoiceLoop

if TYPE_CHECKING:
    from .avatar.avatar_window import AvatarWindow


def _load_dotenv_file(dotenv_path: Path) -> None:
    """Load simple KEY=VALUE pairs from a local .env file if present."""

    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv_file(Path(__file__).resolve().parents[1] / ".env")


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

    def run_transcript(self, user_text: str) -> str:
        return self.voice_loop.respond(user_text, self.core.route_input)

    def run_loop(self) -> None:
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

    def run_wake_word_daemon(self, avatar_window: "AvatarWindow | None" = None) -> None:
        from .voice.wake_word_daemon import WakeWordDaemon

        WakeWordDaemon(self, avatar_window=avatar_window).run()

    def run_forever(self) -> None:
        self.run_loop()