from dataclasses import dataclass
import yaml
from typing import ClassVar, Optional, Callable
import dataclasses
from pathlib import Path

from twitchAPI.type import AuthScope
import os

CONFIG_FILE = Path(__file__).resolve().parent.parent.joinpath('config.yaml')

def conf_path() -> Path:
    return CONFIG_FILE

@dataclass
class App:
    id: str
    secret: str

@dataclass
class OauthTokens:
    access: Optional[str]
    refresh: Optional[str]
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
    app: App
    oauth_tokens: OauthTokens
    rdbms_connection_string: str
    conf: ClassVar[Optional[Config]] = None
    
    def has_tokens(self) -> bool:
        val = self.oauth_tokens is not None
        val = val and oauth_tokens.
    @staticmethod
    def build_type():
        bt = os.getenv('APP_ENV')
        valid_build_types = {"test", "production", "staging"}
        if bt is None or bt not in valid_build_types:
            raise ValueError(f"build type must be set to one of [{', '.join(valid_build_types)}] via the APP_ENV environment variable")
        return bt

    @staticmethod
    def data_dir():
        suff = {"production": "", "test": "/test", "staging": "/staging"}
        s = suff[Config.build_type()]
        return Path.home().joinpath(f"var/log/tctk{s}")

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
                Config.conf = Config(**yaml_dict)
                Config.conf.oauth_tokens.scopes = [AuthScope(s) for s in Config.conf.oauth_tokens.scopes]
        return Config.conf
