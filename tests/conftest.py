from pathlib import Path

import pytest
import yaml
import asyncio
from tctk.bot import ChatBot
from tctk.duel import DuelOffer

duel_bot_user = "are_mod"


@pytest.fixture
async def bot():
    """Create a ChatBot from tests/test_config.yaml."""
    test_config_path = Path(__file__).parent / "test_config.yaml"
    with open(test_config_path) as f:
        cfg = yaml.safe_load(f)

    channel = cfg["test_channel"]
    tokens_file = cfg["mock_duel_raffle_authority_tokens_file"]

    bot = await ChatBot.create(channel, tokens_file)
    yield bot
    bot.chat.stop()
    await bot.twitch.close()

@pytest.mark.asyncio
@pytest.mark.smoke
async def test_three_or_more(bot):
    offerers = [chr(x) for x in range(0x03B1, 0x3B4)]
    apart = 0.5
    amounts = [2,501,501]
    msgs = [DuelOffer(**{"offeree": duel_bot_user, "offerer": str(x), "amount": y}).proposal_message
        for x, y in zip(offerers, amounts)]
    for msg in msgs:
        await bot.sender.send_message(msg)
        await asyncio.sleep(apart)