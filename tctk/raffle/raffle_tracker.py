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
from tctk.store import Raffle as RaffleStore
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
        Raffle.active_raffle.persist()
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

    raffle_close_template = "all of the text up until usernames start{0}text after players"
    uname_re = "[\\w]{3,24}"
    one_winner_re = re.compile(raffle_close_template.format(uname_re))
    two_winner_re = re.compile(raffle_close_template.format(f"{uname_re} and {uname_re}"))
    three_plus_winner_re = re.compile(raffle_close_template.format(f"({uname_re})(, ({uname_re}))*(,)? and ({uname_re})"))
    raffle_close_re = "all of the text until usernames start"

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

def extract_amt_dur(txt: str):
    groups = Regex.extract_amount_re.search(txt).groups()
    amount = int(groups[0])
    groups = Regex.extract_duration_re.search(txt).groups()
    return amount, int(groups[0])

randhex = lambda d: hex(randint(0,16**d - 1)).split("x")[1].rjust(d,"0")
unique = lambda s: f"{s} {randhex(4)}"

class RaffleEvent(StrEnum):
    OPEN = auto()
    JOIN = auto()
    CLOSE = auto()

def join_predicate(msg: ChatMessage, join_command):
    is_join_re = re.compile(f'(^| ){join_command} ')
    return Raffle.is_active_raffle() and is_join_re.search(msg.text) is not None

def raffle_open_predicate(msg: ChatMessage, raffle_bot_username):
    return (msg.user.name.lower() == raffle_bot_username.lower() and
            Regex.raffle_open_re.match(msg.text) is not None)

def raffle_close_predicate(msg: ChatMessage, raffle_bot_username):
    return msg.user.name.lower() == raffle_bot_username.lower() and Regex.raffle_close_re.search(msg.text) is not None

class RaffleFeature(BotFeature):
    def __init__(self, raffle_bot_username, join_command):
        self.raffle_bot_username = raffle_bot_username
        self.join_command = join_command

    def get_subscriptions(self) -> list[tuple[ChatEvent, Callable[[EventData, ChannelSender], Awaitable[Any]]]]:
        return [
            (ChatEvent.MESSAGE, self.on_message),
        ]

    async def on_message(self, msg: ChatMessage, c: ChannelSender):
        if raffle_close_predicate(msg, self.raffle_bot_username):
            Raffle.close_raffle(extract_winners(msg.text))
        if join_predicate(msg, self.join_command):
            Raffle.join_raffle(msg.user.name, round(datetime.now().timestamp()))
        if raffle_open_predicate(msg, self.raffle_bot_username):
            start_time = datetime.now().timestamp()
            Raffle.set_active_raffle(Raffle(start_time, *extract_amt_dur(msg.text)))
            await c.send(unique(self.join_command), delay=1.0)