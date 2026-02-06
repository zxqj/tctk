import asyncclick as click
from twitchAPI.type import ChatEvent

from twitchAPI.chat import ChatMessage
from .bot import ChatBot
from dataclasses import dataclass

from .raffle_tracker import make_raffle_tracker, TriggerResp

feature_repository = {'raffle_tracker': make_raffle_tracker(TriggerResp(
    raffle_start_pred=lambda chat_msg: "Multi-Raffle" in chat_msg.text,
    trigger_username="thestreameast",
    response="!join"))}


@click.command()
@click.option("--channel", "-c", "channel", default="thestreameast")
async def cli(channel):
    responder = ChatBot(channel=channel)
    features = [feature_repository["raffle_tracker"]]
    await responder.run(features)
