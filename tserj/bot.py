from typing import Optional, Callable, Awaitable, Any

from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, ChatEvent, ChatCommand, ChatMessage
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
from .config import Config
from dataclasses import dataclass
from random import randint
import asyncio
# Define your Client ID, Client Secret, bot username, and channel name

# Define the required scopes
USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

async def get_chat(conf: Config = Config.get(), scopes: list[AuthScope] = USER_SCOPE) -> Chat:
    # Set up twitch API instance and add user authentication
    twitch = await Twitch(conf.app.id, conf.app.secret)
    auth = UserAuthenticator(twitch, scopes)
    token, refresh_token = await auth.authenticate()
    await twitch.set_user_authentication(token, USER_SCOPE, refresh_token)

    # Create chat instance
    chat = await Chat(twitch)
    return twitch, chat

class ChatBot:
    def __init__(self, channel: str):
        self.channel = channel
        self.behaviors: list[Callable[[ChatBot, ChatMessage], Awaitable[Any]]] = []
        self.chat = None

    def add_behavior(self, behavior: Callable[[ChatBot, ChatMessage], Awaitable[Any]]):
        self.behaviors.append(behavior)

    async def _delayed_send(self, channel: str, text: str, delay: float = 1.0):
        await asyncio.sleep(delay)
        if self.chat is not None:
            await self.chat.send_message(channel, text)

    async def send_message(self, text: str, delay: float = 1.0):
        await asyncio.create_task(self._delayed_send(self.channel, text, delay))

    async def on_message(self, msg: ChatMessage):
        for behavior in self.behaviors:
            await behavior(self, msg)

    # Main function to run the bot
    async def run(self):
        twitch, chat = await get_chat()
        self.chat = chat

        # Listen to chat messages (optional, if you want general message handling)
        chat.register_event(ChatEvent.MESSAGE, self.on_message)

        # Connect and join the channel
        chat.start()
        await chat.join_room(self.channel)

        print('Bot is running. Press ENTER to stop.')
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, input)
        finally:
            # Stop the bot and close the connection
            chat.stop()
            await twitch.close()