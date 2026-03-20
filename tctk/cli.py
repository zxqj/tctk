from inspect import iscoroutinefunction
from typing import Type, Any

import asyncclick as click

from tctk.auto_resp_feature import AutoRespFeature
from tctk.config import Config
from tctk.raffle.raffle_features import GiveawayRaffleFeature, RaffleReportFeature
from tctk.status_notification import StatusNotificationFeature

from . import BotFeature, Subscription
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
    "raffle_report": RaffleReportFeature,
    "status_notification": StatusNotificationFeature,
}

feature_args: dict[str, dict[str, Any]] = {
    "raffle_tracker": {"raffle_bot_username": "streamelements"}
}
# Variant C: custom validation callback (useful for complex rules)
def _validate_features(ctx, param, value):
    # value is a tuple when using nargs or multiple
    invalid = [v for v in value if v not in feature_registry.keys()]
    if invalid:
        raise click.BadParameter(f"Invalid feature(s): {', '.join(invalid)}.  Possible values: [{', '.join(feature_registry.keys())}]")
    return list(value)

# Events occur in the following order:
#   * Features are instantiated
#   * Feature on_start is called
#   * Feature event subscriptions are retrieved
#   * ChatBot is instantiated, passing the subscriptions
#       * ChatBot class is instantiated
#       * ChatBot subscribes the features to its events
#   * ChatBot is started
#   * ChatBot joins channel (emitting the JOINED event)

@click.command()
@click.option("--channel", "-c", "channel", default=Config.get().channel)
@click.option("--updates")
@click.argument("features", nargs=-1, callback=_validate_features)
async def cli(channel, updates, features):
    feature_instances: list[BotFeature] = []
    if updates is not None:
        feature_args['status_notification'] = { "updates_message": updates }

    for feature in features:
        if feature in feature_args:
            feature_instances.append(feature_registry[feature](*feature_args[feature]))
        else:
            feature_instances.append(feature_registry[feature]())

    for feature in feature_instances:
        if iscoroutinefunction(feature.on_start):
            await feature.on_start()
        else:
            feature.on_start()

    subscriptions: list[Subscription] = []
    for feature in feature_instances:
        subscriptions.extend(feature.get_subscriptions())

    bot = await ChatBot.create(channel=channel, subscriptions=subscriptions)

    for feature in feature_instances:
        if iscoroutinefunction(feature.on_exit):
            await feature.on_exit(bot.sender)
        else:
            feature.on_exit(bot.sender)
