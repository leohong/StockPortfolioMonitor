from datetime import date
import json

from src.analysis.market_state import build_evidence_vector,classify_market_state

DAY=date(2026,9,24); RULES="m6-test"


def row(state,version="source-v1",**values):
    return {"ticker":"3702","market_date":DAY,"state":state,"ruleset_version":version,
            "source_dates_json":json.dumps([str(DAY)]),**values}


def components(**updates):
    base={"regime":row("RISK_ON_TREND"),"sector_regime":None,"structure":row("UPTREND_STRUCTURE"),
        "trend":row("TREND_HEALTHY"),"momentum":row("POSITIVE"),"relative_strength":row("IMPROVING"),
        "participation":row("NORMAL"),"capital_flow":[{**row("PERSISTENT_BUYING"),"participant":"FOREIGN"}],
        "positioning":row("NORMAL"),"volatility":row("NORMAL"),"location":row("MID_RANGE")}
    base.update(updates); return base


def test_evidence_vector_has_all_dimensions_and_no_score():
    vector=build_evidence_vector("3702",DAY,components(),RULES)
    assert set(vector.dimensions)=={"regime","sector_regime","structure","trend","momentum","relative_strength",
        "participation","capital_flow","positioning","volatility","location","fundamental_context"}
    assert vector.dimensions["trend"].calculation_version=="source-v1"
    assert "score" not in vector.model_dump_json().lower()


def test_hierarchy_keeps_broken_structure_primary_and_explains_state():
    vector=build_evidence_vector("3702",DAY,components(structure=row("DOWNTREND_STRUCTURE"),
        trend=row("TREND_BROKEN"),momentum=row("NEGATIVE"),relative_strength=row("LEADING")),RULES)
    state=classify_market_state(vector,"S4_TREND")
    assert state.state=="S8_STRUCTURE_FAILURE"
    assert state.transition=="S4_TREND -> S8_STRUCTURE_FAILURE"
    assert {item["dimension"] for item in state.primary_evidence}>={"structure","trend"}
    assert any(item["dimension"]=="relative_strength" for item in state.supporting_evidence)
    assert state.invalidation_conditions


def test_distribution_risk_requires_combination_and_records_contradictions():
    vector=build_evidence_vector("3702",DAY,components(participation=row("ABNORMAL"),positioning=row("CROWDED")),RULES)
    state=classify_market_state(vector)
    assert state.state=="S6_DISTRIBUTION_RISK"
    assert any(item["dimension"]=="relative_strength" for item in state.supporting_evidence)
    normal=build_evidence_vector("3702",DAY,components(participation=row("ABNORMAL")),RULES)
    assert classify_market_state(normal).state!="S6_DISTRIBUTION_RISK"


def test_future_source_is_rejected_in_historical_replay():
    future=row("TREND_HEALTHY"); future["source_dates_json"]=json.dumps(["2026-09-25"])
    vector=build_evidence_vector("3702",DAY,components(trend=future),RULES)
    assert vector.dimensions["trend"].state=="INSUFFICIENT_DATA"
    assert "future_source_date_rejected" in vector.dimensions["trend"].missing_data
