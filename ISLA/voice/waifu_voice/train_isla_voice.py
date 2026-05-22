#!/usr/bin/env python3
"""Train Tacotron2 TTS model for Isla's voice."""

import os
import sys
from pathlib import Path

# Set thread limits for CPU-friendly training
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

from TTS.tts.configs.shared_configs import BaseDatasetConfig
from TTS.tts.configs.tacotron2_config import Tacotron2Config
from TTS.tts.models.tacotron2 import Tacotron2
from TTS.config.shared_configs import BaseAudioConfig

# Paths
WAIFU_VOICE_DIR = Path(__file__).parent
DATASET_DIR = WAIFU_VOICE_DIR / "my_waifu_dataset"
MODEL_OUTPUT_DIR = WAIFU_VOICE_DIR / "my_waifu_model"

# Ensure model output directory exists
MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Dataset configuration
dataset_config = BaseDatasetConfig(
    formatter="ljspeech",
    meta_file_train="metadata.csv",
    path=str(DATASET_DIR)
)

# Model configuration - tuned for 79 training samples
# Reduced epochs and batch size for smaller dataset
config = Tacotron2Config(
    audio=BaseAudioConfig(sample_rate=22050),
    run_name="waifu_tacotron2_isla",
    num_chars=148,
    batch_size=2,               # Reduced from 4 for smaller dataset
    eval_batch_size=1,          # Reduced from 2
    num_loader_workers=0,
    num_eval_loader_workers=0,
    run_eval=True,              # Run evaluation during training
    test_delay_epochs=10,       # Start testing after 10 epochs
    epochs=200,                 # Reduced from 500 for faster iteration
    text_cleaner="english_cleaners",
    output_path=str(MODEL_OUTPUT_DIR),
    datasets=[dataset_config],
    print_step=10,              # Print loss every 10 steps
    print_eval=True,
    use_phoneme_binarizer=False,
    phoneme_language="en-us",
)

print("=" * 60)
print("ISLA Voice Training - Tacotron2 TTS")
print("=" * 60)
print(f"Dataset: {DATASET_DIR}")
print(f"Samples: 79 utterances")
print(f"Output: {MODEL_OUTPUT_DIR}")
print(f"Epochs: {config.epochs}")
print(f"Batch size: {config.batch_size}")
print("=" * 60)
print()

# Initialize and train model
try:
    model = Tacotron2(config)
    print("✓ Model initialized")
    print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")
    print()
    
    print("Starting training...")
    print()
    model.fit()
    
    print()
    print("=" * 60)
    print("✓ Training completed successfully!")
    print(f"  Model saved to: {MODEL_OUTPUT_DIR}")
    print("=" * 60)
    
except KeyboardInterrupt:
    print("\n⚠ Training interrupted by user")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Training failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
