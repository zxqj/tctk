from typing import Callable, Awaitable, Any

from tctk.bot import ChannelSender
from twitchAPI.chat import EventData
from twitchAPI.type import ChatEvent


class BotFeature:
    def on_start(self):
        pass

    def get_subscriptions(self) -> list[tuple[ChatEvent, Callable[[EventData, ChannelSender], Awaitable[Any]]]]:
        pass

    def on_exit(self):
        pass
