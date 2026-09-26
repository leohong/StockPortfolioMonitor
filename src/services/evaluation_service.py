from __future__ import annotations

import json
from pathlib import Path

from src.analysis.flow.capital_flow import calculate_capital_flow
from src.analysis.location.location import calculate_location
from src.analysis.participation.participation import calculate_participation
from src.analysis.positioning.positioning import calculate_positioning
from src.analysis.price_structure import detect_pivots
from src.analysis.relative_strength.relative_strength import calculate_relative_strength
from src.analysis.trend.trend_quality import calculate_trend_quality
from src.analysis.volatility.volatility import calculate_volatility
from src.config import ROOT, load_config
from src.database.db import connect, frame, read_institutional, read_margin
from src.database.v3 import read_benchmark
from src.evaluation.event_study import event_study
from src.evaluation.performance import benchmark
from src.evaluation.point_in_time import replay_v3
from src.evaluation.robustness import classify_stability, state_agreement
from src.evaluation.walk_forward import walk_forward
from src.services.stock_service import load_stock
from src.services.ui_v3_service import load_v3_portfolio

RULESET = "m9-evaluation-v1"


def _case(name, parameter, baseline, candidate):
    result = state_agreement(baseline, candidate)
    return {"engine": name, "parameter": parameter, **result, "stability": classify_stability(result)}


def robustness(settings, ticker):
    stock, quality = load_stock(settings, ticker)
    if quality.status == "FAIL" or stock.empty:
        raise ValueError("M9 robustness requires validated official stock history")
    with connect(settings.database) as db:
        benchmark_data = read_benchmark(db)
        institutional = frame(read_institutional(db, ticker))
        margin = frame(read_margin(db, ticker))
    results = []
    base = calculate_trend_quality(stock, RULESET, extended_distance_pct=8, persistence_min=.7)
    for distance, persistence in ((7, .65), (9, .75)):
        results.append(_case("trend", f"extended={distance},persistence={persistence}", base,
            calculate_trend_quality(stock, RULESET, extended_distance_pct=distance, persistence_min=persistence)))
    base = calculate_relative_strength(stock, benchmark_data, RULESET, leading_20d_pct=3, leading_60d_pct=5)
    for short, long in ((2, 4), (4, 6)):
        results.append(_case("relative_strength", f"leading20={short},leading60={long}", base,
            calculate_relative_strength(stock, benchmark_data, RULESET, leading_20d_pct=short, leading_60d_pct=long)))
    base = calculate_participation(stock, RULESET, confirm_ratio=1.2, strong_ratio=1.5, abnormal_ratio=2.5)
    for confirm, strong, abnormal in ((1.1, 1.4, 2.3), (1.3, 1.6, 2.7)):
        results.append(_case("participation", f"confirm={confirm},strong={strong},abnormal={abnormal}", base,
            calculate_participation(stock, RULESET, confirm_ratio=confirm, strong_ratio=strong, abnormal_ratio=abnormal)))
    base = calculate_capital_flow(institutional, RULESET, persistence_ratio=.7)
    for ratio in (.65, .75):
        results.append(_case("capital_flow", f"persistence={ratio}", base,
            calculate_capital_flow(institutional, RULESET, persistence_ratio=ratio)))
    base = calculate_positioning(stock, margin, RULESET, expansion_pct=10, crowded_pct=20, deleveraging_pct=-5)
    for expansion, crowded, deleveraging in ((8, 18, -4), (12, 22, -6)):
        results.append(_case("positioning", f"expansion={expansion},crowded={crowded},deleveraging={deleveraging}", base,
            calculate_positioning(stock, margin, RULESET, expansion_pct=expansion, crowded_pct=crowded, deleveraging_pct=deleveraging)))
    base = calculate_volatility(stock, RULESET, compressed=.2, expanding=.7, high=.9, shock_range=2.5)
    for compressed, expanding, high, shock in ((.15, .65, .85, 2.25), (.25, .75, .95, 2.75)):
        results.append(_case("volatility", f"pct={compressed}/{expanding}/{high},shock={shock}", base,
            calculate_volatility(stock, RULESET, compressed=compressed, expanding=expanding, high=high, shock_range=shock)))
    base_pivots = detect_pivots(stock, 3, 3)
    base = calculate_location(stock, base_pivots, RULESET, tolerance_pct=2, near_pct=2, at_pct=.5)[2]
    for width in (2, 4):
        pivots = detect_pivots(stock, width, width)
        candidate = calculate_location(stock, pivots, RULESET, tolerance_pct=2, near_pct=2, at_pct=.5)[2]
        results.append(_case("location", f"pivot_left_right={width}", base, candidate))
    return results


def run_m9(settings, holdings):
    ticker = holdings[0].ticker
    replay = replay_v3(settings, ticker)
    studies = event_study(settings, ticker)
    folds = walk_forward(settings, ticker)
    sensitivity = robustness(settings, ticker)
    performance = [
        benchmark("portfolio_v3", lambda: load_v3_portfolio(settings, holdings)),
        benchmark("point_in_time_replay", lambda: replay_v3(settings, ticker), repeats=2),
        benchmark("event_study", lambda: event_study(settings, ticker)),
    ]
    return {"ruleset": RULESET, "ticker": ticker, "replay": replay, "event_studies": studies,
            "walk_forward": folds, "robustness": sensitivity, "performance": performance}


def save_registry(result, path: Path):
    replay = result["replay"]
    record = {"experiment_id": "M9-2026-09-26-v1",
        "hypothesis": "V3 artifacts are point-in-time reproducible and nearby thresholds do not collapse state classifications",
        "parameters": {"replay_ruleset": "m6/m7 persisted rules", "robustness": "nearby configured values"},
        "dataset": f"official persisted TWSE data for {result['ticker']}", "start_date": replay["start_date"],
        "end_date": replay["end_date"], "metrics": {"replay_passed": replay["passed"],
            "walk_forward_folds": len(result["walk_forward"]),
            "sensitive_cases": sum(row["stability"] == "SENSITIVE" for row in result["robustness"])},
        "result": "PASS" if replay["passed"] else "FAIL", "created_at": "2026-09-26T00:00:00+08:00"}
    path.write_text(json.dumps([record], ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    settings, holdings, _ = load_config()
    result = run_m9(settings, holdings)
    output = ROOT / "data" / "evaluation"
    output.mkdir(parents=True, exist_ok=True)
    (output / "m9_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), "utf-8")
    save_registry(result, ROOT / "docs" / "V3_EXPERIMENT_REGISTRY.json")
    print(json.dumps({"replay": result["replay"], "event_study_rows": len(result["event_studies"]),
        "walk_forward_folds": len(result["walk_forward"]), "robustness_cases": len(result["robustness"]),
        "performance": result["performance"]}, ensure_ascii=False, indent=2))
