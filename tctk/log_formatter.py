import inspect
import json
import logging
import re
from pythonjsonlogger.jsonlogger import JsonFormatter

PINK = "\033[38;5;213m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RESET = "\033[0m"

_VARIABLE_RE = re.compile(r'\.variable\((.+)\)\s*$')


class TctkLogger(logging.Logger):
    def variable(self, val):
        if not self.isEnabledFor(logging.DEBUG):
            return
        frame = inspect.currentframe().f_back
        info = inspect.getframeinfo(frame)
        src = info.code_context[0].strip() if info.code_context else ""
        m = _VARIABLE_RE.search(src)
        name = m.group(1).strip() if m else "?"
        self.debug(f"({type(val).__name__}, {name}, {val})", stacklevel=2)


logging.setLoggerClass(TctkLogger)


class ColoredJsonFormatter(JsonFormatter):
    def jsonify_log_record(self, log_record: dict) -> str:
        if "exc_info" in log_record and isinstance(log_record["exc_info"], str):
            log_record["exc_info"] = log_record["exc_info"].split("\n")

        msg_val = log_record.get("message")
        result = json.dumps(log_record, indent=2)
        if msg_val is not None:
            encoded = json.dumps(msg_val)
            result = result.replace(
                f'"message": {encoded}',
                f'"message": {GREEN}{encoded}{RESET}',
                1,
            )

        exc_lines = log_record.get("exc_info")
        if isinstance(exc_lines, list) and len(exc_lines) > 0:
            n = min(4, len(exc_lines))
            targets = [json.dumps(line) for line in exc_lines[-n:]]
            targets.reverse()
            output_lines = result.split("\n")
            for i in range(len(output_lines) - 1, -1, -1):
                if not targets:
                    break
                if output_lines[i].strip().rstrip(",") == targets[0]:
                    output_lines[i] = f"{YELLOW}{output_lines[i]}{RESET}"
                    targets.pop(0)
            result = "\n".join(output_lines)

        return result

    def format(self, record: logging.LogRecord) -> str:
        result = super().format(record)
        if record.levelno >= logging.ERROR:
            return f"{PINK}{result}{RESET}"
        return result
