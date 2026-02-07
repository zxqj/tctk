from dataclasses import dataclass
import yaml
from typing import ClassVar, Optional, Callable
import dataclasses
from dataclasses import dataclass
from pathlib import Path

from twitchAPI.type import AuthScope
import os

def conf_path():
    env_val = os.getenv("TWITCH_CREDENTIALS_PATH")
    if env_val is not None:
        return Path(env_val)
    return Path('./config.yaml')

@dataclass
class App:
    id: str
    secret: str

@dataclass
class OauthTokens:
    access: str
    refresh: str
    scopes: list[AuthScope]

@dataclass
class MessageTemplates:
    raffle_open: str
    duel_complete: str
    duel_complete_irc: str
    duel_proposed: str
    give: str

@dataclass
class Config:
    message_templates: MessageTemplates
    app: App
    oauth_tokens: OauthTokens
    conf: ClassVar[Optional[Config]] = None


    @staticmethod
    def backup():
        Config.conf = Config.get()
        d = dataclasses.asdict(Config.conf)
        d['oauth_tokens']['scopes'] = [s.value for s in d['oauth_tokens']['scopes']]
        with conf_path().with_suffix(".back").open('w') as f:
            yaml.dump(d, f)

    @staticmethod
    def persist_with(update: Callable[[Config], None]):
        Config.conf = Config.get()
        update(Config.conf)
        d = dataclasses.asdict(Config.conf)
        d['oauth_tokens']['scopes'] = [s.value for s in d['oauth_tokens']['scopes']]
        with conf_path().open('w') as f:
            yaml.dump(d, f)

    @staticmethod
    def get():
        if Config.conf is None:
            with conf_path().open() as f:
                yaml_dict: dict = yaml.safe_load(f)
                yaml_dict['app'] = App(**yaml_dict['app'])
                yaml_dict['oauth_tokens'] = OauthTokens(**yaml_dict['oauth_tokens'])
                yaml_dict['message_templates'] = MessageTemplates(**yaml_dict['message_templates'])
                Config.conf = Config(**yaml_dict)
                Config.conf.oauth_tokens.scopes = [AuthScope(s) for s in Config.conf.oauth_tokens.scopes]
        return Config.conf
