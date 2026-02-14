import io
import sys
import traceback
from pathlib import Path
from typing import Callable, Awaitable, Any, ParamSpec, Protocol
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
import atexit
import os
import signal
from enum import StrEnum, auto
from signal import Signals
from dataclasses import dataclass
from typing import TypedDict

class HandlerKwargs(TypedDict, total=False):
    signal: Signals
    update_reason: "UPDATE_REASON"
    message: str

class HandlerCallable(Protocol):
    def __call__(self, **kwargs: HandlerKwargs) -> Any:
        ...

class UPDATE_REASON(StrEnum):
    INIT_FILE = "INIT_FILE"
    REGULAR_UPDATE = "REGULAR_UPDATE"
    MAX_SIZE_REACHED = "MAX_SIZE_REACHED"
    NORMAL_SERVICE_SHUTDOWN = "NORMAL_SERVICE_SHUTDOWN"
    # Generic unknown placeholder (static member)
    OS_SIGNAL = "OS_SIGNAL"

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

def signal_handler(close_handler, unknown_handler):
    """Register signal handlers.

    Notes:
    - SIGKILL and SIGSTOP cannot be caught/handled and will raise OSError if
      registration is attempted; skip them.
    - Some signals are platform-specific; attempt registration and ignore
      failures.
    - Handlers are installed as callables accepting (signum, frame) so
      they match the interface expected by the signal module.
    """
    # Signals that cannot be caught
    uncatchable = {Signals.SIGKILL, Signals.SIGSTOP}

    def _make_close():
        def _handler(signum, frame):
            try:
                close_handler(signum)
            except Exception as e:
                print(f"signal_handler close_handler raised for {signum}: {e}", file=sys.stderr)
        return _handler

    def _make_unknown():
        def _handler(signum, frame):
            try:
                unknown_handler(signum)
            except Exception as e:
                print(f"signal_handler unknown_handler raised for {signum}: {e}", file=sys.stderr)
        return _handler

    # Attempt to register handlers for all enum members, skipping those that
    # are not catchable or that the platform refuses to register.
    for sig in Signals:
        if sig in uncatchable:
            # skip signals that cannot be handled
            continue
        try:
            if sig in (Signals.SIGINT, Signals.SIGTERM, Signals.SIGQUIT, Signals.SIGHUP, Signals.SIGABRT, Signals.SIGALRM, Signals.SIGSEGV):
                signal.signal(sig, _make_close())
            else:
                signal.signal(sig, _make_unknown())
        except (OSError, ValueError) as e:
            # Platform doesn't allow registering this signal; ignore.
            # Could log to stderr if desired.
            # print(f"Skipping registering handler for {sig}: {e}", file=sys.stderr)
            continue

    # Register atexit handler to call close_handler with a sentinel (-1)
    atexit.register(lambda: close_handler(-1))

LOG_DIR = Path.home().joinpath("var/log/tctk")
MINUTE = 60
HOUR = 60*60
MB = 1024*1024
class ActivityLogPersistence:
    def __init__(self, flush_every=MINUTE, max_file_size=5*MB):
        def close_handler(num: int):
            if num == -1:
                self.data['update_reason'] = UPDATE_REASON.NORMAL_SERVICE_SHUTDOWN
                with open("signal.err", "a") as f:
                    f.write("\n")
                    f.write("A 'normal' exit occurred")
                return
            else:
                self.data['os_signal'] = 'UNKNOWN'
                for s in Signals:
                    if s.value == num:
                        self.data['os_signal'] = s

                self.data['update_reason'] = UPDATE_REASON.OS_SIGNAL
                self.persist()

        def other_handler(*args, **kwargs):
            with open("signals.err", "a") as f:
                f.write(f"Unknown os signal: {args[0]}")

        signal_handler(close_handler, other_handler)
        self.flush_every = flush_every
        self.max_file_size = max_file_size
        self.new_file()

    def get_log_file(self) -> Path:
        return LOG_DIR.joinpath(f"activity_{self.data['start_time']}.json")

    def get_log_file_size(self) -> int:
        return self.get_log_file().stat().st_size  # raises if missing

    def is_file_max_size(self):
        return self.get_log_file_size() > self.max_file_size

    # THIS IS DESTRUCTIVE
    def new_file(self):
        now_ts = round(datetime.datetime.now().timestamp())
        self.data = {
            "start_time": now_ts,
            "last_updated_time": now_ts,
            "update_reason": UPDATE_REASON.INIT_FILE,
            "activity": [],
        }
        # Ensure the log directory exists before creating the file
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with self.get_log_file().open("w") as f:
            json.dump(self.data, f)

    def persist(self):
        """Persist current in-memory data to disk and mark a normal shutdown.
        This is called from ActivityLogFeature.on_exit()."""
        now_ts = round(datetime.datetime.now().timestamp())
        self.data['last_updated_time'] = now_ts
        self.data['end_time'] = now_ts
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with self.get_log_file().open("a") as f:
            json.dump(self.data, f)
        # clear buffered activity after persisting
        self.data['activity'] = []
        print("PROGRAM SHOULD BE EXITING NOW")

    def add(self, *args):
        self.data['activity'].append(args)
        if datetime.datetime.now().timestamp() - self.data['last_updated_time'] > self.flush_every:
            self.flush()

    def flush(self):
        full = self.is_file_max_size()
        now_ts = datetime.datetime.now().timestamp()
        self.data['last_updated_time'] = now_ts
        self.data['update_reason'] = UPDATE_REASON.REGULAR_UPDATE
        if full:
            self.data['update_reason'] = UPDATE_REASON.MAX_SIZE_REACHED
            self.data['end_time'] = now_ts
        with self.get_log_file().open("a") as f:
            json.dump(self.data, f)
        self.data['activity'] = []
        if full:
            self.new_file()


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