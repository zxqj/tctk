from typing import Type, Any

import asyncclick as click

from . import BotFeature
from .activity_log import ActivityLogFeature
from .bot import ChatBot
from sys import modules

from .raffle.raffle_tracker import RaffleFeature

feature_registry: dict[str, Type[BotFeature]] = {
    "raffle_tracker": RaffleFeature,
    "activity_log": ActivityLogFeature,
}

feature_args: dict[str, list[Any]] = {
    "raffle_tracker": ["horse_person00", "Glerp"]
}
# Variant C: custom validation callback (useful for complex rules)
def _validate_features(ctx, param, value):
    # value is a tuple when using nargs or multiple
    invalid = [v for v in value if v not in feature_registry.keys()]
    if invalid:
        raise click.BadParameter(f"Invalid feature(s): {', '.join(invalid)}.  Possible values: [{', '.join(feature_registry.keys())}]")
    return list(value)

@click.command()
@click.option("--channel", "-c", "channel", default="thestreameast")
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
