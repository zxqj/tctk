from dataclasses import dataclass
import re
from typing import Awaitable, Callable

from twitchAPI.chat import ChatMessage
from functools import reduce
from tctk.bot import ChannelSender
from tctk.config import Command, Config
from tctk.message_bot import MessageBotFeature
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
            response = ""
            text = msg.text.replace("Concern", "")
            for match in CON_WORD_PATTERN.finditer(text):
                response = replace_con_words(match.group())
                response = f"bUrself {response}? bUrself LETSGOOO"
                await sender.send_unique(response)

async def are_mod(msg: ChatMessage, sender: ChannelSender):
    # ARE MOD HandsUp is an awesome mod HandsUp HE REIGNS HandsUp
    if ARE_MOD_PATTERN.search(msg.text) is not None:
        await sender.send_unique("HE REIGNS HandsUp")

async def batman(msg: ChatMessage, sender: ChannelSender):
    if "BatMan" in msg.text:
        await sender.send_unique("BatMan I'm the REAL BATMAN ReallyMad BatMan")

async def bank(msg: ChatMessage, sender: ChannelSender):
    if msg.user.name == WITHDRAW_USER:
        m = WITHDRAW_PATTERN.search(msg.text)
        if m:
            await sender.send_unique(f"{Command.give} {int(m.group('amount'))}")

async def andy_done(msg: ChatMessage, sender: ChannelSender):
    conditions = []
    conditions.append(lambda msg: "done".casefold() in msg.text)
    conditions.append(msg.user.name.casefold() == "andyreidisapawg".casefold())

    if reduce(lambda x,y: x(msg) and y(msg), conditions):
        await sender.send_unique("Sure , Andy")

decorators: list[Callable[[ChatMessage, ChannelSender], Awaitable[None]]] = [
    nut,
    are_mod,
    bank
]
@dataclass
class AutoRespFeature(MessageBotFeature):
    async def on_message(self, msg: ChatMessage, sender: ChannelSender):
        for dec in decorators:
            await dec(msg, sender)