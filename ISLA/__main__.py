"""Run Isla as a module."""

from __future__ import annotations

import os
import sys

from pathlib import Path

from .app import IslaApp


def main() -> None:
    manifest_path = Path(__file__).resolve().parent / "manifest" / "isla.yaml"
    app = IslaApp(manifest_path=manifest_path)

    use_interactive_loop = os.getenv("ISLA_INTERACTIVE_LOOP", "false").lower() in {"1", "true", "yes"}
    if use_interactive_loop:
        app.run_loop()
        return

    use_wake_word = os.getenv("ISLA_WAKE_WORD_DAEMON", "true").lower() in {"1", "true", "yes"}
    if use_wake_word:
        avatar_window = None
        if os.getenv("ISLA_ENABLE_AVATAR", "true").lower() in {"1", "true", "yes"}:
            try:
                from .avatar.avatar_window import AvatarWindow

                avatar_window = AvatarWindow()
                # On macOS, Tk must be created and run on the main thread. Start
                # the wake-word daemon in a background thread and run the avatar
                # mainloop here instead to avoid AppKit threading errors.
                if sys.platform == "darwin":
                    import threading as _threading

                    _threading.Thread(
                        target=app.run_wake_word_daemon,
                        kwargs={"avatar_window": avatar_window},
                        daemon=True,
                    ).start()
                    avatar_window.run()
                    return
                else:
                    avatar_window.run_in_thread()
            except Exception:
                avatar_window = None

        app.run_wake_word_daemon(avatar_window=avatar_window)
        return

    app.run_loop()


if __name__ == "__main__":
    main()