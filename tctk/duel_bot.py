import dataclasses

from tctk import ChannelSender
from tctk.duel import Duel
from tctk.message_bot import MessageBotFeature
from twitchAPI.chat import ChatMessage

history = dict()
@dataclasses.dataclass
class DuelBotFeature(MessageBotFeature):
    async def on_message(self, msg: ChatMessage, sender: ChannelSender):
        duel = Duel.from_proposal(msg)
        if duel.duel_offer_recipient == sender.username:
            if duel.amount > 100:
                sender.send("Until the bot acquires more coin, the max duel is 100")
            else:
                sender.send("!accept")

