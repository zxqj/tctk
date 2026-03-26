import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tctk.bot import ChannelSender
from tctk.duel_bot import DuelBotFeature


def make_config(max_duel_amt=500, duel_authority_user="streamelements"):
    conf = MagicMock()
    conf.max_duel_amt = max_duel_amt
    conf.duel_authority_user = duel_authority_user
    return conf


def make_proposal_msg(offerer, offeree, amount, authority_user="streamelements", timestamp=1000):
    msg = MagicMock()
    msg.user.name = authority_user
    msg.text = (
        f"@{offeree}, @{offerer} wants to duel you for {amount} eastcoins, "
        f"you can !accept or !deny within 2 minutes"
    )
    msg.sent_timestamp = timestamp
    msg.chat.username = offeree
    msg.chat.room_cache.keys.return_value = []
    return msg


def make_sender(username="mybot", slow_delay=0):
    """Create a mock sender. If slow_delay > 0, sends sleep before recording."""
    sent = []

    async def _send(text, delay=None):
        if slow_delay > 0:
            await asyncio.sleep(slow_delay)
        sent.append(text)

    async def _send_result(gen_msg):
        if slow_delay > 0:
            await asyncio.sleep(slow_delay)
        sent.append(gen_msg())

    async def _send_guarded(text, guard):
        if slow_delay > 0:
            await asyncio.sleep(slow_delay)
        if not guard():
            return False
        sent.append(text)
        return True

    sender = MagicMock()
    sender.username = username
    sender.send = _send
    sender.send_result = _send_result
    sender.send_guarded = _send_guarded
    sender._sent = sent
    return sender


def make_real_sender(username="mybot", channel="testchannel", slow=3):
    """Create a real ChannelSender backed by a mock Chat with slow mode."""
    sent = []

    room = MagicMock()
    room.slow = slow

    chat = MagicMock()
    chat.room_cache = {channel: room}
    chat.username = username

    async def record_send(ch, text):
        sent.append(text)

    chat.send_message = AsyncMock(side_effect=record_send)

    sender = ChannelSender(chat, channel)
    sender._last_send_time = time.monotonic()
    sender._sent = sent
    return sender


@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_single_valid_proposal_accepted(mock_config_cls, mock_duel_config):
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_sender()

    msg = make_proposal_msg("alice", "mybot", 100)
    await feature.on_message(msg, sender)

    assert len(sender._sent) == 1
    assert "!accept" in sender._sent[0]


@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_single_excessive_proposal_denied(mock_config_cls, mock_duel_config):
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_sender()

    msg = make_proposal_msg("alice", "mybot", 1000)
    await feature.on_message(msg, sender)

    assert len(sender._sent) == 1
    assert "!deny" in sender._sent[0]


@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_stale_accept_suppressed_by_send_result(mock_config_cls, mock_duel_config):
    """Valid duel A starts slow-mode wait, then excessive duel B arrives.
    send_result evaluates the lambda after the wait, seeing B's amount."""
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_sender(slow_delay=0.5)

    msg_a = make_proposal_msg("alice", "mybot", 100, timestamp=1000)
    msg_b = make_proposal_msg("bob", "mybot", 1000, timestamp=1001)

    task_a = asyncio.create_task(feature.on_message(msg_a, sender))
    await asyncio.sleep(0.1)
    task_b = asyncio.create_task(feature.on_message(msg_b, sender))

    await asyncio.gather(task_a, task_b)

    # Both send_result calls evaluate their lambdas after the wait.
    # By then _mrp is duel_b (amount=1000), so both lambdas produce !deny.
    deny_msgs = [m for m in sender._sent if "!deny" in m]
    accept_msgs = [m for m in sender._sent if "!accept" in m]
    assert len(accept_msgs) == 0
    assert len(deny_msgs) >= 1


@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_second_valid_proposal_replaces_first(mock_config_cls, mock_duel_config):
    """Two valid proposals in quick succession — both lambdas see the latest."""
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_sender(slow_delay=0.5)

    msg_a = make_proposal_msg("alice", "mybot", 100, timestamp=1000)
    msg_b = make_proposal_msg("bob", "mybot", 200, timestamp=1001)

    task_a = asyncio.create_task(feature.on_message(msg_a, sender))
    await asyncio.sleep(0.1)
    task_b = asyncio.create_task(feature.on_message(msg_b, sender))

    await asyncio.gather(task_a, task_b)

    # Both produce !accept (both under limit), no stale accept for wrong duel
    assert all("!accept" in m for m in sender._sent)


@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_single_proposal_with_slow_mode_still_responds(mock_config_cls, mock_duel_config):
    """A single valid proposal should send even when slow mode delays it."""
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_sender(slow_delay=0.5)

    msg = make_proposal_msg("alice", "mybot", 100)
    await feature.on_message(msg, sender)

    assert len(sender._sent) == 1
    assert "!accept" in sender._sent[0]



@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_non_proposal_message_ignored(mock_config_cls, mock_duel_config):
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_sender()

    msg = MagicMock()
    msg.user.name = "randomuser"
    msg.text = "hello world"
    msg.chat.room_cache.keys.return_value = []

    await feature.on_message(msg, sender)

    assert len(sender._sent) == 0


@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_slow_mode_second_proposal_over_limit_denied(mock_config_cls, mock_duel_config):
    """Two proposals 1s apart in a room with slow=3.  Second is over the limit.
    send_result evaluates the lambda after the slow-mode wait, seeing B's amount."""
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_real_sender(slow=3)

    msg_a = make_proposal_msg("alice", "mybot", 100, timestamp=1000)
    msg_b = make_proposal_msg("bob", "mybot", 1000, timestamp=1001)

    task_a = asyncio.create_task(feature.on_message(msg_a, sender))
    await asyncio.sleep(1)
    task_b = asyncio.create_task(feature.on_message(msg_b, sender))

    await asyncio.gather(task_a, task_b)

    # No accept should have gone through — both lambdas see _mrp.amount=1000
    accept_msgs = [m for m in sender._sent if "!accept" in m]
    deny_msgs = [m for m in sender._sent if "!deny" in m]
    assert len(accept_msgs) == 0
    assert len(deny_msgs) >= 1


@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_slow_mode_second_proposal_under_limit_accepted(mock_config_cls, mock_duel_config):
    """Two proposals 1s apart in a room with slow=3.  Second is under the limit.
    Both lambdas evaluate against _mrp (the latest), so both produce !accept."""
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_real_sender(slow=3)

    msg_a = make_proposal_msg("alice", "mybot", 100, timestamp=1000)
    msg_b = make_proposal_msg("bob", "mybot", 200, timestamp=1001)

    task_a = asyncio.create_task(feature.on_message(msg_a, sender))
    await asyncio.sleep(1)
    task_b = asyncio.create_task(feature.on_message(msg_b, sender))

    await asyncio.gather(task_a, task_b)

    assert all("!accept" in m for m in sender._sent)
    assert len(sender._sent) >= 1


@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_two_proposals_4s_apart_both_accepted(mock_config_cls, mock_duel_config):
    """Two 1-coin proposals from different users, 4 seconds apart in slow=3 room.
    The slow-mode delay (3s) has fully elapsed by the time the second arrives."""
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_real_sender(username="are_mod", slow=3)

    msg_a = make_proposal_msg("alice", "are_mod", 1, timestamp=1000)
    msg_b = make_proposal_msg("bob", "are_mod", 1, timestamp=1004)

    task_a = asyncio.create_task(feature.on_message(msg_a, sender))
    await asyncio.sleep(4)
    task_b = asyncio.create_task(feature.on_message(msg_b, sender))

    await asyncio.gather(task_a, task_b)

    assert len(sender._sent) == 2
    assert all("!accept" in m for m in sender._sent)


@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_two_proposals_1s_apart_both_accepted(mock_config_cls, mock_duel_config):
    """Two 1-coin proposals from different users, 1 second apart in slow=3 room.
    The second arrives before slow mode expires from the first."""
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_real_sender(username="are_mod", slow=3)

    msg_a = make_proposal_msg("alice", "are_mod", 1, timestamp=1000)
    msg_b = make_proposal_msg("bob", "are_mod", 1, timestamp=1001)

    task_a = asyncio.create_task(feature.on_message(msg_a, sender))
    await asyncio.sleep(1)
    task_b = asyncio.create_task(feature.on_message(msg_b, sender))

    await asyncio.gather(task_a, task_b)

    assert all("!accept" in m for m in sender._sent)
    assert len(sender._sent) >= 1


@pytest.mark.asyncio
@patch("tctk.duel.Config")
@patch("tctk.duel_bot.Config")
async def test_two_proposals_1s_apart_second_over_limit_denied(mock_config_cls, mock_duel_config):
    """Two proposals 1 second apart: first is 1 coin, second is 501 (over limit).
    Both lambdas evaluate against _mrp (the latest), so both produce !deny."""
    cfg = make_config(max_duel_amt=500)
    mock_config_cls.get.return_value = cfg
    mock_duel_config.get.return_value = cfg
    feature = DuelBotFeature()
    sender = make_real_sender(username="are_mod", slow=3)

    msg_a = make_proposal_msg("alice", "are_mod", 1, timestamp=1000)
    msg_b = make_proposal_msg("bob", "are_mod", 501, timestamp=1001)

    task_a = asyncio.create_task(feature.on_message(msg_a, sender))
    await asyncio.sleep(1)
    task_b = asyncio.create_task(feature.on_message(msg_b, sender))

    await asyncio.gather(task_a, task_b)

    accept_msgs = [m for m in sender._sent if "!accept" in m]
    deny_msgs = [m for m in sender._sent if "!deny" in m]
    assert len(accept_msgs) == 0
    assert len(deny_msgs) >= 1
