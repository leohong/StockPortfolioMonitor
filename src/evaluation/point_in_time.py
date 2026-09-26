from __future__ import annotations

import json
from time import perf_counter

from src.analysis.market_state import build_evidence_vector, classify_market_state
from src.analysis.scenario import build_scenarios
from src.analysis.significance import detect_significant_events
from src.database.db import connect

M6_RULESET = "m6-evidence-market-state-v1"
M7_RULESET = "m7-significance-scenario-v1"


def _rows(db, query, params=()):
    cursor = db.execute(query, params)
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _by_date(rows):
    return {row["market_date"]: row for row in rows}


def _scenario_payload(item):
    value = item.model_dump(mode="python", exclude={"created_at", "ruleset_version", "analysis_version"})
    return value


def replay_v3(settings, ticker: str) -> dict:
    """Rebuild M6 state/M7 events and scenarios chronologically from saved PIT inputs."""
    started = perf_counter()
    with connect(settings.database) as db:
        prices = _rows(db, "SELECT * FROM ohlcv_daily WHERE ticker=? ORDER BY market_date", [ticker])
        component_tables = {
            "structure": ("structure_snapshots", False),
            "trend": ("trend_quality_daily", True),
            "momentum": ("momentum_state_daily", True),
            "relative_strength": ("relative_strength_daily", True),
            "participation": ("participation_daily", True),
            "positioning": ("positioning_daily", True),
            "volatility": ("volatility_daily", True),
            "location": ("location_state_daily", True),
        }
        components = {}
        for name, (table, versioned) in component_tables.items():
            qualifier = (" QUALIFY row_number() OVER (PARTITION BY market_date ORDER BY created_at DESC)=1"
                         if versioned else "")
            components[name] = _by_date(_rows(db,
                f"SELECT * FROM {table} WHERE ticker=?{qualifier} ORDER BY market_date", [ticker]))
        flows = _rows(db, "SELECT * FROM capital_flow_daily WHERE ticker=? "
            "QUALIFY row_number() OVER (PARTITION BY market_date,participant ORDER BY created_at DESC)=1 "
            "ORDER BY market_date,participant", [ticker])
        flow_by_date = {day: [row for row in flows if row["market_date"] == day]
                        for day in {row["market_date"] for row in flows}}
        market_regime = _by_date(_rows(db, "SELECT * FROM regime_daily WHERE context_type='MARKET' "
            "QUALIFY row_number() OVER (PARTITION BY market_date ORDER BY created_at DESC)=1 ORDER BY market_date"))
        sector_regime = _by_date(_rows(db, "SELECT * FROM regime_daily WHERE context_type='SECTOR' "
            "QUALIFY row_number() OVER (PARTITION BY market_date ORDER BY created_at DESC)=1 ORDER BY market_date"))
        snapshots = _by_date(_rows(db, "SELECT market_date,data_quality_status,payload_json FROM snapshot_v3_daily "
            "WHERE ticker=? AND ruleset_version=? ORDER BY market_date", [ticker, M6_RULESET]))
        evidence_quality = dict(db.execute("SELECT market_date,data_quality_status FROM evidence_v3_daily "
            "WHERE ticker=? AND ruleset_version=?", [ticker, M6_RULESET]).fetchall())
        saved_events = _rows(db, "SELECT event_id,market_date,dimension,previous_state,current_state,significance "
            "FROM event_significance WHERE ticker=? AND ruleset_version=? ORDER BY market_date,event_id", [ticker, M7_RULESET])
        saved_scenarios = _rows(db, "SELECT * FROM scenario_daily WHERE ticker=? AND ruleset_version=? "
            "ORDER BY market_date,scenario_type", [ticker, M7_RULESET])

    event_identity = {(row["event_id"], row["market_date"], row["dimension"], row["previous_state"],
                       row["current_state"], row["significance"]) for row in saved_events}
    scenario_by_key = {}
    for row in saved_scenarios:
        for field in ("conditions", "confirmation_events", "invalidation_events", "relevant_levels", "evidence_dependencies"):
            row[field] = json.loads(row.pop(field + "_json"))
        scenario_by_key[(row["market_date"], row["scenario_type"])] = {
            key: row[key] for key in ("ticker", "market_date", "scenario_type", "name", "current_status", "conditions",
                                      "confirmation_events", "invalidation_events", "relevant_levels",
                                      "evidence_dependencies", "interpretation")}

    replayed_events = set()
    previous_vector = None
    previous_state = None
    state_mismatches = []
    evidence_mismatches = []
    scenario_mismatches = []
    future_source_violations = []
    price_by_date = _by_date(prices)
    for day in sorted(snapshots):
        parts = {name: history.get(day) for name, history in components.items()}
        parts.update(regime=market_regime.get(day), sector_regime=sector_regime.get(day),
                     capital_flow=flow_by_date.get(day))
        vector = build_evidence_vector(ticker, day, parts, M6_RULESET,
                                       data_quality_status=evidence_quality.get(day, "PASS"))
        state = classify_market_state(vector, previous_state)
        saved = json.loads(snapshots[day]["payload_json"])
        expected_vector = saved.get("evidence_vector", {})
        actual_vector = vector.model_dump(mode="json", exclude={"created_at"})
        if actual_vector != expected_vector:
            evidence_mismatches.append(str(day))
        if state.state != saved.get("market_state"):
            state_mismatches.append({"date": str(day), "saved": saved.get("market_state"), "replayed": state.state})
        for name, dimension in vector.dimensions.items():
            for source_day in dimension.source_dates:
                if source_day > day:
                    future_source_violations.append({"date": str(day), "dimension": name, "source": str(source_day)})
        for event in detect_significant_events(vector, previous_vector, state, previous_state, M7_RULESET):
            replayed_events.add((event.event_id, event.market_date, event.dimension, event.previous_state,
                                 event.current_state, event.significance))
        for scenario in build_scenarios(vector, state, M7_RULESET):
            key = (day, scenario.scenario_type)
            if _scenario_payload(scenario) != scenario_by_key.get(key):
                scenario_mismatches.append({"date": str(day), "scenario": scenario.scenario_type})
        previous_vector, previous_state = vector, state.state

    return {
        "ticker": ticker,
        "snapshot_count": len(snapshots),
        "price_count": len(price_by_date),
        "start_date": str(min(snapshots)) if snapshots else None,
        "end_date": str(max(snapshots)) if snapshots else None,
        "evidence_mismatches": evidence_mismatches,
        "state_mismatches": state_mismatches,
        "event_missing": len(event_identity - replayed_events),
        "event_extra": len(replayed_events - event_identity),
        "scenario_mismatches": scenario_mismatches,
        "future_source_violations": future_source_violations,
        "passed": bool(snapshots) and not any((evidence_mismatches, state_mismatches,
            event_identity - replayed_events, replayed_events - event_identity, scenario_mismatches,
            future_source_violations)),
        "elapsed_seconds": round(perf_counter() - started, 6),
    }
