from enum import auto, StrEnum
from typing import Any, ClassVar, Self, Type, Union, Iterable, TypeAlias, Callable, TypeVar

import dataclasses
import pathlib

import polars as pl
from polars import DataFrame, UInt8
from dataclasses import dataclass
from polars._typing import IntoExprColumn

from .config import Config

PolarsPredicate: TypeAlias = IntoExprColumn | Iterable[IntoExprColumn]

def get_data_file_path(cls):
    return pathlib.Path(f"{cls.__name__}.parquet")

def write(cls):
    cls.store.write_parquet(get_data_file_path(cls))

def read(cls):
    cls.store = pl.read_parquet(get_data_file_path(cls))

def save(cls, me):
    row = dataclasses.asdict(me)
    new = pl.DataFrame([row])
    cls.store = pl.concat([cls.store, new], rechunk=True)
    # persist to Postgres instead of parquet
    write_pg(cls)

def update(cls, predicate: PolarsPredicate, transform: Callable[[Any], Any]):
    # Placeholder: updates should be expressed via with_columns in Polars
    pass

@dataclass
class UserRaffle:
    username: str
    raffle_start_time: pl.UInt32
    did_win: pl.Booolean
    join_time: pl.UInt32

    @classmethod
    def load(cls):
        if get_data_file_path(cls).exists():
            read(cls)
        else:
            cls.store: DataFrame = DataFrame(schema={
                "username": pl.String,
                "raffle_start_time": pl.UInt32,
                "did_win": pl.Boolean,
                "join_time": pl.UInt32
            })

    def save(self):
        save(UserRaffle, self)

@dataclass
class Raffle:
    start_time: pl.UInt32
    duration: pl.UInt8
    amount: pl.UInt16

    @classmethod
    def load(cls):
        if get_data_file_path(cls).exists():
            read(cls)
        else:
            cls.store: DataFrame = DataFrame(schema={
                "start_time": pl.UInt32,
                "duration": pl.UInt8,
                "amount": pl.UInt16
            })

    def save(self):
        save(Raffle, self)

class DuelOfferOutcome(StrEnum):
    NotAccepted = auto()
    Denied = auto()
    Won = auto()
    Lost = auto()

class DuelOfferValidationError(StrEnum):
    SenderInsufficientCoins = auto()
    RecipientInsufficientCoins = auto()
    RecipientNotFound = auto()
    SenderOccupied = auto()
    RecipientOccupied = auto()

@dataclass
class Duel:
    initiator: pl.String
    opponent: pl.String
    amount: pl.UInt16
    offer_time: pl.UInt32
    accepted_time: pl.UInt32
    outcome: Union[DuelOfferOutcome, DuelOfferValidationError]

    @classmethod
    def load(cls):
        if get_data_file_path(cls).exists():
            read(cls)
        else:
            cls.store: DataFrame = DataFrame(schema={
                "initiator": pl.String,
                "opponent": pl.String,
                "amount": pl.UInt16,
                "offer_time": pl.UInt32,
                "accepted": pl.Boolean,
                "accepted_time": pl.UInt32,
                "won": pl.Boolean
            })

    def save(self):
        save(Duel, self)

# Define a clean Message model with Polars-compatible schema
class ClassVarDataFrame:
    pass


@dataclasses.dataclass
class Message:
    user_id: int
    user_name: str
    is_me: bool

    badges: list[str]
    color: str | None
    first_msg: bool
    mod: bool
    first: bool
    subscriber: bool

    room_id: int
    channel: str

    id: str
    text: str
    sent_timestamp: int
    reply_parent_id: str | None
    bits: int #?
    emotes: list[dict] | None
    hype_chat: str | None #?
    source_id: int | None #?


    store: ClassVar[DataFrame] = DataFrame(schema={
            "user_id": pl.UInt32,
            "user_name": pl.String,
            "is_me": pl.Boolean,
            "badges": pl.List(pl.Utf8),
            "color": pl.Utf8,
            "first_msg": pl.Boolean,
            "mod": pl.Boolean,
            "first": pl.Boolean,
            "subscriber": pl.Boolean,
            "room_id": pl.UInt32,
            "channel": pl.Utf8,
            "id": pl.Utf8,
            "text": pl.Utf8,
            "sent_timestamp": pl.UInt32,
            "reply_parent_id": pl.Utf8,
            "bits": pl.UInt16,
            "emotes": pl.List(pl.Struct({"id": pl.UInt32, "ranges": pl.List(pl.Struct({"start": pl.UInt16, "end": pl.UInt16}))})),
            "hype_chat": pl.Utf8,
            "source_id": pl.UInt32,
        })

    def save(self):
        if not hasattr(Message, 'store'):
            Message.init()
        save(Message, self)

# Database persistence using SQLAlchemy + pandas
def write_pg(cls):
    import pandas as pd
    from sqlalchemy import create_engine

    conf = Config.get()
    engine = create_engine(conf.rdbms_connection_string)
    df_pd = cls.store.to_pandas()
    # Table name: lowercased class name
    table_name = cls.__name__.lower()
    # Create or append
    df_pd.to_sql(table_name, con=engine, if_exists="append", index=False)
