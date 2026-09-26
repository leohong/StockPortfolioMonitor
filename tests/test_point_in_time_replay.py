from datetime import date, timedelta
import json

from src.analysis.market_state import build_evidence_vector, classify_market_state


def _row(day, state, source_day=None):
    return {"ticker": "3702", "market_date": day, "state": state,
        "ruleset_version": "source-v1", "source_dates_json": json.dumps([str(source_day or day)])}


def test_future_source_is_missing_in_historical_point_in_time_replay():
    day = date(2026, 1, 5)
    vector = build_evidence_vector("3702", day, {"structure": _row(day, "UPTREND_STRUCTURE", day + timedelta(days=1))}, "replay-v1")
    assert vector.dimensions["structure"].state == "INSUFFICIENT_DATA"
    assert "future_source_date_rejected" in vector.dimensions["structure"].missing_data


def test_same_as_of_inputs_replay_to_identical_historical_state():
    day = date(2026, 1, 5)
    components = {"structure": _row(day, "UPTREND_STRUCTURE"),
        "trend": _row(day, "TREND_HEALTHY"), "momentum": _row(day, "POSITIVE")}
    first = classify_market_state(build_evidence_vector("3702", day, components, "replay-v1"))
    second = classify_market_state(build_evidence_vector("3702", day, components, "replay-v1"))
    assert first.state == second.state == "S4_TREND"
    assert first.primary_evidence == second.primary_evidence
