from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Callable, Awaitable, Any

from tctk.bot import ChatBot, ChannelSender
from tctk import BotFeature
from twitchAPI.type import ChatEvent
from random import randint
from datetime import datetime
import re
from tctk.store import Raffle as RaffleStore, Message
from tctk.store import UserRaffle

class Raffle:
    active_raffle = None
    def __init__(self, start_time, duration, amount):
        self.start_time = start_time
        self.duration = duration
        self.amount = amount
        self.joiners: dict[str, int] = {}
        self.winners: set[str] = set()

    def persist(self):
        RaffleStore(self.start_time, self.duration, self.amount).save()
        for joiner, join_time in self.joiners.items():
            UserRaffle(joiner, self.start_time, joiner in self.winners, join_time).save()

    @staticmethod
    def close_raffle(winners: list[str]):
        Raffle.active_raffle.winners = set(winners)
        Raffle.active_raffle.persist()
        Raffle.active_raffle = None

    @staticmethod
    def open_raffle(raff: Raffle):
        Raffle.active_raffle = raff

    @staticmethod
    def is_active_raffle():
        return Raffle.active_raffle is not None

    @staticmethod
    def join_raffle(username: str, join_time: int):
        if username not in Raffle.active_raffle.joiners:
            Raffle.active_raffle.joiners[username] = join_time

class Regex:
    open = re.compile("PogChamp a Multi-Raffle has begun for (?P<amount>([0-9]+)) EastCoin PogChamp it will end in (?P<duration>([0-9]+)) Seconds.")
    uname_re = "[a-zA-Z_][\\w]{2,23}"
    close = re.compile(f"The Multi-Raffle has ended and ({uname_re}(, {uname_re})*) won ([0-9]+) EastCoin each FeelsGoodMan")

    #raffle_close_re = re.compile(raffle_close_template.format())
    #one_winner_re = re.compile(raffle_close_template.format(uname_re))
    #two_winner_re = re.compile(raffle_close_template.format(f"{uname_re} and {uname_re}"))
    #three_plus_winner_re = re.compile(raffle_close_template.format(f"({uname_re})(, ({uname_re}))*(,)? and ({uname_re})"))

class TRegex:
    extract_amount_re = re.compile("l! gunR ([0-9]+) r! gunR")
    extract_duration_re = re.compile("l! gunR ([0-9]+) r! gunR")
    raffle_open_re = extract_amount_re

    raffle_close_template = "PogChamp Frogdance {0} Dance"
    uname_re = "[\\w]{3,24}"
    one_winner_re = re.compile(raffle_close_template.format(uname_re))
    two_winner_re = re.compile(raffle_close_template.format(f"{uname_re} and {uname_re}"))
    three_plus_winner_re = re.compile(raffle_close_template.format(f"({uname_re})(, ({uname_re}))*(,)? and ({uname_re})"))
    raffle_close_re = re.compile("PogChamp Frogdance ")

# NOTE if there is an oxford comma with 3+ players in the output.
# If so, we can, starting with the below template, break it up into the
# three mutually exclusive cases of 1 winner, 2 winners and 3+winners
def extract_winners(txt: str):
    return Regex.close.search(txt).groups()[0].split(', ')

randhex = lambda d: hex(randint(0,16**d - 1)).split("x")[1].rjust(d,"0")
unique = lambda s: f"{s} {randhex(4)}"

class RaffleEvent(StrEnum):
    OPEN = auto()
    JOIN = auto()
    CLOSE = auto()

def join_predicate(msg: Message, join_command):
    is_join_re = re.compile(f'(^| ){join_command} ')
    return Raffle.is_active_raffle() and is_join_re.search(msg.text) is not None

def raffle_open_predicate(msg: Message, raffle_bot_username):
    return (msg.user_name.lower() == raffle_bot_username.lower() and
            Regex.open.match(msg.text) is not None)

def message_to_raffle(msg: Message) -> Raffle:
    raff_attrs = {"start_time": datetime.now().timestamp()*1000}
    raff_attrs.update(**{k: int(v) for k,v in Regex.open.match(msg.text).groupdict()})
    return Raffle(**raff_attrs)

def raffle_close_predicate(msg: Message, raffle_bot_username):
    return msg.user_name.lower() == raffle_bot_username.lower() and Regex.close.search(msg.text) is not None

class RaffleFeature(BotFeature):
    def __init__(self, raffle_bot_username, join_command):
        self.raffle_bot_username = raffle_bot_username
        self.join_command = join_command

    def get_subscriptions(self) -> list[tuple[ChatEvent, Callable[[Message, ChannelSender], Awaitable[Any]]]]:
        return [
            (ChatEvent.MESSAGE, self.on_message),
        ]

    async def on_message(self, msg: Message, c: ChannelSender):
        if Raffle.is_active_raffle() and raffle_close_predicate(msg, self.raffle_bot_username):
            Raffle.close_raffle(extract_winners(msg.text))
        if Raffle.is_active_raffle() and join_predicate(msg, self.join_command):
            Raffle.join_raffle(msg.user_name, round(datetime.now().timestamp()))
        if raffle_open_predicate(msg, self.raffle_bot_username):
            Raffle.open_raffle(message_to_raffle(msg))
            await c.send(unique(self.join_command), delay=1.0)