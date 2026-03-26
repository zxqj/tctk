import re
from dataclasses import dataclass
from typing import Callable, Optional, Self

from twitchAPI.chat import ChatMessage

from tctk.config import Config

def assign(ns, name):
    return lambda val: setattr(ns, name, val)
class Maybe[T]:
    def __init__(self, val: T):
        self.val = val

    def __bool__(self):
        return self.val is not None

    def into(self, fn: Callable[[T], None]) -> Self[T]:
        if self:
            fn(self.val)
        return self

    def intoprop(self, inst, p: property):
        if self:
            p.fset(inst, self.val)
        return self

    @classmethod
    def empty(cls):
        return cls(None)
@dataclass
class DuelParties:
    offerer: str
    offeree: str

    @property
    def denied_message(self) -> str:
        return f"@{self.offerer}, {self.offeree} denied your duel :("


@dataclass
class DuelOffer(DuelParties):
    amount: int = 0
    proposal_time: Optional[int] = None

    @property
    def proposal_message(self) -> str:
        return f"@{self.offeree}, @{self.offerer} wants to duel you for {self.amount} eastcoins, you can !accept or !deny within 2 minutes"

    @staticmethod
    def from_proposal(msg: ChatMessage)-> Maybe[Self]:
        if msg.user.name.casefold() == Config.get().duel_authority_user.casefold():
            m = re.match(Regex.duel_proposed, msg.text)
            if m is not None:
                d = m.groupdict()
                d['amount'] = int(d['amount'])
                d['proposal_time'] = msg.sent_timestamp
                return Maybe(DuelOffer(**d))
        return Maybe.empty()


@dataclass
class Duel(DuelOffer):
    offerer_win: Optional[bool] = None

    @property
    def complete_message(self) -> str:
        winner = self.offerer if self.offerer_win else self.offeree
        loser = self.offeree if self.offerer_win else self.offerer
        return f"{winner} won the Duel vs {loser} PogChamp {winner} won {self.amount} eastcoins FeelsGoodMan"


duel_complete = 'dookiebetts800 won the Duel vs aallldeeeez PogChamp dookiebetts800 won 348 eastcoins FeelsGoodMan'
duel_proposed = '@aallldeeeez, @dookiebetts800 wants to duel you for 348 eastcoins, you can !accept or !deny within 2 minutes'
duel_denied = '@cenozoicmegafauna, are_mod denied your duel :('

class Regex:
    uname_re = "[\\w]{3,24}"
    duel_complete = '\\@?(?P<offeree>{uname_re}) won the Duel vs \\@?(?P<offeree>{uname_re}) PogChamp dookiebetts800 won 348 eastcoins FeelsGoodMan'
    duel_proposed = f'\\@?(?P<offeree>{uname_re}), \\@?(?P<offerer>{uname_re}) wants to duel you for (?P<amount>[0-9]+) eastcoins, you can !accept or !deny within 2 minutes'
    duel_denied = f"\\@?(?P<offerer>{uname_re}), \\@(?P<offeree>{uname_re}) denied your duel :("
