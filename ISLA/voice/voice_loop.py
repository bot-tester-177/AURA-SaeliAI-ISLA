"""Voice input/output loop for Isla."""

from __future__ import annotations

import os
import shutil
import subprocess
import importlib
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
    tts_language: str = field(default_factory=lambda: os.getenv("ISLA_VOICE_TTS_LANGUAGE", "en"))
    voice_input_prompt: str = field(default_factory=lambda: os.getenv("ISLA_VOICE_INPUT_PROMPT", "You: "))
    tts_output_dir: Path = field(default_factory=lambda: Path.cwd() / ".isla_voice_cache")
    use_mic: bool = field(default_factory=lambda: os.getenv("ISLA_USE_MIC", "true").lower() in {"1", "true", "yes"})
    whisper_model_name: str = field(default_factory=lambda: os.getenv("ISLA_WHISPER_MODEL", "small"))
    allow_keyboard_fallback: bool = field(
        default_factory=lambda: os.getenv("ISLA_ALLOW_KEYBOARD_FALLBACK", "false").lower()
        in {"1", "true", "yes"}
    )

    def listen(self) -> str:
        if self.use_mic:
            try:
                return self._record_and_transcribe()
            except Exception as exc:
                if not self.allow_keyboard_fallback:
                    raise RuntimeError(
                        "Microphone STT failed. Install whisper + audio dependencies or set "
                        "ISLA_ALLOW_KEYBOARD_FALLBACK=true."
                    ) from exc

        if self.allow_keyboard_fallback:
            try:
                return input(self.voice_input_prompt).strip()
            except EOFError:
                return ""

        return ""

    def _record_and_transcribe(self) -> str:
        """Record from the default microphone and transcribe using Whisper.

        This attempts to import `sounddevice`, `soundfile`, and `whisper`.
        If any step fails, an exception is raised and the caller will fall
        back to keyboard input.
        """
        import sys
        import tempfile
        import wave

        # Ensure waifu-env packages (sounddevice, soundfile, whisper) are importable
        # when running from the project venv (Python 3.13).
        waifu_site = str(self.assets.waifu_env_dir / "lib" / "python3.10" / "site-packages")
        if waifu_site not in sys.path:
            sys.path.insert(0, waifu_site)

        sd = importlib.import_module("sounddevice")
        sf = importlib.import_module("soundfile")

        # Parameters from environment (duration in seconds)
        duration = float(os.getenv("ISLA_MIC_DURATION", "5.0"))
        sample_rate = int(os.getenv("ISLA_MIC_SAMPLE_RATE", "16000"))

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        # Record audio
        frames = int(duration * sample_rate)
        recording = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="int16")
        sd.wait()

        # Write WAV
        sf.write(tmp_path, recording, sample_rate)

        # Transcribe with whisper
        whisper = importlib.import_module("whisper")

        model = whisper.load_model(self.whisper_model_name)
        result = model.transcribe(tmp_path)
        try:
            text = result.get("text", "").strip()
        except Exception:
            text = ""

        # Clean up the temp file
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

        return text

    def speak(self, text: str) -> None:
        reference_wavs = self.assets.reference_wavs()
        tts_executable = shutil.which(self.tts_command)
        # If multiple reference WAVs are available, concatenate them into
        # a single temporary file so the TTS CLI can use them as a combined
        # speaker reference sample for zero-shot cloning.
        temp_ref_path = None
        reference_wav = None
        if reference_wavs:
            if len(reference_wavs) == 1:
                reference_wav = reference_wavs[0]
            else:
                try:
                    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    tmp_path = tmp.name
                    tmp.close()

                    # Use wave to concatenate files with matching params.
                    with wave.open(tmp_path, "wb") as out_wav:
                        first_params = None
                        for idx, src in enumerate(reference_wavs):
                            try:
                                with wave.open(str(src), "rb") as in_wav:
                                    if first_params is None:
                                        first_params = in_wav.getparams()
                                        out_wav.setparams(first_params)
                                    else:
                                        # Only append files that match params.
                                        if in_wav.getparams() != first_params:
                                            continue

                                    frames = in_wav.readframes(in_wav.getnframes())
                                    out_wav.writeframes(frames)
                            except Exception:
                                # Skip files that can't be read or have incompatible formats
                                continue
                        temp_ref_path = Path(tmp_path)
                        reference_wav = temp_ref_path
                except Exception:
                    # Fall back to single-file reference selection
                    reference_wav = reference_wavs[0]

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
                "--language_idx",
                self.tts_language,
                "--out_path",
                str(output_path),
            ]

            subprocess.run(command, check=True)

            if shutil.which("afplay") is not None:
                subprocess.run(["afplay", str(output_path)], check=True)
            # Clean up temporary concatenated reference wav if we created one.
            if temp_ref_path is not None:
                try:
                    temp_ref_path.unlink(missing_ok=True)
                except Exception:
                    pass
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