"""Voice asset discovery for Isla."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOICE_PROJECT_DIR = WORKSPACE_ROOT / "local_voice"
DEFAULT_VOICE_MODEL_DIR = DEFAULT_VOICE_PROJECT_DIR / "my_waifu_model"
DEFAULT_VOICE_DATASET_DIR = DEFAULT_VOICE_PROJECT_DIR / "dataset"
DEFAULT_WAIFU_ENV_DIR = WORKSPACE_ROOT / ".venv"
DEFAULT_WAV_DIR = DEFAULT_VOICE_PROJECT_DIR / "wavs"


def _path_from_env(env_name: str, fallback: Path) -> Path:
    raw_value = os.getenv(env_name)
    if raw_value:
        return Path(raw_value).expanduser()
    return fallback.expanduser()


@dataclass(slots=True)
class VoiceAssetPaths:
    """Configured voice sources used by the local voice loop."""

    project_dir: Path = field(default_factory=lambda: _path_from_env("ISLA_VOICE_PROJECT_DIR", DEFAULT_VOICE_PROJECT_DIR))
    model_dir: Path = field(default_factory=lambda: _path_from_env("ISLA_VOICE_MODEL_DIR", DEFAULT_VOICE_MODEL_DIR))
    dataset_dir: Path = field(default_factory=lambda: _path_from_env("ISLA_VOICE_DATASET_DIR", DEFAULT_VOICE_DATASET_DIR))
    waifu_env_dir: Path = field(default_factory=lambda: _path_from_env("ISLA_VOICE_ENV_DIR", DEFAULT_WAIFU_ENV_DIR))
    wav_dir: Path = field(default_factory=lambda: _path_from_env("ISLA_VOICE_WAV_DIR", DEFAULT_WAV_DIR))

    def existing_paths(self) -> dict[str, Path]:
        """Return the configured paths that currently exist on disk."""

        configured_paths = {
            "project_dir": self.project_dir,
            "model_dir": self.model_dir,
            "dataset_dir": self.dataset_dir,
            "waifu_env_dir": self.waifu_env_dir,
            "wav_dir": self.wav_dir,
        }
        return {name: path for name, path in configured_paths.items() if path.exists()}

    def reference_wavs(self) -> list[Path]:
        """Collect candidate reference wavs from the configured directories."""

        candidates: list[Path] = []
        searched_directories = [self.wav_dir, self.project_dir, self.model_dir, self.dataset_dir]

        for directory in searched_directories:
            if not directory.exists():
                continue
            candidates.extend(sorted(directory.rglob("*.wav")))

        unique_candidates: list[Path] = []
        seen_paths: set[Path] = set()
        for candidate in candidates:
            if candidate in seen_paths:
                continue
            seen_paths.add(candidate)
            unique_candidates.append(candidate)

        return unique_candidates

    def preferred_reference_wav(self) -> Path | None:
        """Return the first usable voice sample, if one exists."""

        wavs = self.reference_wavs()
        if wavs:
            return wavs[0]
        return None