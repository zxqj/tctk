import io
import sys
import traceback
from pathlib import Path
from typing import Callable, Awaitable, Any
import datetime
from tctk import BotFeature
import json
from twitchAPI.chat import EventData
from twitchAPI.type import ChatEvent

import json
import dataclasses
import datetime
import enum
import base64
from typing import Any, Set

def serialize_to_json(obj: Any, *, indent: int = 0, sort_keys: bool = False, ensure_ascii: bool = False) -> str:
    seen: Set[int] = set()

    def _make_serializable(o: Any):
        oid = id(o)
        if oid in seen:
            return "<recursion>"
        # primitives
        if o is None or isinstance(o, (str, int, float, bool)):
            return o
        # mark as seen for compound objects
        seen.add(oid)

        try:
            # dataclasses
            if dataclasses.is_dataclass(o):
                result = {k: _make_serializable(v) for k, v in dataclasses.asdict(o).items()}
                return result
            # enums
            if isinstance(o, enum.Enum):
                return o.value
            # datetimes
            if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
                return o.isoformat()
            # bytes -> base64
            if isinstance(o, (bytes, bytearray)):
                return base64.b64encode(bytes(o)).decode("ascii")
            # mappings
            if isinstance(o, dict):
                return {str(k): _make_serializable(v) for k, v in o.items()}
            # iterables
            if isinstance(o, (list, tuple, set, frozenset)):
                return [_make_serializable(v) for v in o]
            # prefer explicit serializer method
            if hasattr(o, "to_dict") and callable(getattr(o, "to_dict")):
                return _make_serializable(o.to_dict())
            # fallback to __dict__
            if hasattr(o, "__dict__"):
                return _make_serializable(vars(o))
        finally:
            # keep object id in seen to avoid infinite recursion on repeated visits
            pass

        # last resort
        return repr(o)

    serializable = _make_serializable(obj)
    return json.dumps(serializable, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)

def describe_exception(exc) -> str:
    writer = io.StringIO()
    exc_type, exc_obj, exc_tb = sys.exc_info()
    writer.writelines(traceback.format_exception(exc_type, exc_obj, exc_tb))
    writer.writelines([
        str(exc),
        f"Error Type: {exc_type.__name__}",
        f"File Name: {exc_tb.tb_frame.f_code.co_filename}",
        f"Line Number: {exc_tb.tb_lineno}"])
    writer.seek(0)
    return writer.read()

LOG_DIR = Path.home().joinpath("var/log/tctk")
HOUR = 60*60
class ActivityLogPersistence:
    def __init__(self, flush_every=4*HOUR):
        self.flush_every = flush_every
        self.data = {
            "start_time": round(datetime.datetime.now().timestamp()),
            "activity": [],
        }

    def add(self, *args):
        if datetime.datetime.now().timestamp() - self.data['start_time'] > self.flush_every:
            self.persist()
        self.data['activity'].append(args)
    def persist(self):
        self.data['end_time'] = round(datetime.datetime.now().timestamp())
        with LOG_DIR.joinpath(f"activity_{self.data['end_time']}.json").open("w") as f:
            json.dump(self.data, f)

        self.data = {
            "start_time": round(datetime.datetime.now().timestamp()),
            "activity": [],
        }

def pp(s: str, *, indent: int = 2, sort_keys: bool = False, ensure_ascii: bool = False) -> str:
    """
    Return a pretty-printed JSON string from a compact JSON string `s`.
    """
    obj = json.loads(s)
    return json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)

def format_datetime(dt: datetime.datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Return an absolute, human-readable timestamp using strftime."""
    return dt.strftime(fmt)

class ActivityLogFeature(BotFeature):

    def on_start(self):
        print("Activity log started")
        self.persistence = ActivityLogPersistence()

    def on_exit(self):
        self.persistence.persist()

    async def catch_all(self, evt: ChatEvent, event_data: EventData):
        delattr(event_data, "chat")
        delete_attrs = ["cached_room"]

        for atr in delete_attrs:
            if hasattr(event_data, atr):
                delattr(event_data, atr)

        try:
            s = serialize_to_json(event_data)
            self.persistence.add(evt.value, datetime.datetime.now().timestamp(), s)
            print(format_datetime(datetime.datetime.now()))
            print(evt)
            print(pp(s))
            print()
        except Exception as e:
            print(describe_exception(e))

    def get_subscriptions(self):
        def handler_add_evt_name(chat_evt: ChatEvent):
            async def f(*args, **kwargs):
                await self.catch_all(chat_evt, args[0])
            return f
        return [(c, handler_add_evt_name(c)) for c in ChatEvent]