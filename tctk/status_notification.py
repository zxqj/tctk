from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Callable, Awaitable, Coroutine, Optional

from twitchAPI.chat import ChatMessage, ChatSub, EventData
from twitchAPI.type import ChatEvent

from tctk import BotFeature, Subscription
from tctk.bot import ChannelSender, ChatBot
from tctk.message_bot import MessageBotFeature
import json

async def message_obj(obj, sender: ChannelSender):
    buffer = StringIO()
    json.dump(obj, buffer, indent=2)
    buffer.seek(0)
    await sender.send_unique(buffer.read())
FUCKING_ARE_MOD = ''.join([chr(x) for x in [120172, 120189, 120176, 32, 120184, 120186, 120175]])

ready_message = f"{FUCKING_ARE_MOD} has entered the chat HandsUp"
@dataclass
class StatusNotificationFeature(BotFeature):
    updates_message: Optional[str] = None

    def get_subscriptions(self) -> list[Subscription]:
        subs = []

        async def on_follow(sub: ChatSub, sender: ChannelSender):
            sender.send_unique("Someone subscribed to the room: ")

            message_obj(sub.room, sender)

            message_obj({
                "type": sub.sub_type,
                "plan": sub.sub_plan,
                "plan_name": sub.sub_plan_name,
                "message": sub.sub_message
            }, sender)

        async def on_ready(event_data: EventData, sender: ChannelSender):
            await sender.send_unique(ready_message)
            if self.updates_message is not None:
                await sender.send_unique(f"POLICE Bot updates! {self.updates_message} POLICE")

        subs.append((ChatEvent.READY, on_ready))
        subs.append((ChatEvent.SUB, on_follow))
        return subs

    async def on_exit(self, sender: ChannelSender):
        return await sender.send_unique(
            "Salute are_mod is going down for maintenance Salute POLICE"
        )
