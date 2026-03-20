from twitchAPI.chat import ChatMessage

from tctk.bot import ChannelSender
from tctk.config import Command, Config
from tctk.raffle.raffle_feature import RaffleEventData, RaffleFeature

logger = Config.logger(__name__)
class GiveawayRaffleFeature(RaffleFeature):
    def __init__(self, *args):
        super().__init__(*args)

    async def on_open(self, event_data, sender):
        logger.debug("on open event")
        logger.debug(event_data.raffle.amount)
        logger.debug(event_data.raffle.duration)
        logger.debug(event_data.raffle.start_time)
        logger.debug()
        return await sender.send_unique(Command.raffle_join())

    async def on_join(self, event_data, sender):
        logger.debug()
        logger.debug("on join event")
        logger.debug()
        pass

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