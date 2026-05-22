"""Enhanced VoiceLoop that uses trained Isla voice model for synthesis."""

import os
import shutil
import subprocess
import importlib
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
import sys

from .voice_assets import VoiceAssetPaths


@dataclass(slots=True)
class VoiceLoopWithIslaModel:
    """Voice loop that prioritizes trained Isla Tacotron2 model over cloud TTS."""

    assets: VoiceAssetPaths = field(default_factory=VoiceAssetPaths)
    use_trained_model: bool = field(
        default_factory=lambda: os.getenv("ISLA_USE_TRAINED_MODEL", "true").lower()
        in {"1", "true", "yes"}
    )
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
    model_device: str = field(default_factory=lambda: os.getenv("ISLA_MODEL_DEVICE", "cpu"))

    _synthesizer: Optional[object] = field(default=None, init=False, repr=False)

    def listen(self) -> str:
        """Record audio and transcribe to text (STT)."""
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
        """Record from the default microphone and transcribe using Whisper."""
        import tempfile

        # Ensure waifu-env packages are importable
        waifu_site = str(self.assets.waifu_env_dir / "lib" / "python3.10" / "site-packages")
        if waifu_site not in sys.path:
            sys.path.insert(0, waifu_site)

        sd = importlib.import_module("sounddevice")
        sf = importlib.import_module("soundfile")

        # Parameters from environment
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

        # Clean up
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

        return text

    def _load_trained_model(self) -> None:
        """Lazily load the trained Isla voice model."""
        if self._synthesizer is not None:
            return

        try:
            from .isla_voice_synthesizer import IslaVoiceSynthesizer

            self._synthesizer = IslaVoiceSynthesizer(device=self.model_device)
            self._synthesizer.load()
        except Exception as e:
            print(f"⚠ Failed to load trained model: {e}")
            self._synthesizer = None

    def speak(self, text: str) -> None:
        """Synthesize and play text using the best available TTS."""
        if os.getenv("ISLA_SKIP_TTS", "false").lower() in {"1", "true", "yes"}:
            print(f"Isla: {text}")
            return

        # Try trained Isla model first (if available and enabled)
        if self.use_trained_model:
            try:
                self._load_trained_model()
                if self._synthesizer is not None:
                    print("Using trained Isla voice model...")
                    wav = self._synthesizer.synthesize(text)
                    self._play_audio(wav)
                    return
            except Exception as e:
                print(f"Trained model synthesis failed, falling back: {e}")

        # Fall back to cloud TTS (XTTS v2 or configured model)
        print("Using cloud TTS (XTTS v2)...")
        self._speak_cloud_tts(text)

    def _play_audio(self, wav: "np.ndarray", sample_rate: int = 22050) -> None:
        """Play audio waveform.

        Args:
            wav: Audio waveform (numpy array)
            sample_rate: Sample rate in Hz
        """
        import numpy as np

        try:
            import sounddevice as sd

            print(f"Playing {len(wav) / sample_rate:.1f}s of audio...")
            sd.play(wav, sample_rate)
            sd.wait()
        except ImportError:
            # Fallback: save to temp file and use system player
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = Path(tmp.name)

            try:
                import soundfile as sf

                wav_int16 = np.int16(wav * 32767)
                sf.write(str(tmp_path), wav_int16, sample_rate)

                if shutil.which("afplay"):
                    subprocess.run(["afplay", str(tmp_path)], check=True)
                elif shutil.which("paplay"):
                    subprocess.run(["paplay", str(tmp_path)], check=True)
            finally:
                tmp_path.unlink(missing_ok=True)

    def _speak_cloud_tts(self, text: str) -> None:
        """Use cloud TTS (XTTS v2 or configured model)."""
        reference_wavs = self.assets.reference_wavs()
        tts_executable = shutil.which(self.tts_command)

        # Build reference wav file
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

                    with wave.open(tmp_path, "wb") as out_wav:
                        first_params = None
                        for idx, src in enumerate(reference_wavs):
                            try:
                                with wave.open(str(src), "rb") as in_wav:
                                    if first_params is None:
                                        first_params = in_wav.getparams()
                                        out_wav.setparams(first_params)
                                    else:
                                        if in_wav.getparams() != first_params:
                                            continue

                                    frames = in_wav.readframes(in_wav.getnframes())
                                    out_wav.writeframes(frames)
                            except Exception:
                                continue
                        temp_ref_path = Path(tmp_path)
                        reference_wav = temp_ref_path
                except Exception:
                    reference_wav = reference_wavs[0] if reference_wavs else None

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

    def respond(self, user_text: str, responder: Callable[[str], str] | None = None) -> str:
        """Generate response and speak it."""
        if not user_text:
            return ""

        response = responder(user_text) if responder is not None else user_text
        if not isinstance(response, str):
            return ""

        print(f"Isla: {response}")
        self.speak(response)
        return response
