# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**tctk** is a Twitch chat bot built on the `twitchAPI` (pytwitchapi) library. It connects to a Twitch channel, authenticates via OAuth, and runs pluggable "features" that react to chat events. Uses Python 3.14+, managed with `uv`.

## Commands

- **Run the bot:** `uv run -m tctk` (or `./run.sh`, which also sets `TWITCH_CREDENTIALS_PATH`)
- **Run with features:** `uv run -m tctk activity_log bot_rinser duel_bot auto_resp giveaway raffle_report`
- **Install dependencies:** `uv sync`
- **Reinstall as tool:** `./uv-reinstall.sh`
- **Run tests:** `uv run pytest` (tests are minimal/outdated — `tests/test_chatbot.py` references old package name)

## Required Environment

- `APP_ENV` must be set to `test`, `production`, or `staging` — controls `Config.data_dir()` path
- `config.yaml` in project root with `app.id`, `app.secret`, `scopes`, `channel`, etc.
- `logging.yaml` in project root for logging configuration
- `twitch_auth.txt` stores OAuth tokens (auto-managed by `UserAuthenticationStorageHelper`)

## Architecture

### Feature Plugin System

The bot uses a plugin pattern centered on `BotFeature` (`tctk/__init__.py`):

1. **`BotFeature`** — base class with `on_start()`, `get_subscriptions()`, `on_exit()` lifecycle hooks. `get_subscriptions()` returns `list[tuple[ChatEvent, handler]]`.
2. **`MessageBotFeature`** (`tctk/message_bot.py`) — subclass of `BotFeature` that simplifies handling `ChatEvent.MESSAGE` events. Subclasses override `on_message(msg, sender)`.
3. **`RaffleFeature`** (`tctk/raffle/raffle_feature.py`) — subclass of `MessageBotFeature` that adds raffle lifecycle: `on_open()`, `on_join()`, `on_close()`.

Feature registration happens in `tctk/cli.py` via `feature_registry` dict mapping string names to feature classes. Features are selected as CLI arguments.

### Key Components

- **`ChatBot`** (`tctk/bot.py`) — wraps `twitchAPI.Chat`, manages connection/auth, delegates events to subscribed feature handlers via `ChannelSender` (a proxy around `Chat` that pins a channel and adds `send_unique()` for dedup via random emoji).
- **`Config`** (`tctk/config.py`) — singleton dataclass loaded from `config.yaml`. Also provides `Config.logger()`, `Config.persist_with()` for updating config on disk, and `Config.data_dir()` which varies by `APP_ENV`.
- **`ActivityLogPersistence`** (`tctk/activity_log.py`) — writes JSON activity logs to `~/var/log/tctk/`, handles OS signals for graceful shutdown, rotates files at 5MB.
- **`store.py`** — Polars-based persistence for raffle/duel data using Parquet files.

### Inheritance Chain for Features

```
BotFeature
├── ActivityLogFeature (subscribes to ALL ChatEvent types)
├── MessageBotFeature (subscribes to ChatEvent.MESSAGE)
│   ├── AutoRespFeature
│   ├── BotRinseFeature
│   ├── DuelBotFeature
│   └── RaffleFeature
│       ├── GiveawayRaffleFeature
│       └── RaffleReportFeature
```

### Config / Data Flow

- Config is loaded once via `Config.get()` (singleton) from `config.yaml` in the project root
- `Command` enum (`config.py`) formats chat commands like `!give`, `!join`, `!duel`
- Activity logs go to `~/var/log/tctk/` (or `/test`/`/staging` subdirs based on `APP_ENV`)
