import logging

from src.logging_config import configure_logging, event


def test_debug_fetch_events_are_quiet_at_normal_level(caplog):
    configure_logging()
    with caplog.at_level(logging.INFO, logger="dashboard"):
        event("DATA_FETCH_START", level=logging.DEBUG, market_date="2026-09-24")
        event("DATA_FETCH_PROGRESS", completed=25, total=250)
    assert "DATA_FETCH_START" not in caplog.text
    assert "DATA_FETCH_PROGRESS" in caplog.text
