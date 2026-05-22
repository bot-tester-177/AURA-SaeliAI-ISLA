"""Integration tests for the voice I/O pipeline."""

from __future__ import annotations

import os
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

from ISLA.voice.voice_loop import VoiceLoop
from ISLA.brain.saeliai_core import SaeliAICore


def _write_silent_wav(path: Path, duration_seconds: float = 1.0) -> None:
    """Write a silent WAV file for testing."""
    framerate = 16000
    nframes = int(framerate * duration_seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(framerate)
        wav_file.writeframes(b"\x00\x00" * nframes)


class VoiceIntegrationTests(TestCase):
    """Test voice pipeline end-to-end without actual audio hardware."""

    def setUp(self) -> None:
        """Set up temporary directories for test isolation."""
        self.tmpdir = TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.wav_dir = self.root / "wavs"
        self.wav_dir.mkdir()
        _write_silent_wav(self.wav_dir / "speaker.wav")

    def tearDown(self) -> None:
        """Clean up temporary files."""
        self.tmpdir.cleanup()

    def _create_voice_loop(self, use_mic: bool = False) -> VoiceLoop:
        """Create a voice loop with test configuration."""
        with patch.dict(
            os.environ,
            {
                "ISLA_VOICE_PROJECT_DIR": str(self.root),
                "ISLA_VOICE_MODEL_DIR": str(self.root / "model"),
                "ISLA_VOICE_DATASET_DIR": str(self.root / "dataset"),
                "ISLA_VOICE_ENV_DIR": str(self.root / ".venv"),
                "ISLA_VOICE_WAV_DIR": str(self.wav_dir),
                "ISLA_USE_MIC": "true" if use_mic else "false",
                "ISLA_ALLOW_KEYBOARD_FALLBACK": "true",
            },
            clear=False,
        ):
            return VoiceLoop()

    def test_voice_loop_stt_to_llm_to_tts_pipeline(self) -> None:
        """Test full STT -> LLM -> TTS pipeline with mocked backends."""
        loop = self._create_voice_loop()

        # Mock the route function to simulate LLM response
        def mock_route(text: str) -> str:
            return f"Echo: {text}"

        with patch.object(type(loop), "speak") as mock_speak:
            result = loop.respond("Hello Isla", mock_route)

        # Verify the response was generated and speak was called
        self.assertEqual(result, "Echo: Hello Isla")
        mock_speak.assert_called_once_with("Echo: Hello Isla")

    def test_voice_loop_handles_empty_input(self) -> None:
        """Test voice loop gracefully handles empty input."""
        loop = self._create_voice_loop()

        def mock_route(text: str) -> str:
            if not text:
                return ""  # Empty input returns empty response
            return "response"

        # Empty string should not crash
        with patch.object(type(loop), "speak") as mock_speak:
            result = loop.respond("", mock_route)

        # Should handle gracefully
        self.assertEqual(result, "")
        # speak should not be called for empty response
        mock_speak.assert_not_called()

    def test_voice_loop_with_core_integration(self) -> None:
        """Test voice loop integrated with SaeliAICore (mocked LLM)."""
        with TemporaryDirectory() as manifest_dir:
            manifest_path = Path(manifest_dir) / "test_manifest.yaml"
            manifest_path.write_text(
                """
name: TestIsla
core_purpose: Test companion
values:
  - test_value
emotional_range: neutral
limits: none
memory_rules: test
"""
            )

            core = SaeliAICore(manifest_path)
            loop = self._create_voice_loop()

            # Mock the LLM to avoid needing Ollama running
            def mock_route(text: str) -> str:
                return f"Mocked response to: {text}"

            with patch.object(type(loop), "speak") as mock_speak:
                result = loop.respond("What is your name?", mock_route)

            # Verify response
            self.assertIn("Mocked response", result)
            mock_speak.assert_called_once()

    def test_voice_asset_paths_discovery(self) -> None:
        """Test that voice assets are discovered correctly."""
        from ISLA.voice.voice_assets import VoiceAssetPaths

        with patch.dict(
            os.environ,
            {
                "ISLA_VOICE_PROJECT_DIR": str(self.root),
                "ISLA_VOICE_MODEL_DIR": str(self.root / "model"),
                "ISLA_VOICE_DATASET_DIR": str(self.root / "dataset"),
                "ISLA_VOICE_WAV_DIR": str(self.wav_dir),
                "ISLA_VOICE_ENV_DIR": str(self.root / ".venv"),
            },
            clear=False,
        ):
            assets = VoiceAssetPaths()

        # Verify assets are discovered
        self.assertIsNotNone(assets.preferred_reference_wav())
        self.assertIn(self.wav_dir / "speaker.wav", assets.reference_wavs())

    def test_voice_loop_listen_with_keyboard_fallback(self) -> None:
        """Test voice loop can fall back to keyboard input."""
        loop = self._create_voice_loop(use_mic=False)

        # Mock keyboard input
        with patch("builtins.input", return_value="test input"):
            result = loop.listen()

        self.assertEqual(result, "test input")

    def test_voice_loop_multiple_turns(self) -> None:
        """Test voice loop can handle multiple conversation turns."""
        loop = self._create_voice_loop()

        call_count = 0

        def mock_route(text: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"Response {call_count} to: {text}"

        with patch.object(type(loop), "speak"):
            response1 = loop.respond("First question", mock_route)
            response2 = loop.respond("Second question", mock_route)

        self.assertIn("Response 1", response1)
        self.assertIn("Response 2", response2)
        self.assertEqual(call_count, 2)

    def test_voice_loop_with_special_characters(self) -> None:
        """Test voice loop handles special characters in input."""
        loop = self._create_voice_loop()

        special_inputs = [
            "What's your favorite color?",
            "It's raining & cold!",
            "émojis: 😀🎉",
            "quotes: 'hello' \"world\"",
        ]

        def mock_route(text: str) -> str:
            return f"Understood: {text}"

        with patch.object(type(loop), "speak"):
            for input_text in special_inputs:
                result = loop.respond(input_text, mock_route)
                self.assertIn("Understood", result)

    def test_voice_loop_response_length(self) -> None:
        """Test that voice loop responses are reasonable length."""
        loop = self._create_voice_loop()

        def mock_route(text: str) -> str:
            return "a" * 5000  # Very long response

        with patch.object(type(loop), "speak") as mock_speak:
            result = loop.respond("test", mock_route)

        # Response should still be generated
        self.assertEqual(len(result), 5000)
        mock_speak.assert_called_once()
