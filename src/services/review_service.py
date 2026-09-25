from __future__ import annotations

import json
import pandas as pd

from src.database.db import connect, read_evidence


def load_timeline(settings, ticker, start=None, end=None):
    clauses, params = ["ticker=?"], [ticker]
    if start is not None: clauses.append("market_date>=?"); params.append(start)
    if end is not None: clauses.append("market_date<=?"); params.append(end)
    where = " AND ".join(clauses)
    with connect(settings.database) as db:
        snapshots = db.execute(f"SELECT * FROM analysis_snapshots WHERE {where} ORDER BY market_date",params).fetchdf()
        events = db.execute(f"SELECT * FROM change_events WHERE {where} ORDER BY market_date,change_type",params).fetchdf()
    if not snapshots.empty:
        snapshots["stage_changed"] = snapshots.market_stage.ne(snapshots.market_stage.shift())
        snapshots.loc[snapshots.index[0],"stage_changed"] = False
    return snapshots, events


def historical_review(settings, ticker, market_date):
    with connect(settings.database) as db:
        snapshot = db.execute("SELECT * FROM analysis_snapshots WHERE ticker=? AND market_date=?",[ticker,market_date]).fetchdf()
        events = db.execute("SELECT * FROM change_events WHERE ticker=? AND market_date=? ORDER BY change_type",[ticker,market_date]).fetchdf()
        evidence = read_evidence(db,ticker,market_date)
    if snapshot.empty:
        return None, events, evidence
    if any(source_date > market_date for item in evidence for source_date in item.source_dates):
        raise ValueError("Historical evidence contains a future source date")
    return snapshot.iloc[0], events, evidence


def compare_holdings(settings, tickers):
    if not 2 <= len(tickers) <= 5 or len(set(tickers)) != len(tickers):
        raise ValueError("Comparison requires 2–5 unique holdings")
    placeholders = ",".join("?" for _ in tickers)
    query = f"""
    WITH history AS (
      SELECT *, lag(close,20) OVER(PARTITION BY ticker ORDER BY market_date) close_20d,
        row_number() OVER(PARTITION BY ticker ORDER BY market_date DESC) rn
      FROM analysis_snapshots WHERE ticker IN ({placeholders})
    ) SELECT ticker,market_date,market_stage,rsi14,
      (close/close_20d-1)*100 return_20d_pct,
      (close/ma20-1)*100 distance_ma20_pct,volume_ratio_20,foreign_5d,foreign_20d,
      trust_5d,trust_20d,margin_change_pct_20d,
      (close/support_1-1)*100 distance_support_pct,
      (resistance_1/close-1)*100 distance_resistance_pct
    FROM history WHERE rn=1 ORDER BY ticker
    """
    with connect(settings.database) as db:
        return db.execute(query,tickers).fetchdf()


def load_data_quality(settings, tickers):
    if not tickers: return pd.DataFrame(), []
    placeholders = ",".join("?" for _ in tickers)
    query = f"""
    SELECT ticker,'行情' dataset,max(market_date) latest_date,arg_max(source,market_date) AS "source",
      sum(CASE WHEN close IS NULL OR volume IS NULL THEN 1 ELSE 0 END) missing,max(retrieved_at) retrieved
      FROM ohlcv_daily WHERE ticker IN ({placeholders}) GROUP BY ticker
    UNION ALL SELECT ticker,'法人',max(market_date),arg_max(source,market_date),
      sum(CASE WHEN foreign_net IS NULL OR investment_trust_net IS NULL OR dealer_net IS NULL THEN 1 ELSE 0 END),max(retrieved_at)
      FROM institutional_daily WHERE ticker IN ({placeholders}) GROUP BY ticker
    UNION ALL SELECT ticker,'融資融券',max(market_date),arg_max(source,market_date),
      sum(CASE WHEN margin_balance IS NULL OR short_balance IS NULL THEN 1 ELSE 0 END),max(retrieved_at)
      FROM margin_daily WHERE ticker IN ({placeholders}) GROUP BY ticker
    ORDER BY ticker,dataset
    """
    params = tickers * 3
    with connect(settings.database) as db:
        data = db.execute(query,params).fetchdf()
        snapshot_quality = dict(db.execute(f"SELECT ticker,arg_max(data_quality_status,market_date) FROM analysis_snapshots WHERE ticker IN ({placeholders}) GROUP BY ticker",tickers).fetchall())
        cursor = db.execute(f"SELECT ticker,checked_at,status,details_json FROM data_quality_events WHERE ticker IN ({placeholders}) ORDER BY checked_at DESC",tickers)
        audits = [dict(zip([x[0] for x in cursor.description],row)) for row in cursor.fetchall()]
    latest_audit = {}
    for item in audits:
        latest_audit.setdefault(item["ticker"],item)
    if not data.empty:
        data["status"] = data.apply(lambda row: snapshot_quality.get(row.ticker,"UNKNOWN") if row.dataset=="行情" else latest_audit.get(row.ticker,{}).get("status","UNKNOWN"),axis=1)
        data["conflicts"] = data.ticker.map(lambda x: sum("revision" in text.lower() or "conflict" in text.lower()
            for audit in audits if audit["ticker"]==x for text in json.loads(audit["details_json"]).get("warnings",[])))
    return data, audits
