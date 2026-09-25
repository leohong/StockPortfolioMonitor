import json
import logging
from datetime import datetime, timezone


def event(name: str, **fields):
    logging.getLogger("dashboard").info(json.dumps({"event": name, "timestamp": datetime.now(timezone.utc).isoformat(), **fields}, ensure_ascii=False, default=str))


def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
