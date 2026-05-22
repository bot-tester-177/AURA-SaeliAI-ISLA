# Isla Verification Checklist

Use this checklist after any change that might affect runtime behavior.

## One-Command Baseline

Run the full component suite:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Run a syntax-level pass over the package:

```bash
python -m compileall ISLA
```

## Phase-by-Phase Checks

### Phase 0 - Project Setup

What it proves:

- The package imports cleanly.
- The manifest file is present and loadable.
- The repo skeleton matches the intended shape.

Run:

- `python -m compileall ISLA`
- `python -m unittest tests.core.test_manifest_and_brain.ManifestAndBrainTests.test_manifest_loads_and_identity_context_is_available`

### Phase 1 - Identity First

What it proves:

- Isla loads identity rules from the manifest.
- The system prompt and manifest context are stable.
- Basic command routing preserves the persona entry points.

Run:

- `python -m unittest tests.test_manifest_and_brain`
- `python -m unittest tests.core.test_manifest_and_brain`

### Phase 2 - Voice Prototype

What it proves:

- Voice asset discovery works.
- A response can be produced without touching the real mic or TTS backend.

Run:

- `python -m unittest tests.test_voice`
- `python -m unittest tests.voice.test_voice`
- Optional hardware smoke test: `python ISLA/voice/test_tts.py "Hello world"`

### Phase 3 - Memory Prototype

What it proves:

- Structured facts persist in SQLite.
- Recent memory and search both return usable results.
- Local documents can be ingested and queried.

Run:

- `python -m unittest tests.test_memory_and_documents`
- `python -m unittest tests.memory.test_memory_and_documents`

### Phase 4 - Tooling and Brain

What it proves:

- Tool registration and execution are deterministic.
- Command routing can call memory and tool paths directly.
- App wiring still connects the core and voice layers.

Run:

- `python -m unittest tests.test_tools`
- `python -m unittest tests.tools.test_tools`
- `python -m unittest tests.core.test_manifest_and_brain`
- `python -m unittest tests.app.test_app`

### Phase 5 - Visual and Presence Layers

What it proves:

- Emotion tagging still maps text to the expected avatar states.
- Wake-word parsing still isolates the user question.
- The VTube bridge still formats and forwards requests correctly.

Run:

- `python -m unittest tests.test_presence`
- `python -m unittest tests.presence.test_presence`

## Practical Rerun Order

1. Run `python -m unittest discover -s tests -p "test_*.py"`.
2. If that fails, run the matching component file from the phase list above.
3. If the failure is import or syntax related, run `python -m compileall ISLA`.
4. If the failure is voice hardware related, use the optional TTS smoke test separately.

## Code Quality Checks

### Python Version Compatibility

Verify no deprecated APIs are in use:

```bash
# Check for Python 3.13 deprecated datetime.utcnow() calls
grep -r "utcnow" ISLA/
```

Expected: No matches (all should be replaced with `datetime.now(UTC)`)

### Type Checking (Optional)

If using `pyright` or `mypy`:

```bash
# Check code without running
pyright ISLA/
```

## Runtime Integration Tests

### Voice I/O End-to-End (requires audio hardware)

```bash
# Test STT + LLM + TTS pipeline
ISLA_INTERACTIVE_LOOP=true python -m ISLA
```

Expected: Speak into mic, hear response back

### Avatar Rendering (requires display)

```bash
# Test emotion tagging + sprite rendering
ISLA_ENABLE_AVATAR=true python -m ISLA
```

Expected: Avatar window appears, changes emotion based on responses

### Memory Persistence

```bash
# Test that facts persist across sessions
python -m ISLA
# Input: "Remember that my favorite color is blue"
# Exit: Ctrl+C
# Restart
python -m ISLA
# Input: "What's my favorite color?"
```

Expected: Isla recalls "blue"

## Post-Change Validation

After any code change:

1. ✅ Syntax check: `python -m compileall ISLA tests`
2. ✅ Unit tests: `python -m unittest discover -s tests -p "test_*.py"`
3. ✅ Runtime test: `python -m ISLA` (interactive, manual testing)
4. ✅ Documentation update: If new features, update ISLA/README.md