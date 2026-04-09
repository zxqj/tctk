import logging
from inspect import iscoroutinefunction
from typing import Any, Type

from twitchAPI.chat import ChatMessage

from tctk import BotFeature, ChannelSender, Subscription
from tctk.config import Config
from tctk.features.message_bot import MessageBotFeature

logger = logging.getLogger(__name__)

PROTECTED_FEATURES: set[str] = {"streamelements_tracker"}


class FeatureManagerFeature(MessageBotFeature):
    """Provides chat commands to list, add, and remove features at runtime.

    Commands (restricted to Config.get().bot_config_user):
        !features                  - list active features
        !feature_add <name>        - instantiate, start, and subscribe a feature
        !feature_remove <name>     - unsubscribe and stop a feature

    Features in PROTECTED_FEATURES cannot be removed.
    """

    def __init__(
        self,
        feature_registry: dict[str, Type[BotFeature]],
        active: dict[str, BotFeature],
        feature_args: dict[str, dict[str, Any]] | None = None,
    ):
        self.feature_registry = feature_registry
        # name -> (feature instance, [(event_type, wrapper_handler), ...])
        self.active: dict[str, tuple[BotFeature, list[tuple[Any, Any]]]] = {
            name: (inst, []) for name, inst in active.items()
        }
        self.feature_args = feature_args or {}

    def record_initial_handlers(self, name: str, handlers: list[tuple[Any, Any]]):
        """Called by cli after initial subscription to track handlers for later removal."""
        if name in self.active:
            inst, _ = self.active[name]
            self.active[name] = (inst, handlers)

    def _instantiate(self, name: str) -> BotFeature:
        cls = self.feature_registry[name]
        if name in self.feature_args:
            return cls(**self.feature_args[name])
        return cls()

    def _wrap_subscription(self, cb, sender: ChannelSender):
        async def handler(*args):
            await cb(*args, sender)
        return handler

    def _deps_of(self, name: str) -> list[str]:
        return list(getattr(self.feature_registry[name], "requires", []) or [])

    def _dependents_of(self, name: str) -> list[str]:
        result = []
        for other in self.active.keys():
            if other == name:
                continue
            if name in self._deps_of(other):
                result.append(other)
        return result

    async def _add_one(self, name: str, sender: ChannelSender) -> str:
        feature = self._instantiate(name)
        if iscoroutinefunction(feature.on_start):
            await feature.on_start()
        else:
            feature.on_start()

        chat = sender.chat
        handlers: list[tuple[Any, Any]] = []
        for event_type, cb in feature.get_subscriptions():
            wrapper = self._wrap_subscription(cb, sender)
            chat.register_event(event_type, wrapper)
            handlers.append((event_type, wrapper))

        self.active[name] = (feature, handlers)
        return f"added {name}"

    async def _add(self, name: str, sender: ChannelSender) -> str:
        if name not in self.feature_registry:
            return f"unknown feature: {name}"
        if name in self.active:
            return f"{name} already active"

        # Resolve dependency order (depth-first, dedup).
        order: dict[str, None] = {}
        def visit(n: str):
            if n in order or n in self.active:
                return
            if n not in self.feature_registry:
                raise KeyError(n)
            for dep in self._deps_of(n):
                visit(dep)
            order[n] = None
        try:
            visit(name)
        except KeyError as e:
            return f"unknown dependency: {e.args[0]}"

        results = []
        for n in order.keys():
            results.append(await self._add_one(n, sender))
        return "; ".join(results)

    async def _remove_one(self, name: str, sender: ChannelSender) -> str:
        feature, handlers = self.active.pop(name)
        chat = sender.chat
        for event_type, wrapper in handlers:
            try:
                chat.unregister_event(event_type, wrapper)
            except Exception as e:
                logger.warning(f"failed to unregister handler for {name}: {e}")

        try:
            if iscoroutinefunction(feature.on_exit):
                await feature.on_exit(sender)
            else:
                feature.on_exit(sender)
        except Exception as e:
            logger.warning(f"on_exit for {name} failed: {e}")

        return f"removed {name}"

    async def _remove(self, name: str, sender: ChannelSender) -> str:
        if name not in self.active:
            return f"{name} not active"

        # Compute removal set: name plus everything that (transitively) depends on it.
        to_remove: dict[str, None] = {}
        def visit(n: str):
            if n in to_remove:
                return
            for dep in self._dependents_of(n):
                visit(dep)
            to_remove[n] = None
        visit(name)

        protected = [n for n in to_remove if n in PROTECTED_FEATURES]
        if protected:
            return f"cannot remove {name}: would also remove protected feature(s) {', '.join(protected)}"

        results = []
        for n in to_remove.keys():
            results.append(await self._remove_one(n, sender))
        return "; ".join(results)

    def _list(self) -> str:
        if not self.active:
            return "no active features"
        names = sorted(self.active.keys())
        return "features: " + ", ".join(names)

    async def on_message(self, msg: ChatMessage, sender: ChannelSender):
        text = msg.text.strip()
        if not text.startswith("!"):
            return

        cfg = Config.get()
        parts = text.split()
        cmd = parts[0]

        if cmd not in ("!features", "!feature_add", "!feature_remove"):
            return

        if msg.user.name.casefold() != cfg.bot_config_user.casefold():
            return

        if cmd == "!features":
            await sender.send_message(self._list())
            return

        if len(parts) < 2:
            await sender.send_message(f"usage: {cmd} <feature_name>")
            return

        name = parts[1]
        if cmd == "!feature_add":
            result = await self._add(name, sender)
        else:
            result = await self._remove(name, sender)
        await sender.send_message(result)
