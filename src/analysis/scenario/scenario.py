from __future__ import annotations

from datetime import datetime, timezone
from src.models_v3 import EvidenceVectorV3, MarketStateV3, ScenarioConditionV3, ScenarioV3


def _condition(vector,dimension,operator,expected):
    observed=vector.dimensions[dimension].state
    satisfied=(observed in expected) if operator=="IN" else (observed not in expected) if operator=="NOT_IN" else observed==expected[0]
    return ScenarioConditionV3(dimension=dimension,operator=operator,expected=expected,observed=observed,satisfied=satisfied)


def _status(conditions):
    count=sum(item.satisfied for item in conditions)
    return "SUPPORTED" if count==len(conditions) else "PARTIAL" if count else "NOT_SUPPORTED"


def _scenario(vector,kind,name,conditions,confirm,invalidate,interpretation,ruleset):
    location=vector.dimensions["location"].observations
    levels=[item for item in location if item.get("metric") in {"support_zone","resistance_zone"}]
    return ScenarioV3(ticker=vector.ticker,market_date=vector.market_date,scenario_type=kind,name=name,
        current_status=_status(conditions),conditions=conditions,confirmation_events=confirm,
        invalidation_events=invalidate,relevant_levels=levels,
        evidence_dependencies=sorted({item.dimension for item in conditions}),interpretation=interpretation,
        ruleset_version=ruleset,created_at=datetime.now(timezone.utc))


def build_scenarios(vector: EvidenceVectorV3, market_state: MarketStateV3, ruleset_version: str) -> list[ScenarioV3]:
    positive=[_condition(vector,"structure","IN",["UPTREND_STRUCTURE","POSSIBLE_BASE"]),
        _condition(vector,"trend","IN",["TREND_HEALTHY","TREND_EMERGING"]),
        _condition(vector,"relative_strength","IN",["LEADING","IMPROVING"]),
        _condition(vector,"location","NOT_IN",["BREAKDOWN_ZONE"])]
    neutral=[ScenarioConditionV3(dimension="market_state",operator="IN",expected=["TRANSITION","UNCLASSIFIED"],
            observed=market_state.state,satisfied=market_state.state in {"TRANSITION","UNCLASSIFIED"}),
        _condition(vector,"sector_regime","EQUALS",["INSUFFICIENT_DATA"]),
        _condition(vector,"fundamental_context","EQUALS",["INSUFFICIENT_DATA"])]
    negative=[_condition(vector,"structure","IN",["DOWNTREND_STRUCTURE","POSSIBLE_TOP"]),
        _condition(vector,"trend","IN",["TREND_BROKEN","TREND_DECELERATING"]),
        _condition(vector,"capital_flow","EQUALS",["NEGATIVE"]),
        _condition(vector,"location","EQUALS",["BREAKDOWN_ZONE"])]
    return [
        _scenario(vector,"POSITIVE_CONTINUATION","Continuation",positive,
            [{"event":"trend_and_structure_align","dependencies":["structure","trend"]},{"event":"resistance_break_confirmed","dependencies":["location","participation"]}],
            [{"event":"support_zone_breaks","dependencies":["location"]},{"event":"trend_breaks","dependencies":["trend"]}],
            "If all listed evidence remains or becomes satisfied, continuation evidence strengthens; this is not a forecast.",ruleset_version),
        _scenario(vector,"NEUTRAL_UNRESOLVED","Unresolved",neutral,
            [{"event":"conflicting_dimensions_resolve","dependencies":["market_state"]}],
            [{"event":"structure_and_trend_align","dependencies":["structure","trend"]}],
            "Current missing or conflicting evidence keeps the state unresolved until listed dependencies change.",ruleset_version),
        _scenario(vector,"NEGATIVE_DETERIORATION","Deterioration",negative,
            [{"event":"support_break_with_weakening_context","dependencies":["location","trend","capital_flow"]}],
            [{"event":"support_holds_or_is_reclaimed","dependencies":["location"]},{"event":"trend_recovers","dependencies":["trend"]}],
            "If all listed deterioration conditions become satisfied, structural-risk evidence strengthens; this is not a forecast.",ruleset_version),
    ]
