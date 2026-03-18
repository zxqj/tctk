import re
from dataclasses import dataclass
from typing import Optional

from twitchAPI.chat import ChatMessage


@dataclass
class Duel:
    duel_offer_recipient: str
    duel_offerer: str
    amount: int
    proposal_time: int
    duel_offerer_win: Optional[bool] = None

    @staticmethod
    def from_proposal(msg: ChatMessage):
        m = re.match(Regex.duel_proposed, msg.text)
        if m is not None:
            d = m.groupdict()
            d['amount'] = int(d['amount'])
            d['proposal_time'] = msg.sent_timestamp
            return Duel(**d)
        else:
            return None


duel_complete = 'dookiebetts800 won the Duel vs aallldeeeez PogChamp dookiebetts800 won 348 eastcoins FeelsGoodMan'
duel_proposed = '@aallldeeeez, @dookiebetts800 wants to duel you for 348 eastcoins, you can !accept or !deny within 2 minutes'
duel_denied = '@cenozoicmegafauna, are_mod denied your duel :('

class Regex:
    uname_re = "[\\w]{3,24}"
    duel_complete = '\\@?(?P<duel_offer_recipient>{uname_re}) won the Duel vs \\@?(?P<duel_offer_recipient>{uname_re}) PogChamp dookiebetts800 won 348 eastcoins FeelsGoodMan'
    duel_proposed = f'\\@?(?P<duel_offer_recipient>{uname_re}), \\@?(?P<duel_offerer>{uname_re}) wants to duel you for (?P<amount>[0-9]+) eastcoins, you can !accept or !deny within 2 minutes'
    duel_denied = f"\\@?(?P<duel_offerer>{uname_re}), \\@(?P<duel_offer_recipient>{uname_re}) denied your duel :("
