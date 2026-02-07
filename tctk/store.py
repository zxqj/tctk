from typing import Any, ClassVar, Self, Type

import json
import polars as pl
from polars import DataFrame
from dataclasses import dataclass
import dataclasses
import pathlib

def get_data_file_path(cls):
    return pathlib.Path(f"{cls.__name__}.parquet")

def write(cls):
    cls.store.write_parquet(get_data_file_path(cls))

def read(cls):
    cls.store.read_parquet(get_data_file_path(cls))

def save[T](cls: Type[T], me: T):
    row = dataclasses.asdict(me)
    new = pl.DataFrame([row])
    cls.store = pl.concat([cls.store, new])
    write(cls)

@dataclass
class UserRaffle:
    username: str
    raffle_start_time: int
    did_win: bool
    join_time: int

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
    start_time: int
    duration: int
    amount: int

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

@dataclass
class Duel:
    initiator: pl.String
    opponent: pl.String
    offer_time: pl.UInt32
    accepted: pl.Boolean
    accepted_time: pl.UInt32
    won: pl.Boolean

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
        save(Duel, self)
