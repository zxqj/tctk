import dataclasses
from dataclasses import dataclass
from typing import Callable, Awaitable, Any, Coroutine

from tctk import BotFeature, ChannelSender
from twitchAPI.chat import EventData, ChatMessage
from twitchAPI.type import ChatEvent

class MessageBotFeature(BotFeature):

    async def on_message(self, msg, sender):
        pass

    def get_subscriptions(self) -> list[tuple[Any, Callable[[ChatMessage, ChannelSender], Coroutine[Any, Any, None]]]]:
        async def f(msg: ChatMessage, sender: ChannelSender):
            await self.on_message(msg, sender)
        return [(ChatEvent.MESSAGE, f)]