# AURA-SaeliAI-ISLA
A detailed development archive/plan for building "Isla" — a local, private AI companion with personality, voice, memory, and eventually a physical/AR presence.

## Project Status

- **Phase 1 - Identity First**: ✅ Complete
- **Phase 2 - Voice and Personality**: ✅ Complete ([Details](docs/phase2-completion.md))
- **Phase 3 - Visual Identity and Memory**: 📋 Pending
- **Phase 4 - Brain and Tools**: 📋 Pending
- **Phase 5 - Final Build**: 📋 Pending

See [docs/isla-update-2026-v1.md](docs/isla-update-2026-v1.md) for the structured roadmap and system spec.

See [docs/implementation-plan.md](docs/implementation-plan.md) for the execution plan.

See [docs/phase2-completion.md](docs/phase2-completion.md) for Phase 2 voice training completion details.

## VS Code Setup

This repository now includes a `.vscode/` folder with launch, task, and extension recommendations so it opens cleanly on another machine, including your HP Pavilion gaming desktop.

1. Open the repo folder in VS Code.
2. Create or recreate the virtual environment in `.venv`.
3. Copy `.env.example` to `.env` and adjust any machine-specific voice or audio paths.
4. Use the `Isla: Run Module` launch config or the `Isla: Run Module` task to start the app.

## Phase 2: Voice Training with Personality Integration

### Quick Start

Run the interactive voice loop to test Isla's personality and voice:
```bash
python -m ISLA.voice.interactive_loop
```

Verify TTS backend is ready:
```bash
python ISLA/voice/tts_verify.py
```

Test voice synthesis with speaker cloning:
```bash
python ISLA/voice/test_tts.py "Hello, I'm Isla"
```

### Features

- **80 Training WAVs**: Speaker samples from LibriTTS (3570_5694) ready for voice cloning
- **5 Personality Examples**: Few-shot prompts to guide consistent tone and behavior
- **Voice Memory**: SQLite persistence for conversations and important interactions
- **Interactive Loop**: Real-time testing with memory and statistics

See [docs/phase2-completion.md](docs/phase2-completion.md) for full details.

## Verification

The test suite is organized by component under `tests/core/`, `tests/memory/`, `tests/tools/`, `tests/voice/`, `tests/presence/`, and `tests/app/`.

Run the full suite from the repo root:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Run a syntax check over the package and tests:

```bash
python -m compileall ISLA tests
```

For a phase-by-phase checklist, see [docs/verification-checklist.md](docs/verification-checklist.md).
