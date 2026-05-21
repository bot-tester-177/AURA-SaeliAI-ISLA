# AURA-SaeliAI-ISLA
A detailed development archive/plan for building "Isla" — a local,   private AI companion with personality, voice, memory, and eventually a   physical/AR presence.

See [docs/isla-update-2026-v1.md](docs/isla-update-2026-v1.md) for the structured roadmap and system spec.

See [docs/implementation-plan.md](docs/implementation-plan.md) to start with the execution plan.

## VS Code Setup

This repository now includes a `.vscode/` folder with launch, task, and extension recommendations so it opens cleanly on another machine, including your HP Pavilion gaming desktop.

1. Open the repo folder in VS Code.
2. Create or recreate the virtual environment in `.venv`.
3. Copy `.env.example` to `.env` and adjust any machine-specific voice or audio paths.
4. Use the `Isla: Run Module` launch config or the `Isla: Run Module` task to start the app.

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
