from tctk.bot import ChannelSender
from tctk.config import Config
from tctk.features.se.duel.duel import DuelOffer, Duel
from tctk.features.message_bot import MessageBotFeature
from twitchAPI.chat import ChatMessage


class DuelFeature(MessageBotFeature):
    def __init__(self, duel_authority_user=Config.get().duel_authority_user):
        self.duel_authority_user = duel_authority_user
        self._pending_proposal: DuelOffer | None = None

    async def on_proposal(self, proposal: DuelOffer, sender: ChannelSender):
        pass

    async def on_result(self, duel: Duel, sender: ChannelSender):
        pass

    async def on_message(self, msg: ChatMessage, sender: ChannelSender):
        proposal = DuelOffer.from_proposal(msg)
        if proposal:
            self._pending_proposal = proposal.val
            await self.on_proposal(self._pending_proposal, sender)
            return

        result = Duel.from_result(msg, self._pending_proposal)
        if result:
            await self.on_result(result.val, sender)
            self._pending_proposal = None
