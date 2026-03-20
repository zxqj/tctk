from dataclasses import dataclass
from enum import StrEnum, auto
from logging import Logger
import yaml
from typing import ClassVar, Optional, Callable, Self
import dataclasses
from pathlib import Path
import logging
import logging.config
from twitchAPI.type import AuthScope
import os

PROJECT_DIR = Path(__file__).resolve().parent.parent

def conf_path() -> Path:
    return PROJECT_DIR.joinpath('config.yaml')

def logging_conf_path() -> Path:
    return PROJECT_DIR.joinpath("logging.yaml")
@dataclass
class App:
    id: str
    secret: str

@dataclass
class MessageTemplates:
    raffle_open: str
    duel_complete: str
    duel_complete_irc: str
    duel_proposed: str
    give: str

class Command(StrEnum):
    give = auto()
    raffle_join = "join"
    duel = auto()

    #my commands
    rinse = auto()
    withdraw = auto()

    def __str__(self):
        return f"!{self.value}"

    def __call__(self, *args):
        l = [str(self), *[str(arg) for arg in args]]
        return " ".join(l)

@dataclass
class Config:
    app: App
    scopes: list[AuthScope]
    rdbms_connection_string: str
    auto_timeout_words: str
    default_raffle_bot_user: str
    channel: str
    max_duel_amt: int = 2500
    conf: ClassVar[Optional[Config]] = None
    log_conf_loaded: ClassVar[bool] = False

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
        with conf_path().with_suffix(".back").open('w') as f:
            yaml.dump(d, f)

    @staticmethod
    def persist_with(update: Callable[[Config], None]):
        Config.conf = Config.get()
        update(Config.conf)
        d = dataclasses.asdict(Config.conf)
        with conf_path().open('w') as f:
            yaml.dump(d, f)

    @staticmethod
    def get() -> Self:
        if Config.conf is None:
            with conf_path().open() as f:
                yaml_dict: dict = yaml.safe_load(f)
                yaml_dict['app'] = App(**yaml_dict['app'])
                Config.conf = Config(**yaml_dict)
                Config.conf.scopes = [AuthScope(s) for s in Config.conf.scopes]
        return Config.conf

    @staticmethod
    def logger(module: str, reload: bool = False) -> Logger:
        def configure_logging():
            with logging_conf_path().open("r") as f:
                config = yaml.safe_load(f.read())
                logging.config.dictConfig(config)
        if reload or not Config.log_conf_loaded:
            configure_logging()
            Config.log_conf_loaded = True
        return logging.getLogger(__name__)