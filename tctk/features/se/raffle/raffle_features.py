from twitchAPI.chat import ChatMessage

from tctk.bot import ChannelSender
from tctk.config import Command, Config
from tctk.features.se.raffle.raffle_feature import RaffleEventData, RaffleFeature

logger = Config.logger(__name__)

class RaffleJoinFeature(RaffleFeature):
    def __init__(self, *args):
        super().__init__(*args)
    async def on_open(self, event_data, sender):
        return await sender.send_unique(Command.raffle_join())

class RaffleGiveawayFeature(RaffleFeature):
    requires = ["raffle_join"]

    def __init__(self, *args):
        super().__init__(*args)

    async def on_close(self, event_data: RaffleEventData, sender: ChannelSender):
        logger.debug("close")
        logger.debug(event_data.raffle.winners)
        raffle = event_data.raffle
        if sender.user.name in raffle.winners:
            non_winning_joiners = set(raffle.joiners.keys()).difference(raffle.winners)
            winner_rcvd_amt = raffle.amount // len(raffle.winners)
            each = winner_rcvd_amt // len(non_winning_joiners)
            await sender.send_unique("EastCoin HandsUp EastCoin")
            for loser in non_winning_joiners:
                await sender.send_unique(Command.give(loser, each))


class RaffleReportFeature(RaffleFeature):
    def __init__(self, *args):
        super().__init__(*args)

    async def on_close(self, event_data: RaffleEventData, sender: ChannelSender):
        participant_count = len(event_data.raffle.joiners)
        success_prob = len(event_data.raffle.winners)/participant_count
        await sender.send_unique("Nerdge total raffle participants: {0:d} Nerdge P(success) = {1:.2f} Nerdge".format(participant_count, success_prob))