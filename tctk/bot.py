from enum import Enum, StrEnum, auto
import logging
from pathlib import Path
from typing import Callable, Awaitable, Any, TypeVar, Optional
import time

from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, ChatEvent, ChatCommand, ChatMessage, EventData
from twitchAPI.oauth import UserAuthenticationStorageHelper, UserAuthenticator
from twitchAPI.type import AuthScope
from .config import App, Config
import asyncio
import emoji
from secrets import choice

U = TypeVar('U', bound=Enum)

def rand_emoji():
    return choice([*emoji.EMOJI_DATA.keys()])

async def show_user_auth_url(url: str):
    print(f"navigate to {url} to authorize twitch")

# Define the required scopes
async def get_chat(access_tokens_file: str = Config.get().bot_access_tokens_file, app: App = Config.get().app, scopes: list[AuthScope] = Config.get().scopes) -> tuple[Twitch, Chat]:
    # Set up twitch API instance and add user authentication
    twitch = await Twitch(app.id, app.secret)

    async def get_tokens(t: Twitch, scopes: list[AuthScope]):
        auth = UserAuthenticator(twitch, scopes)
        token, refresh_token = await auth.authenticate(use_browser=False, auth_url_callback=show_user_auth_url)
        return (token, refresh_token)

    storage_helper = UserAuthenticationStorageHelper(
        twitch,
        storage_path=Path(access_tokens_file),
        scopes=scopes,
        auth_generator_func=get_tokens
    )
    await storage_helper.bind()
    # Create chat instance
    chat = await Chat(twitch)
    return twitch, chat

logger = Config.logger(__name__)

class ChannelSender(Chat):
    def __init__(self, chat: Chat, channel: str):
        self.chat = chat
        self.channel = channel
        self._last_send_time: float = 0.0
        self._slow_lock = asyncio.Lock()

    @property
    def room(self):
        return None if self.channel not in self.chat.room_cache else self.chat.room_cache[self.channel]

    def __getattr__(self, name: str) -> Any:
        # forward any unknown attribute/method access to the wrapped Chat
        return getattr(self.chat, name)

    def _get_slow_delay(self) -> int:
        return self.room.slow if self.room else 0

    async def _wait_for_slow_mode(self):
        slow = self._get_slow_delay()
        logger.debug(f"slow: {slow}")
        if slow > 0:
            elapsed = time.monotonic() - self._last_send_time
            logger.variable(elapsed)
            if elapsed < slow:
                await asyncio.sleep(slow - elapsed)

    async def _delayed_send(self, text: str, delay: float = None):
        if delay is not None:
            await asyncio.sleep(delay)
        if self.chat is not None:
            async with self._slow_lock:
                await self._wait_for_slow_mode()
                await self.chat.send_message(self.channel, text)
                self._last_send_time = time.monotonic()

    async def send_message(self, text: str, delay: float = None):
        await asyncio.create_task(self._delayed_send(text, delay))

    async def send_unique(self, text: str, delay: float = None):
        await asyncio.create_task(self._delayed_send(f"{text} {rand_emoji()}", delay))

    async def send(self, text: str, delay: Optional[float] = None):
        await self.send_message(text, delay)

    async def send_result(self, gen_msg: Callable[[], str]) -> None:
        """Wait for slow mode, then send only if guard() still holds."""
        time_since_last_send_time = time.monotonic() - self._last_send_time
        logger.variable(time_since_last_send_time)
        logger.variable(self._slow_lock)
        async with self._slow_lock:
            logger.debug("in lock")
            await self._wait_for_slow_mode()
            msg = gen_msg()
            logger.variable(msg)
            await self.chat.send_message(self.channel, f'{msg} {rand_emoji()}')
            self._last_send_time = time.monotonic()

    async def send_guarded(self, text: str, guard: Callable[[], bool]) -> bool:
        """Wait for slow mode, then send only if guard() still holds."""
        async with self._slow_lock:
            await self._wait_for_slow_mode()
            if not guard():
                return False
            await self.chat.send_message(self.channel, text)
            self._last_send_time = time.monotonic()
            return True

# Define your Client ID, Client Secret, bot username, and channel name
class EventEmitter[U, T]:
    def subscribe(self, evt_type: U, callback: Callable[[T, ChannelSender], Awaitable[Any]]):
        pass

class ChatBot(EventEmitter[ChatEvent, EventData]):
    def __init__(self, channel: str, access_tokens_file: Path):
        self.channel = channel
        self.access_tokens_file = access_tokens_file
        self.chat = None
        self.sender = None

    @classmethod
    async def create(cls, channel, access_tokens_file: str = Config.get().bot_access_tokens_file, subscriptions: list[tuple] = None):
        self = cls(channel, access_tokens_file)
        await self.init(subscriptions or [])
        return self

    def subscribe(self, t: ChatEvent, cb: Callable[[EventData, ChannelSender], Awaitable[Any]]) -> None:
        async def handler(*args):
            arg_list = list(args)
            if not self.sender:
                self.sender = ChannelSender(self.chat, self.channel)
            arg_list.append(self.sender)
            await cb(*arg_list)
        self.chat.register_event(t, handler)

    # Main function to run the bot
    async def init(self, subscriptions: list[tuple] = None):
        twitch, chat = await get_chat()
        self.chat = chat
        self.twitch = twitch

        for event_type, handler in (subscriptions or []):
            self.subscribe(event_type, handler)

        # Connect and join the channel
        chat.start()

        self.sender = ChannelSender(self.chat, self.channel)
        await chat.join_room(self.channel)

    async def run(self, before_stop: list[Callable[[], Awaitable[Any]]] | None = None):
        print('Bot is running. Press ENTER to stop.')
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, input)
        finally:
            for cb in (before_stop or []):
                await cb()
            # Stop the bot and close the connection
            self.chat.stop()
            await self.twitch.close()