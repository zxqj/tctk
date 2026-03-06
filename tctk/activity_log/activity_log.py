from tctk.activity_log.persistence import describe_exception, ActivityLogPersistence
from tctk import BotFeature
from tctk.store import Message
from twitchAPI.chat import EventData, ChatMessage
from twitchAPI.type import ChatEvent

import json
import dataclasses
import datetime
import enum
import base64
from typing import Any, Set, Union


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


def pp(evt: ChatEvent, obj: EventData, full_json: str):
    """
    Return a pretty-printed JSON string from a compact JSON string `s`.
    """
    output = dict()
    if evt == ChatEvent.MESSAGE:
        msg_obj: ChatMessage = obj
        output['id'] = msg_obj.id
        output['user.name'] = msg_obj.user.name
        output['sent_timestamp'] = msg_obj.sent_timestamp
        output['text'] = msg_obj.text
        return json.dumps(output, indent=2)
    else:
        return full_json


def format_datetime(dt: datetime.datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Return an absolute, human-readable timestamp using strftime."""
    return dt.strftime(fmt)

class ActivityLogFeature(BotFeature):

    def on_start(self):
        print("Activity log started")
        self.persistence = ActivityLogPersistence()

    def on_exit(self):
        self.persistence.persist()

    async def catch_all(self, evt: ChatEvent, event_data: Union[EventData|Message]):
        if evt == ChatEvent.MESSAGE:
            message: Message = event_data
            message.save()
        try:
            s = serialize_to_json(event_data)
            self.persistence.add(evt.value, datetime.datetime.now().timestamp(), s)
            print(format_datetime(datetime.datetime.now()))
            print(evt)
            print(pp(evt, event_data, s))
            print()
        except Exception as e:
            print(describe_exception(e))

    def get_subscriptions(self):
        def handler_add_evt_name(chat_evt: ChatEvent):
            async def f(*args, **kwargs):
                await self.catch_all(chat_evt, args[0])
            return f
        return [(c, handler_add_evt_name(c)) for c in ChatEvent]