from dataclasses import dataclass
import yaml
from typing import ClassVar, Optional
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
class Config:
    app: App
    scopes: list[AuthScope]
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

    conf: ClassVar[Optional[Config]] = None

    def has_tokens(self):
        return self.access_token is not None

    def get_tokens(self):
        return (self.access_token, self.refresh_token)

    @staticmethod
    def backup():
        Config.conf = Config.get()
        d = dataclasses.asdict(Config.conf)
        d['scopes'] = [s.value for s in d['scopes']]
        with conf_path().with_suffix(".back").open('w') as f:
            yaml.dump(d, f)

    @staticmethod
    def persist_with(**kwargs):
        Config.conf = Config.get()
        d = dataclasses.asdict(Config.conf)
        d.update(kwargs)
        Config.conf = Config(**d)
        d['scopes'] = [s.value for s in d['scopes']]
        with conf_path().open('w') as f:
            yaml.dump(d, f)

    @staticmethod
    def get():
        if Config.conf is None:
            with conf_path().open() as f:
                yaml_dict: dict = yaml.safe_load(f)
                yaml_dict['app'] = App(**yaml_dict['app'])
                Config.conf = Config(**yaml_dict)
                Config.conf.scopes = [AuthScope(s) for s in yaml_dict['scopes']]
        return Config.conf
