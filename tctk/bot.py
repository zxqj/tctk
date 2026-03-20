from enum import Enum, StrEnum, auto
from pathlib import Path
from typing import Callable, Awaitable, Any, TypeVar, Optional

from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, ChatEvent, ChatCommand, ChatMessage, EventData
from twitchAPI.oauth import UserAuthenticationStorageHelper, UserAuthenticator
from twitchAPI.type import AuthScope
from .config import Config
import asyncio
import emoji
from secrets import choice

U = TypeVar('U', bound=Enum)

def rand_emoji():
    return choice([*emoji.EMOJI_DATA.keys()])

async def show_user_auth_url(url: str):
    print(f"navigate to {url} to authorize twitch")

# Define the required scopes
async def get_chat(conf: Config = Config.get()) -> Chat:
    # Set up twitch API instance and add user authentication
    twitch = await Twitch(conf.app.id, conf.app.secret)

    async def get_tokens(t: Twitch, scopes: list[AuthScope]):
        auth = UserAuthenticator(twitch, scopes)
        token, refresh_token = await auth.authenticate(use_browser=False, auth_url_callback=show_user_auth_url)
        return (token, refresh_token)

    storage_helper = UserAuthenticationStorageHelper(
        twitch,
        storage_path=Path("twitch_auth.txt"),
        scopes=conf.scopes,
        auth_generator_func=get_tokens
    )
    await storage_helper.bind()
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

    async def send_unique(self, text: str, delay: float = None):
        await asyncio.create_task(self._delayed_send(f"{text} {rand_emoji()}", delay))

    async def send(self, text: str, delay: Optional[float] = None):
        await self.send_message(text, delay)

# Define your Client ID, Client Secret, bot username, and channel name
class EventEmitter[U, T]:
    def subscribe(self, evt_type: U, callback: Callable[[T, ChannelSender], Awaitable[Any]]):
        pass

class ChatBot(EventEmitter[ChatEvent, EventData]):
    def __init__(self, channel: str):
        self.channel = channel
        self.chat = None

    @classmethod
    async def create(cls, channel, subscriptions: list[tuple] = None):
        self = cls(channel)
        await self.init(subscriptions or [])
        print(hasattr(self, "sender"))
        return self

    def subscribe(self, t: ChatEvent, cb: Callable[[EventData, ChannelSender], Awaitable[Any]]) -> None:
        async def handler(*args):
            arg_list = list(args)
            arg_list.append(ChannelSender(self.chat, self.channel))
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