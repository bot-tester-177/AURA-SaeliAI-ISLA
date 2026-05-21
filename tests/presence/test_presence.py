from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ISLA.avatar.emotion_tagger import tag_emotion
from ISLA.avatar.vtube_bridge import VTubeBridge, _make_request
from ISLA.voice.wake_word_daemon import WakeWordDaemon


class PresenceTests(TestCase):
    def test_emotion_tagger_classifies_common_phrases(self) -> None:
        self.assertEqual(tag_emotion("What, seriously?"), "surprised")
        self.assertEqual(tag_emotion("I am sorry and tired."), "sad")
        self.assertEqual(tag_emotion("Let me think for a moment."), "thinking")
        self.assertEqual(tag_emotion("Plain statement."), "neutral")

    def test_vtube_request_builder_and_bridge_wrapper_work(self) -> None:
        payload = json.loads(_make_request("HotkeyTriggerRequest", {"hotkeyID": "isla_happy"}))
        self.assertEqual(payload["messageType"], "HotkeyTriggerRequest")
        self.assertEqual(payload["data"]["hotkeyID"], "isla_happy")

        async def fake_send_emotion_async(emotion: str, token: str | None = None) -> str:
            self.assertEqual(emotion, "happy")
            self.assertIsNone(token)
            return "token-123"

        class FakeLoop:
            def is_running(self) -> bool:
                return False

            def run_until_complete(self, coro):
                return asyncio.run(coro)

        with patch("ISLA.avatar.vtube_bridge.asyncio.get_event_loop", return_value=FakeLoop()), patch(
            "ISLA.avatar.vtube_bridge.send_emotion_async", side_effect=fake_send_emotion_async
        ):
            bridge = VTubeBridge()
            bridge.send_emotion("happy")

        self.assertEqual(bridge._token, "token-123")

    def test_wake_word_daemon_extracts_questions(self) -> None:
        daemon = WakeWordDaemon(app=SimpleNamespace(run_transcript=lambda _: None))

        self.assertTrue(daemon._contains_wake_word("Hey Isla, what time is it?"))
        self.assertEqual(daemon._extract_question("Hey Isla, what time is it?"), "what time is it?")
        self.assertEqual(daemon._extract_question("No wake word here"), "No wake word here")