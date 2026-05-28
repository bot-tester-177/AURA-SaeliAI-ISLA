"""Verify TTS backend is installed and working."""

from __future__ import annotations

import sys
from pathlib import Path


def check_tts_available() -> bool:
    """Check if TTS package is installed and importable."""
    try:
        import TTS  # noqa: F401
        return True
    except ImportError:
        return False


def check_tts_command_available() -> bool:
    """Check if 'tts' CLI command is available."""
    import shutil
    return shutil.which("tts") is not None


def check_voice_samples_available() -> bool:
    """Check if voice samples are available for cloning."""
    from ISLA.voice.voice_assets import VoiceAssetPaths

    assets = VoiceAssetPaths()
    return assets.preferred_reference_wav() is not None


def verify_tts_setup() -> dict[str, bool]:
    """Verify all components of TTS setup are ready.
    
    Returns:
        A dict with component names as keys and bool (available) as values.
    """
    return {
        "tts_package": check_tts_available(),
        "tts_command": check_tts_command_available(),
        "voice_samples": check_voice_samples_available(),
    }


def print_tts_status() -> int:
    """Print TTS setup status and return exit code."""
    status = verify_tts_setup()
    
    print("TTS Backend Verification")
    print("-" * 40)
    
    all_ready = True
    for component, available in status.items():
        symbol = "✓" if available else "✗"
        print(f"{symbol} {component}: {'ready' if available else 'not found'}")
        if not available:
            all_ready = False
    
    print("-" * 40)
    
    if all_ready:
        print("TTS setup looks good!")
        return 0
    else:
        print("Some components are missing. Install with: pip install -r requirements.txt")
        print("Or install TTS directly: pip install 'TTS>=0.21.0'")
        return 1


if __name__ == "__main__":
    workspace_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(workspace_root))
    
    raise SystemExit(print_tts_status())
