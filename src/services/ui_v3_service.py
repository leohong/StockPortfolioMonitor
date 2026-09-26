from __future__ import annotations

import json
import pandas as pd

from src.database.db import connect

M6_RULESET="m6-evidence-market-state-v1"
M7_RULESET="m7-significance-scenario-v1"
SIGNIFICANCE_RANK={"LOW":1,"MEDIUM":2,"HIGH":3,"CRITICAL":4}


def _snapshots(db,tickers):
    if not tickers: return []
    marks=','.join('?' for _ in tickers)
    rows=db.execute(f"SELECT ticker,market_date,data_quality_status,payload_json,created_at FROM snapshot_v3_daily WHERE ruleset_version='{M6_RULESET}' AND ticker IN ({marks}) QUALIFY row_number() OVER(PARTITION BY ticker ORDER BY market_date DESC)=1",tickers)
    return [{**dict(zip([c[0] for c in rows.description],row)),"payload":json.loads(row[3])} for row in rows.fetchall()]


def load_v3_portfolio(settings,holdings):
    tickers=[item.ticker for item in holdings]
    with connect(settings.database) as db:
        snapshots=_snapshots(db,tickers)
        marks=','.join('?' for _ in tickers) or "''"
        events=db.execute(f"SELECT ticker,market_date,significance,dimension,explanation FROM event_significance WHERE ruleset_version='{M7_RULESET}' AND ticker IN ({marks})",tickers).fetchall() if tickers else []
    names={item.ticker:item.name for item in holdings}; by_ticker={row["ticker"]:row for row in snapshots}; output=[]
    for ticker in tickers:
        row=by_ticker.get(ticker); payload={} if row is None else row["payload"]; day=None if row is None else row["market_date"]
        current=[event for event in events if event[0]==ticker and event[1]==day]
        highest=max((event[2] for event in current),key=lambda x:SIGNIFICANCE_RANK[x],default=None)
        output.append({"ticker":ticker,"name":names[ticker],"market_date":day,"close":payload.get("close"),
            "market_regime":payload.get("market_regime"),"sector_regime":payload.get("sector_regime"),
            "market_state":payload.get("market_state"),"relative_strength":payload.get("relative_strength_state"),
            "positioning":payload.get("positioning_state"),"volatility":payload.get("volatility_state"),
            "significant_change":bool(current),"highest_significance":highest,
            "quality":"NO_DATA" if row is None else row["data_quality_status"]})
    return pd.DataFrame(output)


def filter_v3_portfolio(data,search="",states=None,attention="全部",changed_only=False):
    result=data.copy()
    if search.strip():
        needle=search.strip().casefold(); result=result[result.apply(lambda row:needle in str(row.ticker).casefold() or needle in str(row["name"]).casefold(),axis=1)]
    if states: result=result[result.market_state.isin(states)]
    if attention=="HIGH／CRITICAL": result=result[result.highest_significance.isin(["HIGH","CRITICAL"])]
    elif attention=="資料品質警告": result=result[result.quality!="PASS"]
    if changed_only: result=result[result.significant_change]
    return result.reset_index(drop=True)


def load_v3_detail(settings,ticker,market_date=None):
    with connect(settings.database) as db:
        clause="ticker=? AND ruleset_version=?"; params=[ticker,M6_RULESET]
        if market_date is not None: clause+=" AND market_date<=?"; params.append(market_date)
        rows=db.execute(f"SELECT market_date,data_quality_status,payload_json,created_at FROM snapshot_v3_daily WHERE {clause} ORDER BY market_date DESC LIMIT 2",params).fetchall()
        if not rows: return None,None,[],[]
        snapshots=[{"market_date":row[0],"quality":row[1],"payload":json.loads(row[2]),"created_at":row[3]} for row in rows]
        day=snapshots[0]["market_date"]
        cursor=db.execute("SELECT dimension,previous_state,current_state,significance,reason_codes_json,explanation FROM event_significance WHERE ticker=? AND market_date=? AND ruleset_version=? ORDER BY CASE significance WHEN 'CRITICAL' THEN 4 WHEN 'HIGH' THEN 3 WHEN 'MEDIUM' THEN 2 ELSE 1 END DESC,dimension",[ticker,day,M7_RULESET])
        events=[dict(zip([c[0] for c in cursor.description],row)) for row in cursor.fetchall()]
        cursor=db.execute("SELECT scenario_type,name,current_status,conditions_json,confirmation_events_json,invalidation_events_json,relevant_levels_json,evidence_dependencies_json,interpretation FROM scenario_daily WHERE ticker=? AND market_date=? AND ruleset_version=? ORDER BY CASE scenario_type WHEN 'POSITIVE_CONTINUATION' THEN 1 WHEN 'NEUTRAL_UNRESOLVED' THEN 2 ELSE 3 END",[ticker,day,M7_RULESET])
        scenarios=[]
        for row in cursor.fetchall():
            item=dict(zip([c[0] for c in cursor.description],row))
            for field in ("conditions","confirmation_events","invalidation_events","relevant_levels","evidence_dependencies"): item[field]=json.loads(item.pop(field+"_json"))
            scenarios.append(item)
    return snapshots[0],snapshots[1] if len(snapshots)>1 else None,events,scenarios


def load_v3_timeline(settings,ticker,start=None,end=None):
    clauses=["ticker=?","ruleset_version=?"]; params=[ticker,M6_RULESET]
    if start is not None: clauses.append("market_date>=?"); params.append(start)
    if end is not None: clauses.append("market_date<=?"); params.append(end)
    with connect(settings.database) as db:
        rows=db.execute(f"SELECT market_date,payload_json,data_quality_status FROM snapshot_v3_daily WHERE {' AND '.join(clauses)} ORDER BY market_date",params).fetchall()
    result=[]
    for day,payload,quality in rows:
        item=json.loads(payload); result.append({"market_date":day,"market_state":item.get("market_state"),"structure":item.get("structure_state"),"trend":item.get("trend_state"),"quality":quality})
    data=pd.DataFrame(result)
    if not data.empty: data["state_changed"]=data.market_state.ne(data.market_state.shift()); data.loc[data.index[0],"state_changed"]=False
    return data


def compare_v3(settings,tickers):
    if not 2<=len(tickers)<=5 or len(set(tickers))!=len(tickers): raise ValueError("Comparison requires 2–5 unique holdings")
    with connect(settings.database) as db: rows=_snapshots(db,tickers)
    output=[]
    for row in rows:
        p=row["payload"]; output.append({"ticker":row["ticker"],"market_date":row["market_date"],"market_state":p.get("market_state"),
            "regime":p.get("market_regime"),"structure":p.get("structure_state"),"trend":p.get("trend_state"),
            "momentum":p.get("momentum_state"),"relative_strength":p.get("relative_strength_state"),
            "participation":p.get("participation_state"),"capital_flow":p.get("capital_flow_state"),
            "positioning":p.get("positioning_state"),"volatility":p.get("volatility_state"),"location":p.get("location_state")})
    return pd.DataFrame(output).sort_values("ticker") if output else pd.DataFrame()
