from typing import Any, ClassVar, Self, Type

import polars as pl
from polars import DataFrame
from dataclasses import dataclass
import dataclasses


def save[T](cls: Type[T], me: T):
    row = dataclasses.asdict(me)
    new = pl.DataFrame([row])
    cls.store = pl.concat([cls.store, new])

@dataclass
class UserRaffle:
    username: str
    raffle_start_time: int
    did_win: bool
    join_time: int

    store: ClassVar[DataFrame] = DataFrame(schema={
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

    store: ClassVar[DataFrame] = DataFrame(schema={
        "start_time": pl.UInt32,
        "duration": pl.UInt8,
        "amount": pl.UInt16
    })

    def save(self):
        save(Raffle, self)
