#!/usr/bin/env python3
"""Real-time Tacotron2 + HiFi-GAN inference for Isla's voice synthesis.

This module loads the trained Tacotron2 model and uses HiFi-GAN vocoder
to generate high-quality audio that can be played back in real-time,
similar to Siri or Alexa.
"""

import os
from pathlib import Path
from typing import Optional
import numpy as np


class IslaVoiceSynthesizer:
    """Synthesize speech using trained Tacotron2 + HiFi-GAN vocoder."""

    def __init__(
        self,
        model_dir: Optional[Path] = None,
        device: str = "cpu",
        vocoder_name: str = "hifigan_v3",
    ):
        """Initialize the synthesizer.

        Args:
            model_dir: Path to trained model directory
            device: 'cpu' or 'cuda' (GPU)
            vocoder_name: Vocoder model to use for mel-to-wav conversion
        """
        self.device = device
        self.vocoder_name = vocoder_name

        # Locate trained model
        if model_dir is None:
            workspace = Path(__file__).resolve().parents[3]
            model_dir = workspace / "ISLA" / "voice" / "waifu_voice" / "my_waifu_model"
        else:
            model_dir = Path(model_dir)

        self.model_dir = model_dir
        self.model = None
        self.vocoder = None
        self._ap = None

        print(f"IslaVoiceSynthesizer initialized (device: {device}, vocoder: {vocoder_name})")

    def load(self) -> None:
        """Load trained Tacotron2 model and HiFi-GAN vocoder."""
        if self.model is not None:
            print("Model already loaded")
            return

        try:
            from TTS.tts.models.tacotron2 import Tacotron2
            from TTS.vocoder.models.hifigan import HifiGan
            from TTS.utils.audio.processor import AudioProcessor
        except ImportError as e:
            raise ImportError("TTS library required. Install with: pip install TTS") from e

        print(f"Loading model from: {self.model_dir}")

        # Find the actual checkpoint directory (nested under run_name folder)
        checkpoint_dirs = list(self.model_dir.glob("waifu_tacotron2*"))
        if not checkpoint_dirs:
            raise FileNotFoundError(f"No trained model found in {self.model_dir}")

        checkpoint_dir = checkpoint_dirs[0]
        print(f"Using checkpoint: {checkpoint_dir}")

        # Load Tacotron2
        config_path = checkpoint_dir / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")

        print("Loading Tacotron2 model...")
        self.model = Tacotron2.init_from_config(config_path, verbose=False)
        self.model = self.model.to(self.device)
        self.model.eval()

        # Load vocoder (HiFi-GAN for high-quality audio)
        print(f"Loading vocoder: {self.vocoder_name}...")
        self.vocoder = HifiGan.init_from_raw_dict(
            {
                "model_name": self.vocoder_name,
                "vocoder_name": self.vocoder_name,
                "vocoder_model_path": None,  # Use default pre-trained
                "vocoder_config_path": None,
            }
        )
        self.vocoder = self.vocoder.to(self.device)
        self.vocoder.eval()

        # Initialize audio processor
        self._ap = AudioProcessor.init_from_config(self.model.config.audio)
        print("✓ Synthesizer ready!")

    def synthesize(self, text: str) -> np.ndarray:
        """Synthesize audio from text.

        Args:
            text: Input text to synthesize

        Returns:
            Audio waveform as numpy array (mono, 22050 Hz)
        """
        if self.model is None:
            self.load()

        import torch

        print(f"Synthesizing: {text[:50]}...")

        with torch.no_grad():
            # Generate mel-spectrogram
            mel_spec, alignment, stop_tokens = self.model.inference(text)

            # Convert mel-spec to waveform using vocoder
            wav = self.vocoder.inference(mel_spec)

        # Convert tensor to numpy and normalize
        wav = wav.detach().cpu().numpy()
        if wav.ndim > 1:
            wav = wav[0]  # Take first channel if stereo

        # Normalize to [-1, 1] range
        wav = wav / np.max(np.abs(wav)) if np.max(np.abs(wav)) > 0 else wav

        return wav

    def save_wav(self, wav: np.ndarray, output_path: Path, sample_rate: int = 22050) -> None:
        """Save waveform to WAV file.

        Args:
            wav: Audio waveform (numpy array)
            output_path: Path to save WAV file
            sample_rate: Sample rate in Hz
        """
        import soundfile as sf

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure int16 range
        wav_int16 = np.int16(wav * 32767)

        sf.write(str(output_path), wav_int16, sample_rate)
        print(f"✓ Saved: {output_path}")


def synthesize_and_play(text: str, model_dir: Optional[Path] = None) -> None:
    """Synthesize text and play audio (like Siri/Alexa).

    Args:
        text: Text to synthesize
        model_dir: Path to trained model
    """
    import subprocess
    import tempfile

    synth = IslaVoiceSynthesizer(model_dir=model_dir)
    synth.load()

    # Synthesize
    wav = synth.synthesize(text)

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    synth.save_wav(wav, tmp_path)

    # Play audio
    try:
        import sounddevice as sd
        import soundfile as sf

        # Load and play
        data, sr = sf.read(str(tmp_path))
        print(f"Playing audio ({len(data) / sr:.1f}s)...")
        sd.play(data, sr)
        sd.wait()
    except ImportError:
        # Fallback: use system audio player
        player = None
        if os.name == "posix":  # macOS/Linux
            player = "afplay" if os.path.exists("/usr/bin/afplay") else "paplay"
        elif os.name == "nt":  # Windows
            import winsound
            winsound.PlaySound(str(tmp_path), winsound.SND_FILENAME)
            return

        if player:
            subprocess.run([player, str(tmp_path)], check=True)
            print("✓ Playback complete")

    # Cleanup
    tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello, I'm Isla. How can I help you?"
    synthesize_and_play(text)
