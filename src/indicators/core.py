import numpy as np
import pandas as pd


def rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder SMA seed over first 14 deltas, then recursive smoothing.

    Flat gain/loss = 50; loss-only = 0; gain-only = 100. Gaps restart warmup.
    """
    if period < 1:
        raise ValueError("period must be positive")
    output = pd.Series(np.nan, index=close.index, dtype=float)
    gains, losses = [], []
    avg_gain = avg_loss = None
    previous = None
    for i, value in enumerate(close):
        if pd.isna(value):
            previous, avg_gain, avg_loss = None, None, None
            gains, losses = [], []
            continue
        if previous is not None:
            delta = value - previous
            gain, loss = max(delta, 0), max(-delta, 0)
            if avg_gain is None:
                gains.append(gain)
                losses.append(loss)
                if len(gains) == period:
                    avg_gain, avg_loss = sum(gains) / period, sum(losses) / period
            else:
                avg_gain = (avg_gain * (period - 1) + gain) / period
                avg_loss = (avg_loss * (period - 1) + loss) / period
            if avg_gain is not None:
                output.iloc[i] = (50 if avg_gain == 0 else 100) if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
        previous = value
    return output


def calculate(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    for window in (5, 20, 60):
        result[f"ma{window}"] = result.close.rolling(window, min_periods=window).mean()
    result["rsi14"] = rsi_wilder(result.close)
    result["volume_ma20"] = result.volume.rolling(20, min_periods=20).mean()
    result["volume_ratio_20"] = result.volume / result.volume_ma20.replace(0, np.nan)
    return result
