"""Always-on wake-word listener for Isla."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..app import IslaApp


@dataclass(slots=True)
class WakeWordDaemon:
    """Continuously listens for the wake word and hands off the question text."""

    app: "IslaApp"
    avatar_window: Any | None = None
    wake_word_pattern: str = field(default_factory=lambda: os.getenv("ISLA_WAKE_WORD_PATTERN", r"\b(?:hey\s+)?isla\b"))
    wake_model_name: str = field(default_factory=lambda: os.getenv("ISLA_WAKE_WORD_MODEL", "base"))
    wake_language: str = field(default_factory=lambda: os.getenv("ISLA_WAKE_WORD_LANGUAGE", "en"))
    wake_device: str = field(default_factory=lambda: os.getenv("ISLA_WAKE_WORD_DEVICE", "cpu"))
    wake_compute_type: str = field(default_factory=lambda: os.getenv("ISLA_WAKE_WORD_COMPUTE_TYPE", "int8"))
    sample_rate: int = field(default_factory=lambda: int(os.getenv("ISLA_WAKE_WORD_SAMPLE_RATE", "16000")))
    wake_chunk_seconds: float = field(default_factory=lambda: float(os.getenv("ISLA_WAKE_WORD_CHUNK_SECONDS", "1.5")))
    question_seconds: float = field(default_factory=lambda: float(os.getenv("ISLA_WAKE_WORD_QUESTION_SECONDS", "7.0")))

    def run(self) -> None:
        model = self._load_model()
        self._set_avatar("neutral")
        logger.info("Wake-word daemon started.")

        while True:
            try:
                transcript = self._listen_for_wake_word(model)
                if not transcript:
                    continue

                question = self._extract_question(transcript)
                if not question:
                    question = self._listen_for_follow_up(model)

                if not question:
                    continue

                self._set_avatar("thinking")
                logger.info("Wake word detected; processing question: %s", question)
                try:
                    self.app.run_transcript(question)
                finally:
                    self._set_avatar("neutral")
            except KeyboardInterrupt:
                self._set_avatar("neutral")
                raise
            except Exception as exc:
                self._set_avatar("neutral")
                logger.exception("Wake-word daemon error: %s", exc)

    def _load_model(self) -> Any:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is required for wake-word detection. Install it with the project dependencies."
            ) from exc

        return WhisperModel(
            self.wake_model_name,
            device=self.wake_device,
            compute_type=self.wake_compute_type,
        )

    def _listen_for_wake_word(self, model: Any) -> str:
        while True:
            audio = self._record_audio(self.wake_chunk_seconds)
            transcript = self._transcribe(model, audio)
            if transcript and self._contains_wake_word(transcript):
                return transcript

    def _listen_for_follow_up(self, model: Any) -> str:
        # Capture a slightly longer utterance after the wake word so the user
        # can say the whole request in one breath.
        audio = self._record_audio(self.question_seconds)
        return self._extract_question(self._transcribe(model, audio))

    def _record_audio(self, duration_seconds: float) -> Any:
        try:
            import sounddevice as sd  # type: ignore
        except ImportError as exc:
            raise RuntimeError("sounddevice is required for microphone capture.") from exc

        frames = max(1, int(duration_seconds * self.sample_rate))
        recording = sd.rec(frames, samplerate=self.sample_rate, channels=1, dtype="float32")
        sd.wait()
        return recording[:, 0] if getattr(recording, "ndim", 1) > 1 else recording

    def _transcribe(self, model: Any, audio: Any) -> str:
        segments, _info = model.transcribe(
            audio,
            language=self.wake_language,
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments if segment.text).strip()

    def _contains_wake_word(self, transcript: str) -> bool:
        return re.search(self.wake_word_pattern, transcript, flags=re.IGNORECASE) is not None

    def _extract_question(self, transcript: str) -> str:
        match = re.search(self.wake_word_pattern, transcript, flags=re.IGNORECASE)
        if match is None:
            return transcript.strip()

        remainder = transcript[match.end():].strip()
        remainder = remainder.lstrip(" ,.:;!?-")
        return remainder.strip()

    def _set_avatar(self, emotion: str) -> None:
        if self.avatar_window is None:
            return

        try:
            self.avatar_window.set_emotion(emotion)
        except Exception:
            logger.debug("Avatar update failed for emotion %s", emotion)