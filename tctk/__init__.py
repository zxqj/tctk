from typing import Callable, Awaitable, Any

from tctk.bot import ChannelSender, ChatBot
from twitchAPI.chat import EventData
from twitchAPI.type import ChatEvent

type Subscription = tuple[ChatEvent, Callable[[EventData, ChannelSender], Awaitable[Any]]]


class BotFeature:
    # Names (as registered in feature_registry) of features this one depends on.
    requires: list[str] = []

    def on_start(self):
        pass

    def get_subscriptions(self) -> list[Subscription]:
        return []

    def on_exit(self, bot: ChatBot):
        pass
