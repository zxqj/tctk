import dataclasses

from tctk import ChannelSender
from tctk.duel import Duel
from tctk.message_bot import MessageBotFeature
from twitchAPI.chat import ChatMessage
from .config import Config

history = dict()
@dataclasses.dataclass
class DuelBotFeature(MessageBotFeature):
    async def on_message(self, msg: ChatMessage, sender: ChannelSender):
        duel = Duel.from_proposal(msg)
        if duel is not None:
            if duel.duel_offer_recipient == sender.username:
                if duel.amount > Config.get().max_duel_amt:
                    await sender.send(f"!deny Fricc The maximum duel amount is {Config.get().max_duel_amt} coins.")
                else:
                    await sender.send_unique("!accept")

