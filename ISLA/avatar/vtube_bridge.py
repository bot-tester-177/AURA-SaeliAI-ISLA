"""VTube Studio WebSocket bridge — sends emotion/expression triggers to VTS."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# VTube Studio default WebSocket address
VTS_HOST = os.getenv("ISLA_VTS_HOST", "ws://localhost:8001")

# Map Isla emotion names → VTube Studio hotkey names (set these in VTS to match)
EMOTION_TO_HOTKEY: dict[str, str] = {
    "neutral":   "isla_neutral",
    "happy":     "isla_happy",
    "sad":       "isla_sad",
    "surprised": "isla_surprised",
    "thinking":  "isla_thinking",
}

_PLUGIN_NAME = "IslaAI"
_PLUGIN_DEVELOPER = "SaeliAI"


def _make_request(msg_type: str, data: dict[str, Any]) -> str:
    return json.dumps({
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": uuid.uuid4().hex,
        "messageType": msg_type,
        "data": data,
    })


async def _authenticate(ws: Any, token: str | None) -> str | None:
    """Authenticate with VTS. Returns auth token on success, None on failure."""
    if token:
        req = _make_request("AuthenticationRequest", {
            "pluginName": _PLUGIN_NAME,
            "pluginDeveloper": _PLUGIN_DEVELOPER,
            "authenticationToken": token,
        })
        await ws.send(req)
        resp = json.loads(await ws.recv())
        if resp.get("data", {}).get("authenticated"):
            return token

    # Request a new token (user must click Allow in VTS)
    req = _make_request("AuthenticationTokenRequest", {
        "pluginName": _PLUGIN_NAME,
        "pluginDeveloper": _PLUGIN_DEVELOPER,
        "pluginIcon": None,
    })
    await ws.send(req)
    resp = json.loads(await ws.recv())
    new_token = resp.get("data", {}).get("authenticationToken")
    if not new_token:
        return None

    # Authenticate with the new token
    req = _make_request("AuthenticationRequest", {
        "pluginName": _PLUGIN_NAME,
        "pluginDeveloper": _PLUGIN_DEVELOPER,
        "authenticationToken": new_token,
    })
    await ws.send(req)
    resp = json.loads(await ws.recv())
    return new_token if resp.get("data", {}).get("authenticated") else None


async def _trigger_hotkey(ws: Any, hotkey_name: str) -> None:
    req = _make_request("HotkeyTriggerRequest", {"hotkeyID": hotkey_name})
    await ws.send(req)
    await ws.recv()  # consume response


async def send_emotion_async(emotion: str, token: str | None = None) -> str | None:
    """
    Connect to VTube Studio, authenticate, fire the hotkey for `emotion`.
    Returns the auth token so callers can cache it for the session.
    """
    try:
        import websockets  # type: ignore
    except ImportError:
        logger.warning("websockets not installed — VTube Studio bridge disabled.")
        return token

    hotkey = EMOTION_TO_HOTKEY.get(emotion, EMOTION_TO_HOTKEY["neutral"])

    try:
        async with websockets.connect(VTS_HOST) as ws:
            token = await _authenticate(ws, token)
            if token is None:
                logger.warning("VTS authentication failed.")
                return None
            await _trigger_hotkey(ws, hotkey)
            logger.debug("VTS: triggered %r for emotion %r", hotkey, emotion)
    except OSError:
        logger.debug("VTube Studio not running — skipping expression update.")

    return token


class VTubeBridge:
    """
    Synchronous wrapper around the async VTS client.
    Keeps the auth token alive for the session.

    Usage:
        bridge = VTubeBridge()
        bridge.send_emotion("happy")
    """

    def __init__(self) -> None:
        self._token: str | None = None

    def send_emotion(self, emotion: str) -> None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already inside an event loop (e.g. voice_loop) — schedule as task
                loop.create_task(self._update_token(emotion))
            else:
                self._token = loop.run_until_complete(
                    send_emotion_async(emotion, self._token)
                )
        except Exception as exc:
            logger.debug("VTubeBridge.send_emotion error: %s", exc)

    async def _update_token(self, emotion: str) -> None:
        self._token = await send_emotion_async(emotion, self._token)
