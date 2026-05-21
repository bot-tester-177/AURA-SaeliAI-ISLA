from __future__ import annotations

import os
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ISLA.voice.voice_assets import VoiceAssetPaths
from ISLA.voice.voice_loop import VoiceLoop


def _write_silent_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 160)


class VoiceTests(TestCase):
    def test_voice_assets_discover_reference_wavs(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_dir = root / "project"
            model_dir = project_dir / "my_waifu_model"
            dataset_dir = project_dir / "dataset"
            wav_dir = project_dir / "wavs"
            wav_dir.mkdir(parents=True)
            model_dir.mkdir(parents=True)
            dataset_dir.mkdir(parents=True)

            reference = wav_dir / "speaker.wav"
            _write_silent_wav(reference)

            with patch.dict(
                os.environ,
                {
                    "ISLA_VOICE_PROJECT_DIR": str(project_dir),
                    "ISLA_VOICE_MODEL_DIR": str(model_dir),
                    "ISLA_VOICE_DATASET_DIR": str(dataset_dir),
                    "ISLA_VOICE_WAV_DIR": str(wav_dir),
                    "ISLA_VOICE_ENV_DIR": str(root / ".venv"),
                },
                clear=False,
            ):
                assets = VoiceAssetPaths()

            self.assertEqual(assets.preferred_reference_wav(), reference)
            self.assertIn("wav_dir", assets.existing_paths())
            self.assertEqual(assets.reference_wavs(), [reference])

    def test_voice_loop_responds_without_invoking_audio_backends(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wav_dir = root / "wavs"
            wav_dir.mkdir()
            _write_silent_wav(wav_dir / "speaker.wav")

            with patch.dict(
                os.environ,
                {
                    "ISLA_VOICE_PROJECT_DIR": str(root),
                    "ISLA_VOICE_MODEL_DIR": str(root / "model"),
                    "ISLA_VOICE_DATASET_DIR": str(root / "dataset"),
                    "ISLA_VOICE_ENV_DIR": str(root / ".venv"),
                    "ISLA_VOICE_WAV_DIR": str(wav_dir),
                    "ISLA_USE_MIC": "false",
                    "ISLA_ALLOW_KEYBOARD_FALLBACK": "false",
                },
                clear=False,
            ):
                loop = VoiceLoop()

            with patch.object(type(loop), "speak", return_value=None) as speak:
                result = loop.respond("hello", lambda text: text.upper())

            self.assertEqual(result, "HELLO")
            speak.assert_called_once_with("HELLO")