from __future__ import annotations

import pandas as pd

from src.database.db import connect

SEVERITY_RANK = {"CRITICAL": 4, "IMPORTANT": 3, "WATCH": 2, "INFO": 1}


def load_portfolio(settings, holdings):
    if not 1 <= len(holdings) <= 100:
        raise ValueError("Portfolio Radar supports 1–100 holdings")
    tickers = [item.ticker for item in holdings]
    placeholders = ",".join("?" for _ in tickers)
    query = f"""
    WITH latest AS (
      SELECT *, row_number() OVER(PARTITION BY ticker ORDER BY market_date DESC) AS rn
      FROM analysis_snapshots WHERE ticker IN ({placeholders})
    ), latest_events AS (
      SELECT e.*, CASE severity WHEN 'CRITICAL' THEN 4 WHEN 'IMPORTANT' THEN 3 WHEN 'WATCH' THEN 2 ELSE 1 END severity_rank,
             row_number() OVER(PARTITION BY e.ticker ORDER BY CASE severity WHEN 'CRITICAL' THEN 4 WHEN 'IMPORTANT' THEN 3 WHEN 'WATCH' THEN 2 ELSE 1 END DESC, change_type) AS rn
      FROM change_events e JOIN latest l ON e.ticker=l.ticker AND e.market_date=l.market_date AND l.rn=1
    ), event_counts AS (
      SELECT e.ticker,
        count(*) FILTER(WHERE e.severity IN ('WATCH','IMPORTANT','CRITICAL')) meaningful_count,
        count(*) FILTER(WHERE e.severity IN ('IMPORTANT','CRITICAL')) important_count,
        count(*) FILTER(WHERE e.change_type='MARKET_STAGE_CHANGED') stage_change_count
      FROM change_events e JOIN latest l ON e.ticker=l.ticker AND e.market_date=l.market_date AND l.rn=1 GROUP BY e.ticker
    )
    SELECT l.*, coalesce(c.meaningful_count,0) meaningful_count, coalesce(c.important_count,0) important_count,
      coalesce(c.stage_change_count,0) stage_change_count, e.severity key_risk_severity, e.explanation key_risk
    FROM latest l LEFT JOIN event_counts c USING(ticker) LEFT JOIN latest_events e ON l.ticker=e.ticker AND e.rn=1
    WHERE l.rn=1 ORDER BY l.ticker
    """
    with connect(settings.database) as db:
        result = db.execute(query, tickers).fetchdf()
    by_ticker = {str(row.ticker): row._asdict() for row in result.itertuples(index=False)}
    rows = []
    for item in holdings:
        data = by_ticker.get(item.ticker, {})
        close = data.get("close")
        profit = ((close / item.cost - 1) * 100) if close is not None and item.cost not in (None, 0) else None
        ma5, ma20, ma60 = data.get("ma5"), data.get("ma20"), data.get("ma60")
        ma_state = "資料不足"
        if all(pd.notna(x) for x in (ma5,ma20,ma60)):
            ma_state = "多頭排列" if ma5 > ma20 > ma60 else "空頭排列" if ma5 < ma20 < ma60 else "交錯"
        rows.append({"ticker":item.ticker, "name":item.name, "price":close, "cost":item.cost, "profit_pct":profit,
            "stage":data.get("market_stage"), "rsi":data.get("rsi14"), "structure":data.get("structure_state"),
            "ma":ma_state, "foreign_5d":data.get("foreign_5d"), "trust_5d":data.get("trust_5d"),
            "margin_20d_pct":data.get("margin_change_pct_20d"), "key_risk":data.get("key_risk"),
            "key_risk_severity":data.get("key_risk_severity"), "changed":bool(data.get("meaningful_count",0)),
            "important_count":int(data.get("important_count",0)), "stage_changed":bool(data.get("stage_change_count",0)),
            "quality":data.get("data_quality_status","NO_DATA"), "market_date":data.get("market_date")})
    return pd.DataFrame(rows)


def filter_portfolio(data, search="", stages=None, alert="全部", changed_only=False):
    result = data.copy()
    if search.strip():
        needle = search.strip().casefold()
        result = result[result.apply(lambda row: needle in str(row.ticker).casefold() or needle in str(row["name"]).casefold(), axis=1)]
    if stages:
        result = result[result.stage.isin(stages)]
    if alert == "有重要警示": result = result[result.important_count > 0]
    elif alert == "有任何變化": result = result[result.changed]
    elif alert == "資料品質警告": result = result[result.quality != "PASS"]
    if changed_only: result = result[result.changed]
    return result.reset_index(drop=True)
