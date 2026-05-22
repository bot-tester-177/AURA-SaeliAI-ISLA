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

### Voice Model Setup & Tuning

For speaker-cloned TTS with XTTS v2:

1. **Prepare speaker reference samples** (3-5 seconds of clean audio):
   - Record 2-3 `.wav` files (22 kHz, mono) of Isla's target voice
   - Place them in `ISLA/local_voice/wavs/`

2. **Train or initialize the cloning model**:
   - If using Coqui TTS with XTTS v2: `pip install coqui-tts`
   - Run `voice_loop.py test` to verify voice asset discovery
   - Model will auto-download on first use (~2GB)

3. **Test speaker cloning**:
   - Run `python ISLA/voice/test_tts.py "Hello world"` to test TTS output
   - Verify output matches the reference speaker characteristics
   - Adjust `ISLA_VOICE_*` paths if files aren't being discovered

4. **Personality tuning via prompts**:
   - Voice tone is shaped primarily by the system prompt in `ISLA/prompts/system_prompt.md`
   - Few-shot examples in the prompt improve consistency
   - Test with `python -m ISLA` and adjust system prompt as needed

## Running Locally

Start the package with `python -m ISLA` from the repository root.

The current loop is mic-in, voice-out by default:

- STT: Whisper (`ISLA_USE_MIC=true` by default)
- TTS: local XTTS-compatible CLI if available, otherwise macOS `say`

The always-on wake-word daemon is the default launch mode. It uses faster-whisper to listen for "Isla", then hands the captured request to Isla's normal response pipeline. If you want the old interactive loop instead, set `ISLA_INTERACTIVE_LOOP=true` before launching. If you also want the avatar window, leave `ISLA_ENABLE_AVATAR=true`.

Useful wake-word tuning flags:

- `ISLA_WAKE_WORD_MODEL` defaults to `base`
- `ISLA_WAKE_WORD_PATTERN` defaults to `\b(?:hey\s+)?isla\b`
- `ISLA_WAKE_WORD_CHUNK_SECONDS` defaults to `1.5`
- `ISLA_WAKE_WORD_QUESTION_SECONDS` defaults to `7.0`

If you want a keyboard fallback instead of microphone-only behavior, set:

- `ISLA_ALLOW_KEYBOARD_FALLBACK=true`

If microphone STT is enabled, install local dependencies such as `openai-whisper`, `sounddevice`, and `soundfile` in your Python environment.

Isla defaults to the Ollama `mistral` model. Pull it once with `ollama pull mistral` or override it with `ISLA_OLLAMA_MODEL` if you want to experiment.

### Avatar and Visual Presence

Enable Isla's avatar window with:

```bash
ISLA_ENABLE_AVATAR=true python -m ISLA
```

The avatar responds to emotion tags in Isla's responses:
- **neutral**: Default listening/waiting state
- **happy**: Positive or humorous responses
- **sad**: Empathetic or supportive responses  
- **surprised**: Novel information or unexpected turns
- **thinking**: Processing or deliberating

Emotion tagging happens automatically via `emotion_tagger.py`. Sprite images are located in `ISLA/avatar/sprites/`.

For custom avatars:
- Replace `.png` files in `ISLA/avatar/sprites/` with your own emotion states
- Emotion tags are extracted from response text by `emotion_tagger.py`
- Avatar window is optional; full app runs without it

The memory layer now persists structured facts in SQLite and indexes semantic recall in ChromaDB when the package is installed. If ChromaDB is unavailable, Isla falls back to SQLite-backed keyword recall so the app still runs locally.

Local document memory is separate from session memory. Use `file.read` to ingest a file or folder into the local document index, then ask follow-up questions that reuse `file.search`-style retrieval through the normal assistant loop. When ChromaDB is available, Isla uses it for the vector index; otherwise the same chunks are searched through a local sqlite-backed embedding index. PDF support requires `pypdf`.

Default memory files live under `/.isla_memory/` in the repository root. Set `ISLA_MEMORY_ROOT` to move the store, or keep `ISLA_MEMORY_PATH` for a legacy-style override.

## Moving To Another Desktop

1. Copy the repository folder to the other machine.
2. Copy your voice model and wav files into `ISLA/local_voice/` or set the `ISLA_VOICE_*` environment variables on the new machine.
3. Recreate the Python environment there, then run `python -m ISLA`.
