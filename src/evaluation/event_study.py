from __future__ import annotations

from src.database.db import connect

HORIZONS = (5, 10, 20, 60)


def _label(dimension, current):
    named = {
        ("location", "BREAKOUT_ZONE"): "confirmed_breakout",
        ("location", "BREAKDOWN_ZONE"): "support_break",
        ("relative_strength", "IMPROVING"): "rs_improvement",
        ("capital_flow", "REVERSING_POSITIVE"): "capital_flow_reversal_positive",
        ("capital_flow", "REVERSING_NEGATIVE"): "capital_flow_reversal_negative",
        ("positioning", "LEVERAGE_EXPANDING"): "margin_acceleration",
        ("volatility", "SHOCK"): "volatility_shock",
    }
    return named.get((dimension, current), f"{dimension}:{current}")


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    return None if not n else ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2


def event_study(settings, ticker: str) -> list[dict]:
    """Descriptive forward distributions. These are associations, not forecasts."""
    with connect(settings.database) as db:
        prices = db.execute("SELECT market_date,close FROM ohlcv_daily WHERE ticker=? ORDER BY market_date", [ticker]).fetchall()
        events = db.execute("SELECT market_date,dimension,current_state FROM event_significance "
            "WHERE ticker=? AND ruleset_version='m7-significance-scenario-v1' ORDER BY market_date", [ticker]).fetchall()
    index = {day: position for position, (day, _) in enumerate(prices)}
    samples = {}
    for day, dimension, current in events:
        start = index.get(day)
        if start is None or not prices[start][1]:
            continue
        label = _label(dimension, current)
        for horizon in HORIZONS:
            end = start + horizon
            if end >= len(prices):
                continue
            base = prices[start][1]
            future = [row[1] for row in prices[start + 1:end + 1] if row[1] is not None]
            if len(future) != horizon:
                continue
            forward_return = (prices[end][1] / base - 1) * 100
            drawdown = (min(future) / base - 1) * 100
            samples.setdefault((label, horizon), []).append((forward_return, drawdown))
    output = []
    for (label, horizon), values in sorted(samples.items()):
        returns = [item[0] for item in values]
        drawdowns = [item[1] for item in values]
        output.append({"event": label, "horizon": horizon, "sample_count": len(values),
            "mean_return_pct": sum(returns) / len(returns), "median_return_pct": _median(returns),
            "positive_hit_rate": sum(value > 0 for value in returns) / len(returns),
            "mean_drawdown_pct": sum(drawdowns) / len(drawdowns), "worst_drawdown_pct": min(drawdowns),
            "interpretation": "descriptive historical association; not a probability or forecast"})
    return output
