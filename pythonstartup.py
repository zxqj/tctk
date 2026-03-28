"""
PYTHONSTARTUP file for interactive tctk sessions.

Usage:
    APP_ENV=production PYTHONSTARTUP=pythonstartup.py uv run python

Provides:
    sender  — ChannelSender connected to the configured channel
    V       — alpha_format.FontVariant
    bot     — the ChatBot instance
"""

import asyncio
import threading

from tctk.bot import ChatBot
from tctk.config import Config
from tctk.alpha_format import FontVariant as V  # noqa: F401

_channel = Config.get().channel
_loop = asyncio.new_event_loop()


def _run_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


_thread = threading.Thread(target=_run_loop, args=(_loop,), daemon=True)
_thread.start()

bot: ChatBot = asyncio.run_coroutine_threadsafe(
    ChatBot.create(channel=_channel), _loop
).result()

sender = bot.sender


def send(msg: str, delay: float = None):
    """Synchronous wrapper: send('hello') or send(V.Script.formatter()('hello'))"""
    asyncio.run_coroutine_threadsafe(sender.send(msg, delay), _loop).result()


print(f"Connected to #{_channel}")
print("Available: send(), sender, V (FontVariant), bot")
