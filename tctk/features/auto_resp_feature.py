from dataclasses import dataclass
import re
from typing import Awaitable, Callable

from twitchAPI.chat import ChatMessage
from functools import reduce
from tctk.bot import ChannelSender
from tctk.config import Command, Config
from tctk.features.message_bot import MessageBotFeature
from functools import reduce

WITHDRAW_PATTERN = re.compile(f"\b{Command.withdraw}\b(?P<amount>[0-9]+)")
CON_WORD_PATTERN = re.compile(r"\bcon\w*", re.IGNORECASE)
CON_BEG_PATTERN = re.compile(r"\bcon", re.IGNORECASE)
ARE_MOD_PATTERN = re.compile("are mod|our mod", re.IGNORECASE)

WITHDRAW_USER = "cenozoicmegafauna"

def replace_con_words(text: str) -> str:
    return CON_BEG_PATTERN.sub("Kon ... ", text)

async def nut(msg: ChatMessage, sender: ChannelSender):
    # Nut button 'functionality'
    if "nutButton" in msg.text:
        await sender.send_unique("gachiHYPER l! uwotWater")

async def kon(msg: ChatMessage, sender: ChannelSender):
    # Go Hornets
    if CON_WORD_PATTERN.search(msg.text) is not None:
        if reduce(lambda a, b: a or b, [bw in msg.text.lower() for bw in Config.get().auto_timeout_words]):
            await sender.send_unique("Fricc")
        else:
            text = msg.text.replace("Concern", "")
            match = CON_WORD_PATTERN.search(text)
            if match is not None:
                response = replace_con_words(match.group())
                response = f"bUrself {response} ? bUrself LETSGOOO"
                await sender.send_unique(response)

async def are_mod(msg: ChatMessage, sender: ChannelSender):
    # ARE MOD HandsUp is an awesome mod HandsUp HE REIGNS HandsUp
    if ARE_MOD_PATTERN.search(msg.text) is not None:
        await sender.send_unique("HE REIGNS HandsUp")

async def batman(msg: ChatMessage, sender: ChannelSender):
    if "BatMan" in msg.text:
        await sender.send_unique("BatMan I'm the REAL BATMAN ReallyMad BatMan")

decorators: list[Callable[[ChatMessage, ChannelSender], Awaitable[None]]] = [
    nut,
    are_mod,
    kon
]
@dataclass
class AutoRespFeature(MessageBotFeature):
    async def on_message(self, msg: ChatMessage, sender: ChannelSender):
        for dec in decorators:
            await dec(msg, sender)
