from inspect import iscoroutinefunction
from typing import Type, Any

import asyncclick as click

from tctk.features.auto_resp_feature import AutoRespFeature
from tctk.config import Config
from tctk.features.se.raffle.raffle_features import RaffleGiveawayFeature, RaffleJoinFeature, RaffleReportFeature
from tctk.features.status_notification import StatusNotificationFeature

from . import BotFeature, Subscription
from .bot import ChatBot
from sys import modules
import dataclasses

from .features.se.duel.duel_bot import DuelBotFeature
from .features.feature_manager import FeatureManagerFeature
from .features.se.raffle.raffle_feature import RaffleFeature
from .features.se.streamelements_tracker import StreamElementsTrackerFeature

logger = Config.logger(__name__)

feature_registry: dict[str, Type[BotFeature]] = {
    "dueler": DuelBotFeature,
    "auto_responder": AutoRespFeature,
    "raffle_join": RaffleJoinFeature,
    "raffle_giveaway": RaffleGiveawayFeature,
    "raffle_report": RaffleReportFeature,
    "status_notification": StatusNotificationFeature,
    "streamelements_tracker": StreamElementsTrackerFeature,
}

default_features = ["streamelements_tracker"]

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
    def expand_deps(names):
        seen: dict[str, None] = {}
        def visit(n):
            if n in seen:
                return
            for dep in getattr(feature_registry[n], "requires", []) or []:
                visit(dep)
            seen[n] = None
        for n in names:
            visit(n)
        return list(seen.keys())

    features = expand_deps(dict.fromkeys(default_features + list(features)))
    feature_args: dict[str, dict[str, Any]] = {
        "raffle_tracker": {"raffle_bot_username": Config.get().raffle_authority_user}
    }
    if updates is not None:
        feature_args['status_notification'] = { "updates_message": updates }

    active: dict[str, BotFeature] = {}
    for feature in features:
        if feature in feature_args:
            active[feature] = feature_registry[feature](**feature_args[feature])
        else:
            active[feature] = feature_registry[feature]()

    manager = FeatureManagerFeature(
        feature_registry=feature_registry,
        active=active,
        feature_args=feature_args,
    )
    active["feature_manager"] = manager

    for feature in active.values():
        if iscoroutinefunction(feature.on_start):
            await feature.on_start()
        else:
            feature.on_start()

    async def register_initial_features(b):
        for name, feature in active.items():
            handlers: list[tuple[Any, Any]] = []
            for event_type, cb in feature.get_subscriptions():
                wrapper = manager._wrap_subscription(cb, b.sender)
                b.chat.register_event(event_type, wrapper)
                handlers.append((event_type, wrapper))
            manager.record_initial_handlers(name, handlers)

    bot = await ChatBot.create(
        channel=channel,
        subscriptions=[],
        post_subscribe=register_initial_features,
    )

    async def stop_features():
        for feature in active.values():
            if iscoroutinefunction(feature.on_exit):
                await feature.on_exit(bot.sender)
            else:
                feature.on_exit(bot.sender)

    await bot.run(before_stop=[stop_features])
