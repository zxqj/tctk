import logging
from pythonjsonlogger.jsonlogger import JsonFormatter

PINK = "\033[38;5;213m"
RESET = "\033[0m"


class ColoredJsonFormatter(JsonFormatter):
    def format(self, record: logging.LogRecord) -> str:
        result = super().format(record)
        if record.levelno >= logging.ERROR:
            return f"{PINK}{result}{RESET}"
        return result
