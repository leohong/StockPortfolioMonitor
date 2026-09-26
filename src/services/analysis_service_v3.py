from __future__ import annotations

import argparse

from src.analysis.momentum.momentum import calculate_momentum
from src.analysis.relative_strength.relative_strength import calculate_relative_strength
from src.analysis.trend.trend_quality import calculate_trend_quality
from src.analysis.versioning import V3_RULESET_VERSION, register_analysis_version, version_record
from src.analysis.participation import calculate_participation
from src.analysis.flow import calculate_capital_flow
from src.analysis.positioning import calculate_positioning
from src.config import load_config
from src.database.db import connect, frame, read_institutional, read_margin, read_pivots
from src.database.v3 import (persist_momentum_states, persist_relative_strength, persist_trend_quality,
                             persist_participation, persist_capital_flow, persist_positioning, read_benchmark)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--ticker", default="3702")
    args = parser.parse_args()
    settings, _, _ = load_config()
    participation,flows,positioning=refresh_m4(settings,args.ticker,args.git_commit)
    for item in (participation,*flows,positioning): print(item.model_dump_json(indent=2))
