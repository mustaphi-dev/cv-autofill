import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes every LogRecord has, plus uvicorn's terminal-colour copy of the
# message. Anything else was passed with `extra=`.
_STANDARD = set(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
    "color_message",
}


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Exceptions are logged by type only: their
    messages can carry request data (validation errors quote the input)."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **{k: v for k, v in vars(record).items() if k not in _STANDARD},
        }
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = record.exc_info[0].__name__
        return json.dumps(entry, default=str)


def setup() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

    # Stamp the request ID when a record is created, inside the request.
    make_record = logging.getLogRecordFactory()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = make_record(*args, **kwargs)
        record.request_id = request_id.get()
        return record

    logging.setLogRecordFactory(factory)

    uvicorn = logging.getLogger("uvicorn")
    uvicorn.handlers.clear()
    uvicorn.propagate = True
    # These log full URLs, query strings included. Our middleware logs instead.
    logging.getLogger("uvicorn.access").disabled = True
    for client in ("httpx", "httpx2"):
        logging.getLogger(client).setLevel(logging.WARNING)
