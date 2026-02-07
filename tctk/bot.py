from enum import Enum
from typing import Callable, Awaitable, Any, TypeVar, Optional

from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, ChatEvent, ChatCommand, ChatMessage, EventData
from twitchAPI.oauth import UserAuthenticator
from .config import Config
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

class ChatBot(EventEmitter[ChatEvent, EventData]):
    def __init__(self, channel: str):
        self.channel = channel
        self.chat = None

    def subscribe(self, t: ChatEvent, cb: Callable[[EventData, ChannelSender], Awaitable[Any]]) -> None:
        async def handler(*args):
            arg_list = list(args)
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