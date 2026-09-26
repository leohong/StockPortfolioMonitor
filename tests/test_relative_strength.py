from datetime import date, timedelta

import pandas as pd

from src.analysis.relative_strength.relative_strength import calculate_relative_strength


def frames(count=140):
    dates=[date(2026,1,1)+timedelta(days=i) for i in range(count)]
    stock=pd.DataFrame({"ticker":["3702"]*count,"market_date":dates,
        "close":[100+i for i in range(count)],"source_note":["X0.00" if i==30 else "" for i in range(count)]})
    benchmark=pd.DataFrame({"market_date":dates,"close":[100+i*.5 for i in range(count)]})
    return stock,benchmark


def test_market_relative_strength_20_60_120_matches_manual_returns():
    stock,benchmark=frames(); result=calculate_relative_strength(stock,benchmark,"m3",leading_20d_pct=.1,leading_60d_pct=.1)[-1]
    i=len(stock)-1
    for window,actual in ((20,result.rs_market_20d),(60,result.rs_market_60d),(120,result.rs_market_120d)):
        expected=(stock.close.iloc[i]/stock.close.iloc[i-window]-1)*100-(benchmark.close.iloc[i]/benchmark.close.iloc[i-window]-1)*100
        assert abs(actual-expected)<1e-12
    assert result.state == "LEADING"
    assert result.rs_sector_20d is None and "sector_benchmark" in result.missing_inputs
    assert result.price_basis == "UNADJUSTED" and result.corporate_action_warning


def test_missing_benchmark_date_does_not_forward_fill_or_fabricate_rs():
    stock,benchmark=frames(); missing_day=stock.market_date.iloc[-1]
    benchmark=benchmark[benchmark.market_date != missing_day]
    result=calculate_relative_strength(stock,benchmark,"m3")[-1]
    assert result.state == "INSUFFICIENT_DATA"
    assert result.benchmark_date is None and result.rs_line is None
    assert "benchmark_date_alignment" in result.missing_inputs


def test_future_data_does_not_change_historical_relative_strength():
    stock,benchmark=frames(); before=calculate_relative_strength(stock.iloc[:130],benchmark.iloc[:130],"m3")[-1]
    after=calculate_relative_strength(stock,benchmark,"m3")[129]
    assert before.model_dump(exclude={"created_at"}) == after.model_dump(exclude={"created_at"})
