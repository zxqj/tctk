from dataclasses import dataclass
from typing import Callable

from tctk.bot import ChatBot
from twitchAPI.chat import ChatMessage
from twitchAPI.type import ChatEvent
from random import randint
from datetime import datetime
import re
from store import Raffle as RaffleStore
from store import UserRaffle

extract_amount_re = re.compile("a Multi - Raffle has begun for ([0-9]+) EastCoin")
extract_duration_re = re.compile("([0-9]+) seconds")
is_join_re = re.compile('(^| )!join ')

# TODO TODO
raffle_close_re = re.compile("TODO WHAT GOES IN HERE")

# NOTE if there is an oxford comma with 3+ players in the output.
# If so, we can, starting with the below template, break it up into the
# three mutually exclusive cases of 1 winner, 2 winners and 3+winners
def extract_winners(txt: str):
    # TODO TODO WHAT GOES IN HERE also check logic below
    template = "all of the text up until usernames start{0}text after players"
    uname_re = "[\\w]{3,24}"
    one_winner_re = re.compile(template.format(uname_re)).search(txt)
    two_winner_re = re.compile(template.replace(f"{uname_re} and {uname_re}")).search(txt)
    three_plus_winner_re = re.compile(template.replace(f"({uname_re})(, ({uname_re}))*(,)? and ({uname_re})")).search(txt)
    if one_winner_re is not None:
        return one_winner_re.groups()
    if two_winner_re is not None:
        return two_winner_re.groups()
    if three_plus_winner_re is not None:
        stripped = [x.strip(",").strip(" ") for x in three_plus_winner_re.groups()]
        return [*filter(lambda x: x != '', stripped)]

def extract_amt_dur(txt: str):
    groups = extract_amount_re.search(txt).groups()
    amount = int(groups[0])
    groups = extract_duration_re.search(txt).groups()
    return amount, int(groups[0])

randhex = lambda d: hex(randint(0,16**d - 1)).split("x")[1].rjust(d,"0")
unique = lambda s: f"{s} {randhex(4)}"

@dataclass
class TriggerResp:
    raffle_start_pred: Callable[[ChatMessage], bool]
    trigger_username: str
    response: str

class Raffle:
    active_raffle = None
    def __init__(self, start_time, duration, amount):
        self.start_time = start_time
        self.duration = duration
        self.amount = amount
        self.joiners: dict[str, int] = {}
        self.winners: set[str] = {}

    def persist(self):
        RaffleStore(self.start_time, self.duration, self.amount).save()
        for joiner, join_time in self.joiners.items():
            UserRaffle(joiner, self.start_time, joiner in self.winners, join_time).save()

    @staticmethod
    def close_raffle(winners: set[str]):
        Raffle.active_raffle.persist()
        Raffle.active_raffle.winners = winners

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

def make_raffle_tracker(context: TriggerResp):
    raffle_tracker = dict()

    def join_predicate(msg: ChatMessage):
        return Raffle.is_active_raffle() and is_join_re.search(msg.text) is not None

    async def f(c: ChatBot, msg: ChatMessage):
        if raffle_close_re.search(msg.text) is not None:
            Raffle.close_raffle(extract_winners(msg.text))
        if join_predicate(msg):
            Raffle.join_raffle(msg.user.name, round(datetime.now().timestamp()))

        predicate = context.raffle_start_pred
        if context.trigger_username is not None:
            predicate = lambda m: context.raffle_start_pred(m) and context.trigger_username.lower() == m.user.name.lower()
        if predicate(msg):
            start_time = datetime.now().timestamp()
            Raffle.set_active_raffle(Raffle(start_time, *extract_amt_dur(msg.text)))
            await c.send_message(unique(context.response))

    raffle_tracker[ChatEvent.MESSAGE] = f
    return raffle_tracker