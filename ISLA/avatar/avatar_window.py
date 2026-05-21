"""
Always-on-top transparent avatar display window for Isla.

Shows a PNG sprite for the current emotion. Sits in the corner of the screen,
transparent background, no window chrome. Swap sprites by calling set_emotion().

Usage (standalone):
    python -m ISLA.avatar.avatar_window

Usage (from code):
    from ISLA.avatar.avatar_window import AvatarWindow
    win = AvatarWindow()
    win.set_emotion("happy")
    win.run()          # blocks — call from a thread if needed
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Where sprite PNGs live: ISLA/avatar/sprites/<emotion>.png
_SPRITE_DIR = Path(__file__).parent / "sprites"

# Fallback colour shown when no sprite exists for an emotion
_EMOTION_COLOURS: dict[str, str] = {
    "neutral":   "#A8C8E8",
    "happy":     "#FFD580",
    "sad":       "#8899BB",
    "surprised": "#FF9966",
    "thinking":  "#B8A8D8",
}

_DEFAULT_SIZE = (220, 300)   # px — smaller default for compact avatar
_CORNER_OFFSET = (20, 20)    # px from bottom-right corner


class AvatarWindow:
    """Transparent, always-on-top window that displays Isla's avatar sprite."""

    def __init__(self) -> None:
        self._root: tk.Tk | None = None
        self._label: tk.Label | None = None
        self._current_emotion = "neutral"
        self._photo: object = None  # keep reference to prevent GC
        self._ready = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_emotion(self, emotion: str) -> None:
        """Thread-safe: update the displayed sprite/colour."""
        self._current_emotion = emotion
        if self._root is not None:
            self._root.after(0, self._update_display)

    def run(self) -> None:
        """Start the Tk main loop (blocks). Call from a dedicated thread."""
        self._root = tk.Tk()
        self._setup_window()
        self._ready.set()
        self._root.mainloop()

    def run_in_thread(self) -> threading.Thread:
        """Launch the window in a daemon thread and return it."""
        t = threading.Thread(target=self.run, daemon=True, name="isla-avatar")
        t.start()
        self._ready.wait(timeout=5)
        return t

    def close(self) -> None:
        if self._root is not None:
            self._root.after(0, self._root.destroy)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        root = self._root
        assert root is not None

        root.title("Isla")
        root.overrideredirect(True)          # no title bar / chrome
        root.attributes("-topmost", True)    # always on top
        root.attributes("-alpha", 0.92)      # slight transparency

        # Transparent background (Windows uses -transparentcolor; macOS uses -transparent)
        try:
            root.attributes("-transparentcolor", "black")
            root.configure(bg="black")
        except tk.TclError:
            # Try the macOS-style transparent attribute, fall back to a solid bg.
            try:
                root.attributes("-transparent", True)
                # Allow widgets to inherit a truly transparent background where supported
                root.configure(bg="systemTransparent")
            except tk.TclError:
                root.configure(bg="black")

        w, h = _DEFAULT_SIZE
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        ox, oy = _CORNER_OFFSET
        x = sw - w - ox
        y = sh - h - oy
        root.geometry(f"{w}x{h}+{x}+{y}")

        # Use a standard arrow cursor to avoid platform-specific cursor artifacts
        self._label = tk.Label(root, bg=root.cget("bg"), cursor="arrow")
        self._label.pack(fill="both", expand=True)

        # Allow dragging
        self._label.bind("<ButtonPress-1>", self._drag_start)
        self._label.bind("<B1-Motion>", self._drag_motion)

        self._update_display()

    def _update_display(self) -> None:
        if self._label is None:
            return

        emotion = self._current_emotion
        sprite_path = _SPRITE_DIR / f"{emotion}.png"

        if sprite_path.exists():
            try:
                from PIL import Image, ImageTk  # type: ignore
                img = Image.open(sprite_path).resize(_DEFAULT_SIZE, Image.LANCZOS)
                self._photo = ImageTk.PhotoImage(img)
                self._label.configure(image=self._photo, bg=root.cget("bg"))
                return
            except ImportError:
                pass  # Pillow not installed — fall through to colour block

        # Fallback: solid colour block with emotion label
        colour = _EMOTION_COLOURS.get(emotion, "#CCCCCC")
        self._label.configure(
            image="",
            bg=colour,
            text=f"Isla\n{emotion}",
            fg="white",
            font=("Helvetica", 14, "bold"),
            compound="center",
        )
        self._photo = None

    # Drag support
    def _drag_start(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_motion(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._root is None:
            return
        x = self._root.winfo_x() + (event.x - self._drag_x)
        y = self._root.winfo_y() + (event.y - self._drag_y)
        self._root.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    import time

    win = AvatarWindow()
    win.run_in_thread()

    for emo in ["neutral", "happy", "surprised", "thinking", "sad", "neutral"]:
        print(f"→ {emo}")
        win.set_emotion(emo)
        time.sleep(2)

    win.close()
