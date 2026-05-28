#!/usr/bin/env python3
"""End-to-end test: Use trained Isla voice model for real-time speech synthesis.

This is the final validation step after training completes.
It demonstrates Isla speaking like Siri/Alexa with the trained voice.
"""

import sys
from pathlib import Path

# Ensure workspace is on path
workspace = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(workspace))

def test_trained_model():
    """Test the trained Tacotron2 + HiFi-GAN voice."""
    print("=" * 70)
    print("ISLA VOICE MODEL - REAL-TIME SYNTHESIS TEST")
    print("=" * 70)
    print()

    try:
        from ISLA.voice.waifu_voice.isla_voice_synthesizer import IslaVoiceSynthesizer
    except ImportError as e:
        print(f"ERROR: Failed to import synthesizer: {e}")
        print()
        print("Make sure TTS library is installed:")
        print("  pip install TTS torch numpy scipy librosa soundfile sounddevice")
        return False

    # Test 1: Initialize
    print("[1/4] Initializing voice synthesizer...")
    try:
        synth = IslaVoiceSynthesizer(device="cpu")
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    print("✓ Synthesizer created")
    print()

    # Test 2: Load model
    print("[2/4] Loading trained model...")
    try:
        synth.load()
    except Exception as e:
        print(f"ERROR: Failed to load model: {e}")
        print()
        print("Make sure training is complete and the model exists at:")
        print(f"  {synth.model_dir}")
        return False
    print()

    # Test 3: Synthesize
    print("[3/4] Synthesizing speech...")
    test_phrases = [
        "Hello, I am Isla.",
        "I'm your personal AI assistant.",
        "Ready to help you anytime.",
    ]

    for phrase in test_phrases:
        try:
            wav = synth.synthesize(phrase)
            print(f"✓ Generated {len(wav) / 22050:.1f}s of audio")
        except Exception as e:
            print(f"ERROR: Synthesis failed: {e}")
            return False

    print()

    # Test 4: Play (optional, if sounddevice available)
    print("[4/4] Playing audio...")
    try:
        from ISLA.voice.waifu_voice.isla_voice_synthesizer import synthesize_and_play

        test_text = "I'm Isla, and I'm ready to talk."
        print(f"Saying: '{test_text}'")
        print()
        synthesize_and_play(test_text)
        print()
        print("✓ Audio playback complete")
    except Exception as e:
        print(f"⚠ Playback not available: {e}")
        print("  (Audio was synthesized successfully)")

    print()
    print("=" * 70)
    print("✓✓✓ SUCCESS! Isla can now speak like Siri/Alexa ✓✓✓")
    print("=" * 70)
    print()
    print("The trained voice model is ready to use in:")
    print("  - voice_loop_with_model.py (real-time interaction)")
    print("  - isla_voice_synthesizer.py (batch synthesis)")
    print()
    print("To use in your app:")
    print("  from ISLA.voice.voice_loop_with_model import VoiceLoopWithIslaModel")
    print("  loop = VoiceLoopWithIslaModel()")
    print("  loop.speak('Hello world!')")
    print()
    return True


if __name__ == "__main__":
    success = test_trained_model()
    sys.exit(0 if success else 1)
