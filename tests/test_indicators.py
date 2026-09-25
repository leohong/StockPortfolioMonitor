import numpy as np
import pandas as pd
import pytest

from src.indicators.core import calculate, rsi_wilder
from src.database.db import frame


def test_moving_averages_and_inclusive_volume_ratio():
    # Synthetic mathematical sequence only in tests, never in production.
    data = pd.DataFrame({"close": range(1, 81), "volume": range(1, 81)})
    result = calculate(data)
    assert result.ma5.iloc[4] == 3
    assert result.ma20.iloc[19] == 10.5
    assert result.ma60.iloc[59] == 30.5
    assert result.ma60.iloc[:59].isna().all()
    assert result.volume_ma20.iloc[19] == 10.5
    assert result.volume_ratio_20.iloc[19] == pytest.approx(20 / 10.5)


@pytest.mark.parametrize("values,expected", [(range(30), 100), (range(30, 0, -1), 0), ([12] * 30, 50)])
def test_rsi_edges(values, expected):
    result = rsi_wilder(pd.Series(values, dtype=float))
    assert result.iloc[:14].isna().all()
    assert (result.iloc[14:] == expected).all()


def test_rsi_seed_and_recursive_update():
    # 7 gains of 2, 7 losses of 1: seed averages 1 and 0.5 -> RSI 66 2/3.
    prices = [100]
    for delta in [2, -1] * 7 + [4]:
        prices.append(prices[-1] + delta)
    rsi = rsi_wilder(pd.Series(prices))
    assert rsi.iloc[14] == pytest.approx(100 - 100 / 3)
    assert rsi.iloc[15] == pytest.approx(100 - 100 / (1 + 17 / 6.5))


def test_zero_volume_and_missing_close_stay_missing():
    data = pd.DataFrame({"close": [100.] * 40, "volume": [0] * 40})
    data.loc[20, "close"] = np.nan
    result = calculate(data)
    assert result.volume_ratio_20.isna().all()
    assert result.rsi14.iloc[20:35].isna().all()
    assert result.rsi14.iloc[35] == 50


def test_real_regression_and_no_future_dependency(real_rows):
    data = frame(real_rows)
    actual = calculate(data)
    assert actual.ma5.iloc[4] == pytest.approx(122.1)
    # First 14 deltas: gains=1.5+11.5+7.5+1+6.5=28; losses=33.
    assert actual.rsi14.iloc[14] == pytest.approx(100 * 28 / 61)
    pd.testing.assert_frame_equal(calculate(data.iloc[:16]), actual.iloc[:16])
