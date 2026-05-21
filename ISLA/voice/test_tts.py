"""Simple helper to test local TTS via `VoiceLoop`.

Usage:
  python ISLA/voice/test_tts.py "Hello world"

Set environment variables to point at your voice/model/wav dirs, for example:
  export ISLA_VOICE_PROJECT_DIR=/Users/jessiejavanbrown/Desktop/waifu_voice
  export ISLA_VOICE_MODEL_DIR=/Users/jessiejavanbrown/Desktop/waifu_voice/my_waifu_model/waifu_tacotron2-July-07-2025_06+16PM-0000000
  export ISLA_VOICE_WAV_DIR=/Users/jessiejavanbrown/Downloads/LibriTTS_2/test-clean/3570/waifu
  export ISLA_VOICE_TTS_COMMAND=tts

The script will attempt to run the configured TTS command and play the output.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else argv
    text = "Everyone sing one" if not argv else " ".join(argv)

    # Ensure workspace root is on sys.path so we can import package modules.
    workspace_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(workspace_root))

    try:
        from ISLA.voice.voice_loop import VoiceLoop
    except Exception as exc:
        print("Failed to import VoiceLoop:", exc)
        return 2

    loop = VoiceLoop()

    print("Configured asset paths:")
    for name, path in loop.assets.existing_paths().items():
        print(f" - {name}: {path}")

    print("Using TTS command:", loop.tts_command)
    print("Using TTS model name:", loop.tts_model_name)

    try:
        loop.speak(text)
    except Exception as exc:
        print("TTS run failed:", exc)
        return 3

    print("TTS test completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
