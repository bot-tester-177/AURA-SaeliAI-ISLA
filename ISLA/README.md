# ISLA Component Skeleton

This directory is the initial component scaffold for Isla.

## Components

- brain: identity and orchestration
- voice: local speech in and out
- memory: layered persistence and retrieval
- tools: safe action routing
- avatar: visual identity and expression rules
- ar: augmented-reality presence spec
- hardware: device and physical build notes
- prompts: canonical system prompt assets
- manifest: versioned source of truth for Isla's identity

## Voice Setup

The voice loop now reads local asset locations from environment variables and falls back to repo-relative folders so the workspace can move between machines cleanly.

- `ISLA_VOICE_PROJECT_DIR` defaults to `ISLA/local_voice`
- `ISLA_VOICE_MODEL_DIR` defaults to `ISLA/local_voice/my_waifu_model`
- `ISLA_VOICE_DATASET_DIR` defaults to `ISLA/local_voice/dataset`
- `ISLA_VOICE_ENV_DIR` defaults to `.venv`
- `ISLA_VOICE_WAV_DIR` defaults to `ISLA/local_voice/wavs`

`ISLA/voice/voice_loop.py` will use the first `.wav` file it finds in those locations as the speaker reference for a local TTS backend such as Coqui TTS with XTTS-compatible speaker cloning.

## Running Locally

Start the package with `python -m ISLA` from the repository root. The current loop is text-in, voice-out by default, and it will use your local voice reference files when a compatible TTS backend is available.

## Moving To Another Desktop

1. Copy the repository folder to the other machine.
2. Copy your voice model and wav files into `ISLA/local_voice/` or set the `ISLA_VOICE_*` environment variables on the new machine.
3. Recreate the Python environment there, then run `python -m ISLA`.
