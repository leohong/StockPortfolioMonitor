from datetime import date, timedelta

import pandas as pd

from src.analysis.momentum.momentum import _divergence, calculate_momentum
from src.indicators.core import rsi_wilder
from src.models import PricePivot


def test_momentum_preserves_existing_wilder_rsi_definition():
    close = pd.Series([100+i*.2 for i in range(50)])
    data = pd.DataFrame({"ticker":["3702"]*50,"market_date":[date(2026,1,1)+timedelta(days=i) for i in range(50)],"close":close})
    result = calculate_momentum(data, [], "m3")
    expected = rsi_wilder(close)
    assert result[-1].rsi14 == expected.iloc[-1]
    assert result[-1].roc20 == (close.iloc[-1]/close.iloc[-21]-1)*100


def test_divergence_uses_only_confirmed_pivots_available_by_date():
    first = PricePivot(ticker="3702",pivot_date=date(2026,1,10),confirmation_date=date(2026,1,13),pivot_kind="LOW",price=90)
    second = PricePivot(ticker="3702",pivot_date=date(2026,1,20),confirmation_date=date(2026,1,23),pivot_kind="LOW",price=85)
    rsi = {first.pivot_date:30.0,second.pivot_date:40.0}
    assert _divergence(date(2026,1,22),[first,second],rsi) == (None,None,None)
    assert _divergence(date(2026,1,23),[first,second],rsi) == ("BULLISH",second.pivot_date,second.confirmation_date)
