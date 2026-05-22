"""Integration tests for Phase 2 voice features: cloning, memory, personality."""

from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from ISLA.voice.voice_assets import VoiceAssetPaths
from ISLA.voice.voice_loop import VoiceLoop
from ISLA.voice.voice_memory import VoiceMemory, VoiceMemoryStore
from ISLA.voice.personality_examples import get_few_shot_prompt, PERSONALITY_EXAMPLES
from ISLA.voice.tts_verify import verify_tts_setup


def _write_silent_wav(path: Path, duration_seconds: float = 1.0) -> None:
    """Write a silent WAV file for testing."""
    framerate = 16000
    nframes = int(framerate * duration_seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(framerate)
        wav_file.writeframes(b"\x00\x00" * nframes)


class VoicePhase2IntegrationTests(TestCase):
    """Test Phase 2 voice features: cloning, memory, personality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.wav_dir = self.root / "wavs"
        self.wav_dir.mkdir()
        
        # Create multiple reference WAVs to test concatenation
        for i in range(3):
            _write_silent_wav(self.wav_dir / f"speaker_{i}.wav", duration_seconds=0.5)
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.tmpdir.cleanup()

    def test_voice_cloning_setup_with_multiple_wavs(self) -> None:
        """Test that voice cloning can use multiple WAV files."""
        with patch.dict(
            os.environ,
            {
                "ISLA_VOICE_PROJECT_DIR": str(self.root),
                "ISLA_VOICE_MODEL_DIR": str(self.root / "model"),
                "ISLA_VOICE_DATASET_DIR": str(self.root / "dataset"),
                "ISLA_VOICE_ENV_DIR": str(self.root / ".venv"),
                "ISLA_VOICE_WAV_DIR": str(self.wav_dir),
            },
            clear=False,
        ):
            assets = VoiceAssetPaths()
            wavs = assets.reference_wavs()
            
            # Verify multiple WAVs are found
            self.assertEqual(len(wavs), 3)
            self.assertIsNotNone(assets.preferred_reference_wav())

    def test_voice_memory_store_saves_and_retrieves(self) -> None:
        """Test voice memory persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_memories.db"
            store = VoiceMemoryStore(db_path)
            
            # Save a memory
            memory = VoiceMemory(
                user_input="What makes you unique?",
                isla_response="My ability to listen without judgment, I'd say.",
                emotion_detected="reflective",
                important=False,
            )
            mem_id = store.save_memory(memory)
            self.assertIsNotNone(mem_id)
            self.assertGreater(mem_id, 0)
            
            # Retrieve recent memories
            recent = store.get_recent_memories(limit=5)
            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0].user_input, memory.user_input)

    def test_voice_memory_mark_important(self) -> None:
        """Test marking memories as important."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_memories.db"
            store = VoiceMemoryStore(db_path)
            
            memory = VoiceMemory(
                user_input="Remember this is important",
                isla_response="Got it, I'll remember.",
                important=False,
            )
            mem_id = store.save_memory(memory)
            
            # Mark as important
            success = store.mark_important(mem_id)
            self.assertTrue(success)
            
            # Verify it's marked
            important = store.get_important_memories(limit=5)
            self.assertEqual(len(important), 1)
            self.assertTrue(important[0].important)

    def test_voice_memory_search(self) -> None:
        """Test searching through voice memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_memories.db"
            store = VoiceMemoryStore(db_path)
            
            # Save several memories
            memories = [
                VoiceMemory(user_input="What is your favorite color?", isla_response="Blue, like the sky."),
                VoiceMemory(user_input="Do you like music?", isla_response="Absolutely, music is wonderful."),
                VoiceMemory(user_input="Tell me about your dreams.", isla_response="I dream of being helpful."),
            ]
            for mem in memories:
                store.save_memory(mem)
            
            # Search for 'music'
            results = store.search_memories("music", limit=10)
            self.assertEqual(len(results), 1)
            self.assertIn("music", results[0].user_input.lower())
            
            # Search for 'like'
            results = store.search_memories("like", limit=10)
            self.assertEqual(len(results), 2)

    def test_personality_examples_are_defined(self) -> None:
        """Test that personality examples exist and are well-formed."""
        self.assertGreater(len(PERSONALITY_EXAMPLES), 0)
        
        for example in PERSONALITY_EXAMPLES:
            self.assertIsNotNone(example.user_input)
            self.assertIsNotNone(example.isla_response)
            self.assertGreater(len(example.user_input), 0)
            self.assertGreater(len(example.isla_response), 0)

    def test_few_shot_prompt_generation(self) -> None:
        """Test few-shot prompt generation for personality consistency."""
        # Generate full prompt
        prompt_full = get_few_shot_prompt(num_examples=5)
        self.assertIn("Isla", prompt_full)
        self.assertIn("personality", prompt_full.lower())
        self.assertIn("Humor", prompt_full)
        self.assertIn("Intelligence", prompt_full)
        
        # Generate partial prompt
        prompt_partial = get_few_shot_prompt(num_examples=2)
        self.assertLess(len(prompt_partial), len(prompt_full))
        self.assertIn("Example 1", prompt_partial)
        self.assertIn("Example 2", prompt_partial)
        self.assertNotIn("Example 3", prompt_partial)

    def test_personality_consistency_markers(self) -> None:
        """Test that personality examples demonstrate key traits."""
        prompt = get_few_shot_prompt(num_examples=5)
        
        # Check for personality markers
        markers = [
            ("warmth", "care"),
            ("intelligence", "insight"),
            ("curiosity", "question"),
            ("humor", "wit"),
        ]
        
        for trait, marker in markers:
            self.assertTrue(
                marker.lower() in prompt.lower() or trait.lower() in prompt.lower(),
                f"Personality trait '{trait}' not evident in prompt"
            )

    def test_tts_verification_structure(self) -> None:
        """Test TTS verification system returns proper structure."""
        status = verify_tts_setup()
        
        # Should return a dict with expected keys
        expected_keys = {"tts_package", "tts_command", "voice_samples"}
        self.assertEqual(set(status.keys()), expected_keys)
        
        # All values should be boolean
        for value in status.values():
            self.assertIsInstance(value, bool)

    def test_voice_memory_store_statistics(self) -> None:
        """Test memory store provides accurate statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_memories.db"
            store = VoiceMemoryStore(db_path)
            
            # Start with empty stats
            stats = store.get_memory_summary()
            self.assertEqual(stats["total_memories"], 0)
            self.assertEqual(stats["important_count"], 0)
            
            # Add memories
            for i in range(3):
                memory = VoiceMemory(
                    user_input=f"Input {i}",
                    isla_response=f"Response {i}",
                    important=(i == 0),  # Mark first as important
                )
                store.save_memory(memory)
            
            # Check updated stats
            stats = store.get_memory_summary()
            self.assertEqual(stats["total_memories"], 3)
            self.assertEqual(stats["important_count"], 1)

    def test_voice_loop_with_personality_responder(self) -> None:
        """Test voice loop with personality-aware responder."""
        with patch.dict(
            os.environ,
            {
                "ISLA_VOICE_PROJECT_DIR": str(self.root),
                "ISLA_VOICE_MODEL_DIR": str(self.root / "model"),
                "ISLA_VOICE_DATASET_DIR": str(self.root / "dataset"),
                "ISLA_VOICE_ENV_DIR": str(self.root / ".venv"),
                "ISLA_VOICE_WAV_DIR": str(self.wav_dir),
                "ISLA_USE_MIC": "false",
                "ISLA_ALLOW_KEYBOARD_FALLBACK": "false",
            },
            clear=False,
        ):
            loop = VoiceLoop()
            
            # Create a personality-aware responder
            def personality_responder(text: str) -> str:
                few_shot = get_few_shot_prompt(num_examples=3)
                return f"[Guided by personality] Response to: {text}"
            
            with patch.object(type(loop), "speak", return_value=None):
                result = loop.respond("Tell me about yourself", personality_responder)
            
            self.assertIn("Guided by personality", result)

    def test_interactive_loop_integration(self) -> None:
        """Test that interactive loop components integrate properly."""
        from ISLA.voice.interactive_loop import InteractiveVoiceLoop
        
        with patch.dict(
            os.environ,
            {
                "ISLA_VOICE_PROJECT_DIR": str(self.root),
                "ISLA_VOICE_MODEL_DIR": str(self.root / "model"),
                "ISLA_VOICE_DATASET_DIR": str(self.root / "dataset"),
                "ISLA_VOICE_ENV_DIR": str(self.root / ".venv"),
                "ISLA_VOICE_WAV_DIR": str(self.wav_dir),
            },
            clear=False,
        ):
            with tempfile.TemporaryDirectory() as tmpdir:
                # Use a temp database for the loop
                db_path = Path(tmpdir) / "memories.db"
                
                loop = InteractiveVoiceLoop(use_mic=False)
                loop.memory_store.db_path = db_path
                
                # Verify components are initialized
                self.assertIsNotNone(loop.voice_loop)
                self.assertIsNotNone(loop.memory_store)
                self.assertIsNotNone(loop.responder)
                self.assertEqual(loop.stats["turns"], 0)
