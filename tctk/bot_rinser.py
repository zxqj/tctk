from tctk.config import Command
from tctk.message_bot import MessageBotFeature
import re
import dataclasses

@dataclasses.dataclass
class BotRinseFeature(MessageBotFeature):
    authorized_cmd_user: str
    command: Command
    start_amount: int

    async def on_message(self, msg, sender):
        match = re.match(msg.text, self.cmd_text)
        if msg.user == self.authorized_cmd_user and match is not None:
            sender.send(f"!duel {self.duel_bot_username} {self.start_amount}")
