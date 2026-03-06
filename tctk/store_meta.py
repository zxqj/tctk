# Python
import pathlib
import dataclasses
from dataclasses import dataclass, fields
import polars as pl

PY_TO_PL = {
    int: pl.Int64,
    float: pl.Float64,
    bool: pl.Boolean,
    str: pl.String,
    bytes: pl.Binary,
}

def _schema_from_dataclass(cls) -> dict[str, pl.DataType]:
    schema: dict[str, pl.DataType] = {}
    for f in fields(cls):
        ann = f.type
        # Accept direct Polars dtypes (e.g. pl.UInt32) or map Python types
        if isinstance(ann, pl.DataType):
            schema[f.name] = ann
        elif ann in PY_TO_PL:
            schema[f.name] = PY_TO_PL[ann]
        else:
            # Fallback to String if unknown
            schema[f.name] = pl.String
    return schema

def _data_file_path(cls) -> pathlib.Path:
    return pathlib.Path(f"{cls.__name__}.parquet")

class StoreMeta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)

        # Only apply to dataclasses
        if not dataclasses.is_dataclass(cls):
            return cls

        # Create empty store with schema
        schema = _schema_from_dataclass(cls)
        cls.store = pl.DataFrame(schema=schema)

        # Inject load
        def load(cls_):
            path = _data_file_path(cls_)
            if path.exists():
                cls_.store = pl.read_parquet(path)
            else:
                cls_.store = pl.DataFrame(schema=_schema_from_dataclass(cls_))
        cls.load = classmethod(load)

        # Inject save (append row and write parquet)
        def save(self):
            row = dataclasses.asdict(self)
            df_new = pl.DataFrame([row])
            type(self).store = pl.concat([type(self).store, df_new], rechunk=True)
            type(self).store.write_parquet(_data_file_path(type(self)))
        cls.save = save

        return cls