from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json

from src.analysis.momentum.momentum import calculate_momentum
from src.analysis.relative_strength.relative_strength import calculate_relative_strength
from src.analysis.trend.trend_quality import calculate_trend_quality
from src.analysis.versioning import V3_RULESET_VERSION, register_analysis_version, version_record
from src.analysis.participation import calculate_participation
from src.analysis.flow import calculate_capital_flow
from src.analysis.positioning import calculate_positioning
from src.analysis.volatility import calculate_volatility
from src.analysis.location import calculate_location
from src.analysis.market_state import build_evidence_vector, classify_market_state
from src.analysis.significance import detect_significant_events
from src.analysis.scenario import build_scenarios
from src.config import load_config
from src.database.db import connect, frame, read_institutional, read_margin, read_pivots
from src.database.v3 import (persist_momentum_states, persist_relative_strength, persist_trend_quality,
                             persist_participation, persist_capital_flow, persist_positioning, read_benchmark,
                             persist_volatility, persist_anchored_vwap, persist_location_zones, persist_location_states)
from src.database.v3 import persist_evidence_vectors, persist_market_states
from src.database.v3 import persist_significant_events,persist_scenarios
from src.models_v3 import EvidenceVectorV3,MarketStateV3,V3SnapshotEnvelope
from src.snapshots.v3_snapshot import persist_v3_snapshot
from src.services.stock_service import load_stock


def refresh_m3(settings, ticker: str, git_commit: str):
    stock, quality = load_stock(settings, ticker)
    if quality.status == "FAIL" or stock.empty:
        raise ValueError("M3 requires validated V2 stock history")
    with connect(settings.database) as db:
        benchmark = read_benchmark(db)
        pivots = read_pivots(db, ticker)
    if benchmark.empty:
        raise ValueError("M3 requires M2 official benchmark history")
    trend = calculate_trend_quality(stock, V3_RULESET_VERSION,
        extended_distance_pct=settings.trend_extended_distance_pct,
        persistence_min=settings.trend_persistence_min)
    momentum = calculate_momentum(stock, pivots, V3_RULESET_VERSION)
    relative_strength = calculate_relative_strength(stock, benchmark, V3_RULESET_VERSION,
        leading_20d_pct=settings.rs_leading_20d_pct, leading_60d_pct=settings.rs_leading_60d_pct)
    version = version_record(git_commit, settings)
    with connect(settings.database) as db:
        register_analysis_version(db, version)
        persist_trend_quality(db, trend)
        persist_momentum_states(db, momentum)
        persist_relative_strength(db, relative_strength)
    return trend[-1], momentum[-1], relative_strength[-1]


def refresh_m4(settings, ticker: str, git_commit: str):
    stock, quality = load_stock(settings, ticker)
    if quality.status == "FAIL" or stock.empty:
        raise ValueError("M4 requires validated V2 stock history")
    with connect(settings.database) as db:
        institutional=frame(read_institutional(db,ticker))
        margin=frame(read_margin(db,ticker))
    if institutional.empty or margin.empty:
        raise ValueError("M4 requires validated V2 institutional and margin history")
    participation=calculate_participation(stock,V3_RULESET_VERSION,
        confirm_ratio=settings.participation_confirm_ratio,strong_ratio=settings.participation_strong_ratio,
        abnormal_ratio=settings.participation_abnormal_ratio)
    flows=calculate_capital_flow(institutional,V3_RULESET_VERSION,persistence_ratio=settings.flow_persistence_ratio)
    positioning=calculate_positioning(stock,margin,V3_RULESET_VERSION,
        expansion_pct=settings.positioning_margin_expansion_pct,crowded_pct=settings.positioning_crowded_margin_pct,
        deleveraging_pct=settings.positioning_deleveraging_pct)
    version=version_record(git_commit,settings)
    with connect(settings.database) as db:
        register_analysis_version(db,version)
        persist_participation(db,participation)
        persist_capital_flow(db,flows)
        persist_positioning(db,positioning)
    latest_day=participation[-1].market_date
    return participation[-1],[item for item in flows if item.market_date==latest_day],positioning[-1]


def refresh_m5(settings,ticker:str,git_commit:str):
    stock,quality=load_stock(settings,ticker)
    if quality.status=="FAIL" or stock.empty: raise ValueError("M5 requires validated V2 stock history")
    with connect(settings.database) as db: pivots=read_pivots(db,ticker)
    volatility=calculate_volatility(stock,V3_RULESET_VERSION,compressed=settings.volatility_compressed_percentile,
        expanding=settings.volatility_expanding_percentile,high=settings.volatility_high_percentile,
        shock_range=settings.volatility_shock_range_ratio)
    avwaps,zones,locations=calculate_location(stock,pivots,V3_RULESET_VERSION,tolerance_pct=settings.level_tolerance_pct,
        near_pct=settings.location_near_pct,at_pct=settings.location_at_pct)
    version=version_record(git_commit,settings)
    with connect(settings.database) as db:
        register_analysis_version(db,version); persist_volatility(db,volatility); persist_anchored_vwap(db,avwaps)
        persist_location_zones(db,zones); persist_location_states(db,locations)
    latest=locations[-1].market_date
    return volatility[-1],[x for x in avwaps if x.market_date==latest],[x for x in zones if x.market_date==latest],locations[-1]


def _history(db,table,ticker,state_key=None,versioned=True):
    if not versioned:
        cursor=db.execute(f"SELECT * FROM {table} WHERE ticker=? ORDER BY market_date",[ticker])
        names=[column[0] for column in cursor.description]
        return [dict(zip(names,row)) for row in cursor.fetchall()]
    partition="market_date" if state_key is None else f"market_date,{state_key}"
    cursor=db.execute(f"SELECT * FROM {table} WHERE ticker=? QUALIFY row_number() OVER (PARTITION BY {partition} ORDER BY created_at DESC)=1 ORDER BY market_date",[ticker])
    names=[column[0] for column in cursor.description]
    return [dict(zip(names,row)) for row in cursor.fetchall()]


def _by_date(rows): return {row["market_date"]:row for row in rows}


def refresh_m6(settings,ticker:str,git_commit:str):
    with connect(settings.database) as db:
        prices=_history(db,"ohlcv_daily",ticker,versioned=False)
        components={
            "structure":_by_date(_history(db,"structure_snapshots",ticker,versioned=False)),
            "trend":_by_date(_history(db,"trend_quality_daily",ticker)),
            "momentum":_by_date(_history(db,"momentum_state_daily",ticker)),
            "relative_strength":_by_date(_history(db,"relative_strength_daily",ticker)),
            "participation":_by_date(_history(db,"participation_daily",ticker)),
            "positioning":_by_date(_history(db,"positioning_daily",ticker)),
            "volatility":_by_date(_history(db,"volatility_daily",ticker)),
            "location":_by_date(_history(db,"location_state_daily",ticker)),
        }
        flows=_history(db,"capital_flow_daily",ticker,"participant")
        flow_by_date={day:[row for row in flows if row["market_date"]==day] for day in {row["market_date"] for row in flows}}
        cursor=db.execute("SELECT * FROM regime_daily WHERE context_type='MARKET' QUALIFY row_number() OVER (PARTITION BY market_date ORDER BY created_at DESC)=1")
        names=[c[0] for c in cursor.description]; market_regime=_by_date([dict(zip(names,row)) for row in cursor.fetchall()])
        cursor=db.execute("SELECT * FROM regime_daily WHERE context_type='SECTOR' QUALIFY row_number() OVER (PARTITION BY market_date ORDER BY created_at DESC)=1")
        names=[c[0] for c in cursor.description]; sector_regime=_by_date([dict(zip(names,row)) for row in cursor.fetchall()])
    vectors=[]; states=[]; snapshots=[]; previous=None
    price_by_date=_by_date(prices)
    for day in sorted(price_by_date):
        parts={name:history.get(day) for name,history in components.items()}
        parts.update(regime=market_regime.get(day),sector_regime=sector_regime.get(day),capital_flow=flow_by_date.get(day))
        vector=build_evidence_vector(ticker,day,parts,V3_RULESET_VERSION)
        state=classify_market_state(vector,previous); previous=state.state
        row=price_by_date[day]; trend=parts["trend"] or {}; momentum=parts["momentum"] or {}; rs=parts["relative_strength"] or {}
        participation=parts["participation"] or {}; positioning=parts["positioning"] or {}; volatility=parts["volatility"] or {}; location=parts["location"] or {}
        flow_rows={item["participant"]:item for item in (parts["capital_flow"] or [])}
        foreign=flow_rows.get("FOREIGN",{}); trust=flow_rows.get("INVESTMENT_TRUST",{})
        payload={"close":row["close"],"market_regime":vector.dimensions["regime"].state,
            "sector_regime":vector.dimensions["sector_regime"].state,"market_state":state.state,
            **{f"{name}_state":vector.dimensions[name].state for name in ("structure","trend","momentum","relative_strength","participation","capital_flow","positioning","volatility","location")},
            "rsi14":momentum.get("rsi14"),"ma20":trend.get("ma20"),"ma60":trend.get("ma60"),"ma120":trend.get("ma120"),
            "atr14_pct":volatility.get("atr14_pct"),"rs_market_20d":rs.get("rs_market_20d"),"rs_market_60d":rs.get("rs_market_60d"),
            "rs_sector_20d":rs.get("rs_sector_20d"),"volume_ratio_20":participation.get("volume_ratio_20"),
            "foreign_5d":foreign.get("net_flow_5d"),"foreign_20d":foreign.get("net_flow_20d"),
            "trust_5d":trust.get("net_flow_5d"),"trust_20d":trust.get("net_flow_20d"),
            "margin_change_pct_20d":positioning.get("margin_change_pct_20d"),"leverage_divergence_20d":positioning.get("leverage_divergence_20d"),
            "support_zone_low":location.get("support_zone_low"),"support_zone_high":location.get("support_zone_high"),
            "resistance_zone_low":location.get("resistance_zone_low"),"resistance_zone_high":location.get("resistance_zone_high"),
            "evidence_vector":vector.model_dump(mode="json",exclude={"created_at"}),
            "market_state_detail":state.model_dump(mode="json",exclude={"created_at"})}
        vectors.append(vector); states.append(state); snapshots.append(V3SnapshotEnvelope(ticker=ticker,market_date=day,
            ruleset_version=V3_RULESET_VERSION,data_quality_status=vector.data_quality_status,payload=payload,created_at=state.created_at))
    version=version_record(git_commit,settings)
    with connect(settings.database) as db:
        register_analysis_version(db,version); persist_evidence_vectors(db,vectors); persist_market_states(db,states)
        for snapshot in snapshots: persist_v3_snapshot(db,snapshot)
    return vectors[-1],states[-1],snapshots[-1]


def _read_m6(db,ticker):
    rows=db.execute("SELECT market_date,dimensions_json,data_quality_status FROM evidence_v3_daily WHERE ticker=? AND ruleset_version='m6-evidence-market-state-v1' ORDER BY market_date",[ticker]).fetchall()
    vectors=[EvidenceVectorV3(ticker=ticker,market_date=row[0],dimensions=json.loads(row[1]),
        data_quality_status=row[2],ruleset_version="m6-evidence-market-state-v1",created_at=datetime.now(timezone.utc)) for row in rows]
    rows=db.execute("SELECT * FROM market_state_v3_daily WHERE ticker=? AND ruleset_version='m6-evidence-market-state-v1' ORDER BY market_date",[ticker])
    names=[c[0] for c in rows.description]; states=[]
    for raw in rows.fetchall():
        item=dict(zip(names,raw))
        for field in ("primary_evidence","supporting_evidence","contradicting_evidence","invalidation_conditions","unresolved_questions"):
            item[field]=json.loads(item.pop(field+"_json"))
        states.append(MarketStateV3(**item))
    return vectors,states


def refresh_m7(settings,ticker:str,git_commit:str):
    with connect(settings.database) as db: vectors,states=_read_m6(db,ticker)
    if not vectors or len(vectors)!=len(states): raise ValueError("M7 requires complete M6 evidence and market states")
    events=[]; scenarios=[]; previous_vector=None; previous_state=None
    for vector,state in zip(vectors,states):
        events.extend(detect_significant_events(vector,previous_vector,state,previous_state,V3_RULESET_VERSION))
        scenarios.extend(build_scenarios(vector,state,V3_RULESET_VERSION))
        previous_vector=vector; previous_state=state.state
    version=version_record(git_commit,settings)
    with connect(settings.database) as db:
        register_analysis_version(db,version); persist_significant_events(db,events); persist_scenarios(db,scenarios)
    latest_day=vectors[-1].market_date
    return [x for x in events if x.market_date==latest_day],[x for x in scenarios if x.market_date==latest_day]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--ticker", default="3702")
    args = parser.parse_args()
    settings, _, _ = load_config()
    events,scenarios=refresh_m7(settings,args.ticker,args.git_commit)
    for item in (*events,*scenarios): print(item.model_dump_json(indent=2))
