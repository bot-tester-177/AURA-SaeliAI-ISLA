"""Run Isla as a module."""

from __future__ import annotations

from pathlib import Path

from .app import IslaApp


def main() -> None:
    manifest_path = Path(__file__).resolve().parent / "manifest" / "isla.yaml"
    app = IslaApp(manifest_path=manifest_path)
    app.run_loop()


if __name__ == "__main__":
    main()