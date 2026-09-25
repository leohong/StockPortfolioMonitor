import json
import logging
from datetime import datetime, timezone


def event(name: str, level: int = logging.INFO, **fields):
    logging.getLogger("dashboard").log(level, json.dumps({"event": name, "timestamp": datetime.now(timezone.utc).isoformat(), **fields}, ensure_ascii=False, default=str))


def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
