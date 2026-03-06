from enum import Enum
from typing import Callable, Awaitable, Any, TypeVar, Optional

from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, ChatEvent, ChatCommand, ChatMessage, EventData
from twitchAPI.oauth import UserAuthenticator
from .config import Config
from .store import Message as StoreMessage
import asyncio

U = TypeVar('U', bound=Enum)

# Define the required scopes
async def get_chat(conf: Config = Config.get()) -> Chat:
    # Set up twitch API instance and add user authentication
    twitch = await Twitch(conf.app.id, conf.app.secret)
    auth = UserAuthenticator(twitch, conf.oauth_tokens.scopes)
    token, refresh_token = await auth.authenticate()
    def update_tokens(c: Config):
        c.oauth_tokens.access = token
        c.oauth_tokens.refresh = refresh_token
    Config.persist_with(update_tokens)
    await twitch.set_user_authentication(token, conf.oauth_tokens.scopes, refresh_token)

    # Create chat instance
    chat = await Chat(twitch)
    return twitch, chat

class ChannelSender(Chat):
    def __init__(self, chat: Chat, channel: str):
        self._chat = chat
        self.channel = channel

    def __getattr__(self, name: str) -> Any:
        # forward any unknown attribute/method access to the wrapped Chat
        return getattr(self._chat, name)

    async def _delayed_send(self, text: str, delay: float = None):
        if delay is not None:
            await asyncio.sleep(delay)
        if self._chat is not None:
            await self._chat.send_message(self.channel, text)

    async def send_message(self, text: str, delay: float = None):
        await asyncio.create_task(self._delayed_send(text, delay))

    async def send(self, text: str, delay: Optional[float] = None):
        await self.send_message(text, delay)

# Define your Client ID, Client Secret, bot username, and channel name
class EventEmitter[U, T]:
    def subscribe(self, evt_type: U, callback: Callable[[T, ChannelSender], Awaitable[Any]]):
        pass

class EventSubBot:
    def __init__(self, chat: Chat, channel: str):
        self.channel = channel

    async def init(self):
        self.twitch = await Twitch(Config.app.id, Config.app.secret)
        UserAuthenticator

class ChatBot(EventEmitter[ChatEvent, EventData]):
    def __init__(self, channel: str):
        self.channel = channel
        self.chat = None

    def subscribe(self, t: ChatEvent, cb: Callable[[EventData, ChannelSender], Awaitable[Any]]) -> None:
        async def handler(*args):
            arg_list = list(args)
            # If this is a message event, convert ChatMessage to StoreMessage
            if t == ChatEvent.MESSAGE and arg_list and isinstance(arg_list[0], ChatMessage):
                arg_list[0] = chat_message_to_store(arg_list[0])
            arg_list.append(ChannelSender(self.chat, self.channel))

            await cb(*arg_list)
        self.chat.register_event(t, handler)

    # Main function to run the bot
    async def init(self):
        twitch, chat = await get_chat()
        self.chat = chat
        self.twitch = twitch

        # Connect and join the channel
        chat.start()
        await chat.join_room(self.channel)

    async def run(self):
        print('Bot is running. Press ENTER to stop.')
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, input)
        finally:
            # Stop the bot and close the connection
            self.chat.stop()
            await self.twitch.close()


def chat_message_to_store(cm: ChatMessage) -> StoreMessage:
    parsed = getattr(cm, "_parsed", {}) or {}
    tags = parsed.get("tags", {}) or {}
    source = parsed.get("source", {}) or {}
    command = parsed.get("command", {}) or {}

    def _bool(v):
        if v in ("0", "1"):
            return v == "1"
        return bool(v)

    def _int(v):
        try:
            return int(v)
        except Exception:
            return 0

    badges = []
    if tags.get("badges"):
        try:
            # badges are often in format: "moderator/1,subscriber/12"
            parts = str(tags["badges"]).split(",")
            badges = [p.split("/")[0] for p in parts if p]
        except Exception:
            pass

    emotes = None
    if getattr(cm, "emotes", None):
        try:
            emotes = []
            for e in cm.emotes:
                # shape: {id, ranges:[{start,end}]}
                emotes.append({"id": int(e.get("id", 0)), "ranges": [{"start": int(r[0]), "end": int(r[1])} for r in e.get("range", [])]})
        except Exception:
            emotes = None

    return StoreMessage(
        user_id=_int(tags.get("user-id")),
        user_name=cm.user.name,
        is_me=getattr(cm, "is_me", False),
        badges=list(dict.fromkeys(badges)),
        color=tags.get("color"),
        first_msg=_bool(tags.get("first-msg", False)),
        mod=_bool(tags.get("mod", False)),
        first=getattr(cm, "first", False),
        subscriber=_bool(tags.get("subscriber", False)),
        room_id=_int(tags.get("room-id")),
        channel=str(command.get("channel", "")).lstrip("#") if command.get("channel") else getattr(cm, "channel", ""),
        id=getattr(cm, "id", tags.get("id", "")),
        text=cm.text,
        sent_timestamp=_int(getattr(cm, "sent_timestamp", tags.get("tmi-sent-ts", 0))),
        reply_parent_id=getattr(cm, "reply_parent_msg_id", None),
        bits=int(getattr(cm, "bits", 0)),
        emotes=emotes,
        hype_chat=getattr(cm, "hype_chat", None),
        source_id=_int(getattr(cm, "source_id", tags.get("user-id", 0))),
    )


def activities_to_messages(activity: list[tuple[str, float, dict]]) -> list[StoreMessage]:
    messages: list[StoreMessage] = []
    for etype, ts, payload in activity:
        if str(etype).lower() == "message" and isinstance(payload, dict):
            # reconstruct minimal ChatMessage-like object for converter
            cm = type("_CM", (), {})()
            setattr(cm, "_parsed", payload.get("_parsed", {}))
            setattr(cm, "text", payload.get("text", ""))
            setattr(cm, "is_me", bool(payload.get("is_me", False)))
            setattr(cm, "bits", int(payload.get("bits", 0)))
            setattr(cm, "first", bool(payload.get("first", False)))
            setattr(cm, "sent_timestamp", int(payload.get("sent_timestamp", ts)))
            setattr(cm, "reply_parent_msg_id", payload.get("reply_parent_msg_id", None))
            setattr(cm, "emotes", payload.get("emotes", None))
            setattr(cm, "id", payload.get("id", ""))
            setattr(cm, "hype_chat", payload.get("hype_chat", None))
            setattr(cm, "source_id", payload.get("source_id", None))
            msg = chat_message_to_store(cm)  # type: ignore[arg-type]
            messages.append(msg)
    return messages
