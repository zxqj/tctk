from typing import Type, Any

import asyncclick as click

from tctk.auto_resp_feature import AutoRespFeature
from tctk.config import Config
from tctk.raffle.raffle_features import GiveawayRaffleFeature, RaffleReportFeature

from . import BotFeature
from .bot_rinser import BotRinseFeature
from .activity_log import ActivityLogFeature
from .bot import ChatBot
from sys import modules
import dataclasses

from .duel_bot import DuelBotFeature
from .raffle.raffle_feature import RaffleFeature

feature_registry: dict[str, Type[BotFeature]] = {
    "activity_log": ActivityLogFeature,
    "bot_rinser": BotRinseFeature,
    "duel_bot": DuelBotFeature,
    "auto_resp": AutoRespFeature,
    "giveaway": GiveawayRaffleFeature,
    "raffle_report": RaffleReportFeature   
}

feature_args: dict[str, dict[str, Any]] = {
    "raffle_tracker": {"raffle_bot_username": "horse_person00"}
}
# Variant C: custom validation callback (useful for complex rules)
def _validate_features(ctx, param, value):
    # value is a tuple when using nargs or multiple
    invalid = [v for v in value if v not in feature_registry.keys()]
    if invalid:
        raise click.BadParameter(f"Invalid feature(s): {', '.join(invalid)}.  Possible values: [{', '.join(feature_registry.keys())}]")
    return list(value)

@click.command()
@click.option("--channel", "-c", "channel", default=Config.get().channel)
@click.argument("features", nargs=-1, callback=_validate_features)
async def cli(channel, features):
    bot = ChatBot(channel=channel)

    await bot.init()

    feature_instances: list[BotFeature] = []

    for feature in features:
        if feature in feature_args:
            feature_instances.append(feature_registry[feature](*feature_args[feature]))
        else:
            feature_instances.append(feature_registry[feature]())

    for feature in feature_instances:
        if hasattr(feature, "on_start"):
            feature.on_start()

    for feature in feature_instances:
        for event_type, handler in feature.get_subscriptions():
            bot.subscribe(event_type, handler)

    await bot.run()

    for feature in feature_instances:
        if hasattr(feature, "on_exit"):
            feature.on_exit()
