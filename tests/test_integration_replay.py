# python
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple, TypeAlias, TypeVar

import pytest
from asyncclick.testing import CliRunner

# Under test
from tctk.cli import cli as main_cli

# Event classes from twitchAPI.chat
from twitchAPI.chat import (
    ChatMessage,
    JoinEvent,
    JoinedEvent,
    LeftEvent,
    RoomStateChangeEvent,
    MessageDeletedEvent,
    ChatSub,
    EventData,
)
from twitchAPI.type import ChatEvent, ChatRoom

# Utilities to build chat event payload objects
def _mk_event_object(event_type: ChatEvent, payload: Dict[str, Any], username: str, channel: str):
    # Minimal parsed dict shim to satisfy constructors
    # These classes expect "parsed" from IRC. We simulate the necessary fields.
    base_parsed = {
        "command": {"channel": f"#{channel}"},
        "source": {"nick": username},
        "tags": {},
        "parameters": "",
    }

    # Merge payload into base, letting payload override if provided
    parsed = dict(**base_parsed, **payload)
    if event_type == ChatEvent.MESSAGE:
        # Expected keys: parsed['command']['bot_command'] optional, parsed['tags'], text, user
        # ChatMessage(self, parsed) reads text via parsed['parameters'] or similar; we set text directly
        # Provide a simple user stub compatible with ChatMessage expectations
        class _User:
            def __init__(self, name): self.name = name
        # ChatMessage accepts parsed and constructs properties; if your version needs exact 'text',
        # set both 'parameters' and 'text' to be safe.
        parsed.setdefault("parameters", payload.get("text", ""))
        msg = ChatMessage(None, parsed)
        # Patch attributes commonly accessed in features
        msg.text = payload.get("text", "")
        msg.user = _User(username)
        return msg

    if event_type == ChatEvent.JOIN:
        return JoinEvent(None, channel, username)

    if event_type == ChatEvent.JOINED:
        return JoinedEvent(None, channel, username)

    if event_type in (ChatEvent.LEFT, ChatEvent.USER_LEFT):
        room = ChatRoom(
            name=channel,
            is_emote_only=False,
            is_subs_only=False,
            is_followers_only=False,
            is_unique_only=False,
            follower_only_delay=-1,
            room_id="0",
            slow=0,
        )
        return LeftEvent(None, channel, room, username)

    if event_type == ChatEvent.ROOM_STATE_CHANGE:
        # Minimal previous/current states
        prev = ChatRoom(
            name=channel,
            is_emote_only=False,
            is_subs_only=False,
            is_followers_only=False,
            is_unique_only=False,
            follower_only_delay=-1,
            room_id="0",
            slow=0,
        )
        curr = ChatRoom(
            name=channel,
            is_emote_only=payload.get("is_emote_only", False),
            is_subs_only=payload.get("is_subs_only", False),
            is_followers_only=payload.get("is_followers_only", False),
            is_unique_only=payload.get("is_unique_only", False),
            follower_only_delay=payload.get("follower_only_delay", -1),
            room_id=payload.get("room_id", "0"),
            slow=payload.get("slow", 0),
        )
        return RoomStateChangeEvent(None, prev, curr)

    if event_type == ChatEvent.MESSAGE_DELETE:
        return MessageDeletedEvent(None, parsed)

    if event_type == ChatEvent.SUB:
        return ChatSub(None, parsed)

    if event_type == ChatEvent.READY:
        return EventData(None)

    # Fallback: treat unknowns as NOTICE/WHISPER if needed; use EventData
    return EventData(None)


def _event_handlers_for(chat, event_type: ChatEvent):
    # Access registered handlers from chat internals
    return chat._event_handler.get(event_type, [])


async def _replay_events(chat, events: List[Tuple[str, float, Dict[str, Any]]], username: str, channel: str):
    # Ensure READY is emitted first if handlers exist
    ready_handlers = _event_handlers_for(chat, ChatEvent.READY)
    if ready_handlers:
        ev = _mk_event_object(ChatEvent.READY, {}, username, channel)
        await asyncio.gather(*(h(ev) for h in ready_handlers))

    # Replay event stream in order
    for etype_str, _ts, payload in events:
        try:
            etype = ChatEvent(etype_str)
        except ValueError:
            continue
        obj = _mk_event_object(etype, payload or {}, username, channel)
        handlers = _event_handlers_for(chat, etype)
        if not handlers:
            continue
        # Dispatch all handlers asynchronously
        await asyncio.gather(*(h(obj) for h in handlers))

from box import Box

def _load_log(path: str) -> List[Tuple[str, float, Dict[str, Any]]]:
    data = json.loads(Path(path).read_text())
    # Each entry: [event_type, datetime_timestamp, serialized_event_object]
    return Box({
        "start_time": round(data.get("start_time")*1000),
        "end_time": round(data.get("end_time")*1000),
        "activity": [(e[0], round(e[1]), Box(json.loads(e[2])) or {}) for e in data.get("activity", [])]
    })

def _save_log(l: Box, new_path: Path):
    if new_path.exists():
        raise ValueError("FAIL")
    with new_path.open("w") as f:
        json.dump(l, f, indent=2)

T = TypeVar("T", bound=EventData)
def _load_events[T](path:str = "activity_latest.json", username="are_mod", channel="thestreameast") -> List[T]:

    log = _load_log(path)
    events = log.activity
    l = []
    for etype_str, _ts, payload in events:
        try:
            etype = ChatEvent(etype_str)
        except ValueError:
            continue
        class _User:
            def __init__(self, name): self.name = name
        payload.user = _User(username)
        payload.user_name = username
        l.append(payload)
    return l

def _filter_window(events, start_ts: float, duration_sec: float):
    end_ts = start_ts + duration_sec
    return [e for e in events if e[1] >= start_ts and e[1] <= end_ts]


@pytest.mark.asyncio
async def test_integration_replay(tmp_path):

    if os.environ.get("APP_ENV") != "test":
        raise RuntimeError("APP_ENV must be set to 'test'")

    # Configuration
    timestamp_start = time.time() - 3600  # start one hour ago
    duration = 120.0  # seconds
    json_path = tmp_path / "activity.json"
    username = "test_user"
    channel = "test_channel"
    features = ["raffle_tracker", "activity_log"]  # adjust to your available features

    # Example activity file content; replace with your fixture file as needed
    sample = {
        "activity": [
            ["ready", timestamp_start, {}],
            ["joined", timestamp_start + 1, {}],
            ["message", timestamp_start + 2, {"text": "Hello world"}],
            ["room_state_change", timestamp_start + 3, {"is_emote_only": True}],
            ["message_delete", timestamp_start + 4, {"parameters": "123"}],
            ["sub", timestamp_start + 5, {"tags": {"msg-id": "sub"}}],
            ["left", timestamp_start + 6, {}],
        ]
    }
    json_path.write_text(json.dumps(sample))

    # Prepare events
    all_events = _load_log(str(json_path))
    windowed = _filter_window(all_events, timestamp_start, duration)
    # Replay order: ascending timestamp
    windowed.sort(key=lambda x: x[1])

    # Run CLI with channel and features
    runner = CliRunner()

    # We patch ChatBot.run to prevent real network ops and expose bot.chat
    # The CLI constructs ChatBot(channel=channel), bot.init(), subscribes features, then bot.run()
    # We intercept bot.run by monkeypatching the ChatBot class inside tctk.cli via environment
    # Use a small wrapper to capture the chat instance and replay
    captured = {"chat": None}

    # Monkeypatch by replacing ChatBot.run at runtime
    # Import here to reach the same class instance used by CLI
    import tctk.bot as bot_module

    original_run = bot_module.ChatBot.run

    async def fake_run(self):
        # Capture chat object
        captured["chat"] = self.chat
        # Simulate ready state
        await _replay_events(self.chat, windowed, username, channel)

    bot_module.ChatBot.run = fake_run

    try:
        # Invoke CLI: `cli --channel <channel> <features...>`
        result = await runner.invoke(main_cli, ["--channel", channel, *features], catch_exceptions=False)
        assert result.exit_code == 0
        assert captured["chat"] is not None
    finally:
        # Restore original run
        bot_module.ChatBot.run = original_run
