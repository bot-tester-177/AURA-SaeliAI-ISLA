"""Keyword-based emotion classifier for Isla's avatar expressions."""

from __future__ import annotations

# Five expressions matching the archive spec + Live2D parameter names
EMOTION_KEYWORDS: dict[str, list[str]] = {
    "happy": [
        "haha", "lol", "love", "great", "amazing", "wonderful", "excited",
        "glad", "happy", "yay", "awesome", "fantastic", "fun", "enjoy",
        "laugh", "smile", "good", "nice", "perfect", "yes!", "sure!",
    ],
    "sad": [
        "sorry", "sad", "miss", "hurt", "cry", "tired", "lonely", "lost",
        "unfortunate", "bad", "awful", "terrible", "depressed", "upset",
        "disappoint", "regret", "wish", "hard", "difficult",
    ],
    "surprised": [
        "wow", "what", "really", "seriously", "no way", "omg", "oh my",
        "unexpected", "sudden", "wait", "whoa", "unbelievable", "shocking",
        "incredible", "can't believe",
    ],
    "thinking": [
        "hmm", "let me", "i think", "maybe", "perhaps", "consider",
        "wonder", "curious", "interesting", "actually", "well,", "so,",
        "analyzing", "calculating", "processing", "figuring",
    ],
}

# Default when nothing matches
DEFAULT_EMOTION = "neutral"


def tag_emotion(text: str) -> str:
    """Return one of: neutral, happy, sad, surprised, thinking."""
    lowered = text.lower()
    scores: dict[str, int] = {emotion: 0 for emotion in EMOTION_KEYWORDS}

    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                scores[emotion] += 1

    best = max(scores, key=lambda e: scores[e])
    return best if scores[best] > 0 else DEFAULT_EMOTION
