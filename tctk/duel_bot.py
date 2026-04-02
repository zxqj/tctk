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
        if await self._handle_set(msg, sender):
            return

        if DuelOffer.from_proposal(msg).intoprop(self, DuelBotFeature.most_recent_proposal):
            if self._mrp.offeree.casefold() == msg.chat.username.casefold():
                duel_max = Config.get().max_duel_amt
                no = Command.deny(f"Fricc The maximum duel amount is {duel_max} coins.")
                yes = Command.accept()
                logger.variable(self._mrp.offerer)
                await sender.send_result(lambda: no if self._mrp.amount > duel_max else yes)

    async def _handle_set(self, msg: ChatMessage, sender: ChannelSender) -> bool:
        if msg.user.name.casefold() != Config.get().bot_config_user.casefold():
            return False
        parts = msg.text.strip().split()
        if len(parts) != 3 or parts[0] != "!set" or parts[1] != "max_duel_amt":
            return False
        try:
            new_max = int(parts[2])
        except ValueError:
            return False
        Config.persist_with(lambda c: setattr(c, 'max_duel_amt', new_max))
        logger.info(f"max_duel_amt set to {new_max} by {msg.user.name}")
        await sender.send(f"Max duel amount set to {new_max} coins.")
        return True