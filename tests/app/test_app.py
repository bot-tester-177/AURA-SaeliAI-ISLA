from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ISLA.app import IslaApp


class AppTests(TestCase):
    def test_app_wires_core_and_voice_loop_together(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        manifest_path = repo_root / "ISLA" / "manifest" / "isla.yaml"

        with TemporaryDirectory() as tmpdir:
            with patch.dict(
                os.environ,
                {
                    "ISLA_MEMORY_ROOT": str(Path(tmpdir) / "memory"),
                    "ISLA_USE_MIC": "false",
                    "ISLA_ALLOW_KEYBOARD_FALLBACK": "false",
                },
                clear=False,
            ):
                app = IslaApp(manifest_path=manifest_path)

            with patch.object(app.core, "route_input", return_value="wired"), patch.object(
                type(app.voice_loop), "speak", return_value=None
            ):
                self.assertEqual(app.run_transcript("hello"), "wired")