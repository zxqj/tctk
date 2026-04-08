from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Callable, Awaitable, Coroutine, Optional

from twitchAPI.chat import ChatMessage, ChatSub, EventData
from twitchAPI.type import ChatEvent

from tctk import BotFeature, Subscription
from tctk.bot import ChannelSender, ChatBot
from tctk.features.message_bot import MessageBotFeature
import json
from tctk.alpha_format import AlphaFormatter as Fmtr, AlphaFormat as Fmt, FontVariant as Vrnt

async def message_obj(obj, sender: ChannelSender):
    buffer = StringIO()
    json.dump(obj, buffer, indent=2)
    buffer.seek(0)
    await sender.send_unique(buffer.read())

buffer = StringIO()
buffer.write("RatJamming Nothing Nothing ")
buffer.write(Vrnt.Fraktur.formatter(bold= True)("ARE MOD "))
buffer.write(Vrnt.Monospace.formatter()("has entered the chat."))
buffer.write(" Nothing Nothing RatJamming")
buffer.seek(0)

ready_message = buffer.read()
goodbye_message = f"{Vrnt.Fraktur.formatter(bold=True)("ARE MOD")} has left the building Salute"

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
            logger.variable("self.updates_message")
            if self.updates_message is not None:
                await sender.send_unique(f"POLICE {Vrnt.SansSerif.formatter(f"Bot updates: {self.updates_message}")} POLICE")

        subs.append((ChatEvent.READY, on_ready))
        subs.append((ChatEvent.SUB, on_follow))
        return subs

    async def on_exit(self, sender: ChannelSender):
        return await sender.send_unique(
            goodbye_message
        )
