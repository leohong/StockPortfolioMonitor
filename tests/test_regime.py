from datetime import date, timedelta

import pandas as pd

from src.analysis.regime.market_regime import calculate_market_regimes, regime_as_of


def benchmark(direction=1, count=160):
    start = date(2026, 1, 1)
    closes = [100 + direction * index * .5 for index in range(count)]
    return pd.DataFrame({"market_date":[start+timedelta(days=index) for index in range(count)],
        "open":closes, "high":[x+1 for x in closes], "low":[x-1 for x in closes],
        "close":closes, "source":["official"]*count})


def test_market_regime_is_structured_and_missing_breadth_stays_missing():
    result = calculate_market_regimes(benchmark(), "m2-regime-v2")[-1]
    assert result.regime == "RISK_ON_EXTENDED"
    assert result.confidence_class == "CONFIRMED"
    assert result.evidence_for and "market_breadth" in result.missing_inputs
    assert result.source_dates == [result.market_date]


def test_risk_off_and_insufficient_history_are_explicit():
    assert calculate_market_regimes(benchmark(-1), "m2-regime-v2")[-1].regime == "RISK_OFF"
    short = calculate_market_regimes(benchmark(count=30), "m2-regime-v2")[-1]
    assert short.regime == "INSUFFICIENT_DATA" and short.confidence_class == "INSUFFICIENT"


def test_future_bars_do_not_change_as_of_regime():
    history = benchmark(count=150)
    as_of = history.market_date.iloc[139]
    before = regime_as_of(history.iloc[:140], as_of, "m2-regime-v2")
    future = benchmark(-1, 20)
    future["market_date"] = [history.market_date.iloc[-1] + timedelta(days=index+1) for index in range(len(future))]
    after = regime_as_of(pd.concat([history, future], ignore_index=True), as_of, "m2-regime-v2")
    assert before.model_dump(exclude={"created_at"}) == after.model_dump(exclude={"created_at"})
    assert all(day <= as_of for day in after.source_dates)
