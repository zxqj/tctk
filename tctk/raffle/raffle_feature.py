from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Callable, Awaitable, Any

from tctk.bot import ChatBot, ChannelSender
from tctk import BotFeature
from twitchAPI.chat import ChatMessage, EventData
from twitchAPI.type import ChatEvent
from random import randint
from datetime import datetime
import re
from tctk.config import Command, Config
from tctk.message_bot import MessageBotFeature
from tctk.store import Raffle as RaffleStore
from tctk.store import UserRaffle
import pydash as py

def clone_without(obj, *paths):
    cloned = py.clone_deep(obj)      # deep copy, original stays unchanged
    for path in paths:
        py.unset(cloned, path)       # deep path: "user.password", "items[0].debug"
    return cloned

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

    def did_win(self, name: str):
        return name.casefold() in {x.casefold() for x in self.winners}
    
    def did_join(self, name: str):
        return name.casefold() in {x.casefold() for x in self.joiners}
    
    @staticmethod
    def close_raffle(winners: list[str]):
        Raffle.active_raffle.winners = set(winners)

    @staticmethod
    def set_active_raffle(raff: Raffle):
        Raffle.active_raffle = raff

    @staticmethod
    def is_active_raffle():
        return Raffle.active_raffle is not None

    @staticmethod
    def join_raffle(username: str, join_time: int):
        if username not in Raffle.active_raffle.joiners:
            Raffle.active_raffle.joiners[username] = join_time

class Regex:
    extract_amount_re = re.compile("a Multi-Raffle has begun for ([0-9]+) EastCoin")
    extract_duration_re = re.compile("it will end in ([0-9]+) Seconds")
    raffle_open_re = extract_amount_re
    uname_re = "[\\w]{3,24}"
    raffle_close_re = re.compile("The Multi-Raffle has ended and {0} won [0-9]+ EastCoin each FeelsGoodMan".format(uname_re))
    
    #one_winner_re = re.compile(raffle_close_template.format(uname_re))
    #two_winner_re = re.compile(raffle_close_template.format(f"{uname_re} and {uname_re}"))
    #three_plus_winner_re = re.compile(raffle_close_template.format(f"({uname_re})(, ({uname_re}))*(,)? and ({uname_re})"))
    

class PRegex:
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
    # TODO TODO WHAT GOES IN HERE also check logic below
    one_match = Regex.one_winner_re.search(txt)
    two_match = Regex.two_winner_re.search(txt)
    three_match = Regex.three_plus_winner_re.search(txt)
    if one_match is not None:
        return list(one_match.groups())
    if two_match is not None:
        return list(two_match.groups())
    if three_match is not None:
        stripped = [x.strip(",").strip(" ") for x in three_match.groups()]
        return [*filter(lambda x: x != '', stripped)]
    print(f"Could not extract winners from {txt} {datetime.now().timestamp()}")
    return None

def extract_dur_amt(txt: str):
    groups = Regex.extract_amount_re.search(txt).groups()
    amount = int(groups[0])
    groups = Regex.extract_duration_re.search(txt).groups()
    return int(groups[0]), amount

randhex = lambda d: hex(randint(0,16**d - 1)).split("x")[1].rjust(d,"0")
unique = lambda s: f"{s} {randhex(4)}"

class RaffleEvent(StrEnum):
    OPEN = auto()
    JOIN = auto()
    CLOSE = auto()

@dataclass
class RaffleEventData:
    message: ChatMessage
    raffle: Raffle

def join_predicate(msg: ChatMessage):
    is_join_re = re.compile('( |^)'+str(Command.raffle_join) + '\\b')
    return Raffle.is_active_raffle() and is_join_re.search(msg.text) is not None

def raffle_open_predicate(msg: ChatMessage, raffle_bot_username):
    return (msg.user.name.casefold() == raffle_bot_username.casefold() and
            Regex.raffle_open_re.search(msg.text) is not None)

def raffle_close_predicate(msg: ChatMessage, raffle_bot_username):
    return msg.user.name.casefold() == raffle_bot_username.casefold() and Regex.raffle_close_re.search(msg.text) is not None

class RaffleFeature(MessageBotFeature):
    def __init__(self, raffle_bot_username = Config.get().default_raffle_bot_user):
        self.raffle_bot_username = raffle_bot_username

    async def on_open(self, raffle_event_data: RaffleEventData, sender: ChannelSender):
        pass

    async def on_join(self, raffle_event_data: RaffleEventData, sender: ChannelSender):
        pass

    async def on_close(self, raffle_event_data: RaffleEventData, sender: ChannelSender):
        pass

    async def on_message(self, msg: ChatMessage, c: ChannelSender):
        print(msg.__dict__)
        if raffle_close_predicate(msg, self.raffle_bot_username):
            Raffle.close_raffle(extract_winners(msg.text))
            await self.on_close(RaffleEventData(msg, Raffle.active_raffle), c)
        elif join_predicate(msg):
            Raffle.join_raffle(msg.user.name, msg.sent_timestamp)
            await self.on_join(RaffleEventData(msg, Raffle.active_raffle), c)
        elif raffle_open_predicate(msg, self.raffle_bot_username):
            start_time = msg.sent_timestamp
            Raffle.set_active_raffle(Raffle(start_time, *extract_dur_amt(msg.text)))
            await self.on_open(RaffleEventData(msg, Raffle.active_raffle), c)