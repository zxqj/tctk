import logging
import re
import time
from typing import Callable, Self
from tctk import ChannelSender, Subscription
from tctk.bot import rand_emoji
from tctk.duel import Duel, DuelOffer, Regex
from tctk.duel_feature import DuelFeature
from tctk.message_bot import MessageBotFeature
from twitchAPI.chat import ChatMessage, EventData
from twitchAPI.type import ChatEvent
from .config import Command, Config

history = dict()
logger = logging.getLogger(__name__)


def resolve_max_duel_amt(max_duel_amt: int | str, current_coins: int | None, floor: int = 0) -> int | None:
    if isinstance(max_duel_amt, str) and max_duel_amt.endswith('%'):
        pct = float(max_duel_amt[:-1]) / 100
        if current_coins is None:
            return None
        return max(int(current_coins * pct), floor)
    return int(max_duel_amt)


class DuelBotFeature(DuelFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_coins: int | None = None
        self._coins_queried: bool = False

    async def _on_joined(self, event: EventData, sender: ChannelSender):
        if not self._coins_queried:
            self._coins_queried = True
            logger.info("Querying coin balance")
            await sender.send_message(str(Command.coins))

    def get_subscriptions(self) -> list[Subscription]:
        subs = super().get_subscriptions()
        subs.append((ChatEvent.JOINED, self._on_joined))
        return subs

    async def on_proposal(self, proposal: DuelOffer, sender: ChannelSender):
        if proposal.offeree.casefold() != sender.chat.username.casefold():
            return

        cfg = Config.get()
        duel_max = resolve_max_duel_amt(cfg.max_duel_amt, self.current_coins, cfg.min_max_duel_amt_if_percent)
        if duel_max is None:
            logger.warning("Cannot determine max duel amount (coins unknown), denying")
            await sender.send_unique(Command.deny("Fricc I don't know how many coins I have yet."))
            return

        no = Command.deny(f"Fricc The maximum duel amount is {duel_max} coins.")
        yes = Command.accept()
        logger.debug(f"Duel proposal from {proposal.offerer} for {proposal.amount}, max={duel_max}")
        await sender.send_result(lambda: no if proposal.amount > duel_max else yes)

    async def on_result(self, duel: Duel, sender: ChannelSender):
        bot_name = sender.chat.username.casefold()
        if duel.offerer.casefold() != bot_name and duel.offeree.casefold() != bot_name:
            return

        bot_is_offerer = duel.offerer.casefold() == bot_name
        bot_won = (bot_is_offerer and duel.offerer_win) or (not bot_is_offerer and not duel.offerer_win)

        if self.current_coins is not None:
            if bot_won:
                self.current_coins += duel.amount
            else:
                self.current_coins -= duel.amount
            logger.info(f"Coins updated: {'won' if bot_won else 'lost'} {duel.amount}, balance={self.current_coins}")

    async def on_message(self, msg: ChatMessage, sender: ChannelSender):
        if await self._handle_set(msg, sender):
            return

        if self._handle_coins_response(msg, sender):
            return

        if self._handle_give(msg, sender):
            return

        if self._handle_raffle_win(msg, sender):
            return

        await super().on_message(msg, sender)

    def _handle_coins_response(self, msg: ChatMessage, sender: ChannelSender) -> bool:
        if msg.user.name.casefold() != Config.get().duel_authority_user.casefold():
            return False
        m = re.search(Regex.coins_response, msg.text)
        if m is None:
            return False
        username = m.group('username')
        if username.casefold() != sender.chat.username.casefold():
            return False
        self.current_coins = int(m.group('coins'))
        logger.info(f"Coin balance: {self.current_coins}")
        return True

    _raffle_close_re = re.compile(
        r'The Multi-Raffle has ended and (.+) won (\d+) EastCoin each'
    )

    def _handle_raffle_win(self, msg: ChatMessage, sender: ChannelSender) -> bool:
        if msg.user.name.casefold() != Config.get().raffle_authority_user.casefold():
            return False
        m = self._raffle_close_re.search(msg.text)
        if m is None:
            return False
        winners_str = m.group(1)
        amount_each = int(m.group(2))
        winners = [w.strip().casefold() for w in re.split(r',\s*|\s+and\s+', winners_str) if w.strip()]
        bot_name = sender.chat.username.casefold()
        if bot_name in winners and self.current_coins is not None:
            self.current_coins += amount_each
            logger.info(f"Won raffle for {amount_each}, balance={self.current_coins}")
        return False

    def _handle_give(self, msg: ChatMessage, sender: ChannelSender) -> bool:
        if msg.user.name.casefold() != Config.get().duel_authority_user.casefold():
            return False
        m = re.search(Regex.coins_given, msg.text)
        if m is None:
            return False
        bot_name = sender.chat.username.casefold()
        giver = m.group('giver')
        receiver = m.group('receiver')
        amount = int(m.group('amount'))
        if giver.casefold() == bot_name:
            if self.current_coins is not None:
                self.current_coins -= amount
                logger.info(f"Gave {amount} to {receiver}, balance={self.current_coins}")
            return True
        if receiver.casefold() == bot_name:
            if self.current_coins is not None:
                self.current_coins += amount
                logger.info(f"Received {amount} from {giver}, balance={self.current_coins}")
            return True
        return False

    async def _handle_set(self, msg: ChatMessage, sender: ChannelSender) -> bool:
        if msg.user.name.casefold() != Config.get().bot_config_user.casefold():
            return False
        parts = msg.text.strip().split()
        if len(parts) != 3 or parts[0] != "!set" or parts[1] != "max_duel_amt":
            return False
        raw_value = parts[2]
        if raw_value.endswith('%'):
            try:
                float(raw_value[:-1])
            except ValueError:
                return False
            new_max = raw_value
        else:
            try:
                new_max = int(raw_value)
            except ValueError:
                return False

        Config.persist_with(lambda c: setattr(c, 'max_duel_amt', new_max))
        logger.info(f"max_duel_amt set to {new_max} by {msg.user.name}")
        await sender.send(f"Max duel amount set to {new_max}.")
        return True
