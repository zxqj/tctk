import dataclasses
from dataclasses import field
import logging
import time
from typing import Callable, Self
from tctk import ChannelSender
from tctk.bot import rand_emoji
from tctk.duel import DuelOffer, assign
from tctk.message_bot import MessageBotFeature
from twitchAPI.chat import ChatMessage
from .config import Command, Config

history = dict()
logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DuelBotFeature(MessageBotFeature):
    _mrp: DuelOffer | None = field(default=None, init=False, repr=False)

    @property
    def most_recent_proposal(self):
        return self._mrp

    @most_recent_proposal.setter
    def most_recent_proposal(self, val):
        logger.debug(val)
        self._mrp = val

    async def on_message(self, msg: ChatMessage, sender: ChannelSender):

        if DuelOffer.from_proposal(msg).intoprop(self, DuelBotFeature.most_recent_proposal):
            if self._mrp.offeree.casefold() == msg.chat.username.casefold():
                duel_max = Config.get().max_duel_amt
                no = Command.deny(f"Fricc The maximum duel amount is {duel_max} coins.")
                yes = Command.accept()
                logger.variable(self._mrp.offerer)
                await sender.send_result(lambda: no if self._mrp.amount > duel_max else yes)

                el_former = """
                if duel.amount > Config.get().max_duel_amt:
                    await sender.send_guarded(
                        f"!deny Fricc The maximum duel amount is {Config.get().max_duel_amt} coins.",
                        guard=lambda: self.most_recent_proposal is duel
                    )
                else:
                    await sender.send_guarded(
                        f"!accept {rand_emoji()}",
                        guard=lambda: self.most_recent_proposal is duel
                    )
                """