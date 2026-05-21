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
