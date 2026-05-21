"""Voice input/output loop for Isla."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .voice_assets import VoiceAssetPaths


@dataclass(slots=True)
class VoiceLoop:
    """Handles the local STT -> response -> TTS loop."""

    assets: VoiceAssetPaths = field(default_factory=VoiceAssetPaths)
    tts_command: str = field(default_factory=lambda: os.getenv("ISLA_VOICE_TTS_COMMAND", "tts"))
    tts_model_name: str = field(
        default_factory=lambda: os.getenv(
            "ISLA_VOICE_TTS_MODEL_NAME", "tts_models/multilingual/multi-dataset/xtts_v2"
        )
    )
    voice_input_prompt: str = field(default_factory=lambda: os.getenv("ISLA_VOICE_INPUT_PROMPT", "You: "))
    tts_output_dir: Path = field(default_factory=lambda: Path.cwd() / ".isla_voice_cache")

    def listen(self) -> str:
        try:
            return input(self.voice_input_prompt).strip()
        except EOFError:
            return ""

    def speak(self, text: str) -> None:
        reference_wav = self.assets.preferred_reference_wav()
        tts_executable = shutil.which(self.tts_command)

        if reference_wav is not None and tts_executable is not None:
            self.tts_output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.tts_output_dir / "isla_voice.wav"

            command = [
                tts_executable,
                "--text",
                text,
                "--model_name",
                self.tts_model_name,
                "--speaker_wav",
                str(reference_wav),
                "--out_path",
                str(output_path),
            ]

            subprocess.run(command, check=True)

            if shutil.which("afplay") is not None:
                subprocess.run(["afplay", str(output_path)], check=True)
            return

        say_executable = shutil.which("say")
        if say_executable is not None:
            subprocess.run([say_executable, text], check=True)
            return

        raise RuntimeError(
            "No usable TTS backend was found. Install a local TTS engine or configure one via ISLA_VOICE_TTS_COMMAND."
        )

    def run_once(self, responder: Callable[[str], str] | None = None) -> str:
        user_text = self.listen()
        if not user_text:
            return ""

        response = responder(user_text) if responder is not None else user_text
        if not isinstance(response, str):
            response = str(response)

        self.speak(response)
        return response