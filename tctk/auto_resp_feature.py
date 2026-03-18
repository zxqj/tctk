from dataclasses import dataclass
import re

from twitchAPI.chat import ChatMessage
from functools import reduce
from tctk.bot import ChannelSender
from tctk.config import Config
from tctk.message_bot import MessageBotFeature

CON_WORD_PATTERN = re.compile(r"\bcon\w*", re.IGNORECASE)
CON_BEG_PATTERN = re.compile(r"\bcon", re.IGNORECASE)
ARE_MOD_PATTERN = re.compile("are mod|our mod", re.IGNORECASE)

def replace_con_words(text: str) -> str:
    return CON_BEG_PATTERN.sub("Kon ... ", text)

@dataclass
class AutoRespFeature(MessageBotFeature):
    async def on_message(self, msg: ChatMessage, sender: ChannelSender):
        
        # Nut button 'functionality'
        if "nutButton" in msg.text:
            await sender.send_unique("gachiHYPER l! uwotWater")

        # Go Hornets
        if CON_WORD_PATTERN.search(msg.text) is not None:
            if reduce(lambda a, b: a or b, [bw in msg.text.lower() for bw in Config.get().auto_timeout_words]):
                await sender.send_unique("Fricc")
            else:
                response = ""
                text = msg.text.replace("Concern", "")
                for match in CON_WORD_PATTERN.finditer(text):
                    response = replace_con_words(match.group())
                    response = f"bUrself {response}? bUrself LETSGOOO"
                    await sender.send_unique(response)

        # ARE MOD HandsUp is an awesome mod HandsUp HE REIGNS HandsUp  
        if ARE_MOD_PATTERN.search(msg.text) is not None:
            await sender.send_unique("HE REIGNS HandsUp")
        
        if "BatMan" in msg.text:
            await sender.send_unique("BatMan I'm the REAL BATMAN ReallyMad BatMan")