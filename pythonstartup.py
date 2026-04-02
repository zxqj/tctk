"""
PYTHONSTARTUP file for interactive tctk sessions.

Usage:
    APP_ENV=production PYTHONSTARTUP=pythonstartup.py uv run python

Provides:
    sender  — ChannelSender connected to the configured channel
    V       — alpha_format.FontVariant
    bot     — the ChatBot instance
    ds, f, ss — DoubleStruck, Fraktur, SansSerif senders
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

make_sender = lambda v, **kwargs: lambda s: send(v.formatter(**kwargs)(s))

ds = make_sender(V.DoubleStruck)
f = make_sender(V.Fraktur)
ss = make_sender(V.SansSerif)

s = send
ms = make_sender

print(f"Connected to #{_channel}")
import io
buff = io.StringIO()

print(
    "Available:\n"
    "  s(msg)              — send a message\n"
    "  ms(variant, **kw)   — make a sender, e.g. ms(V.SansSerif, bold=True, italic=True)\n"
    "  sender              — ChannelSender instance\n"
    "  bot                 — ChatBot instance\n"
    "  V                   — FontVariant enum\n"
    "  ds, f, ss           — senders: DoubleStruck, Fraktur, SansSerif\n"
    '                        e.g. ds("hey mods")'
)
