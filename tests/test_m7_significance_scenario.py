from datetime import date,datetime,timezone

from src.analysis.market_state import build_evidence_vector,classify_market_state
from src.analysis.scenario import build_scenarios
from src.analysis.significance import detect_significant_events

DAY=date(2026,9,24); RULES="m7-test"


def parts(**updates):
    def row(state,**extra): return {"state":state,"market_date":DAY,"ruleset_version":"source-v1",**extra}
    base={"regime":row("RISK_ON_TREND"),"sector_regime":row("INSUFFICIENT_DATA"),
        "structure":row("UPTREND_STRUCTURE"),"trend":row("TREND_HEALTHY"),"momentum":row("POSITIVE"),
        "relative_strength":row("IMPROVING"),"participation":row("NORMAL"),
        "capital_flow":[{**row("BUYING"),"participant":"FOREIGN"}],"positioning":row("NORMAL"),
        "volatility":row("NORMAL"),"location":row("MID_RANGE",observations_json='[{"metric":"support_zone","low":100,"high":101}]')}
    base.update(updates); return base


def vector(**updates): return build_evidence_vector("3702",DAY,parts(**updates),"m6-test")


def test_significance_is_deterministic_attention_priority():
    previous=vector()
    current=vector(structure={"state":"DOWNTREND_STRUCTURE","market_date":DAY,"ruleset_version":"x"})
    state=classify_market_state(current,"S4_TREND")
    events=detect_significant_events(current,previous,state,"S4_TREND",RULES)
    structure=next(item for item in events if item.dimension=="structure")
    assert structure.significance=="HIGH" and "STRUCTURAL_CHANGE" in structure.reason_codes
    assert "trade advice" in structure.explanation and len(structure.event_id)==24


def test_critical_requires_structured_combination():
    previous=vector()
    current=vector(structure={"state":"DOWNTREND_STRUCTURE","market_date":DAY,"ruleset_version":"x"},
        participation={"state":"CONFIRMING","market_date":DAY,"ruleset_version":"x"},
        capital_flow=[{"state":"PERSISTENT_SELLING","participant":"FOREIGN","market_date":DAY,"ruleset_version":"x"}],
        positioning={"state":"LEVERAGE_EXPANDING","market_date":DAY,"ruleset_version":"x"},
        location={"state":"BREAKDOWN_ZONE","market_date":DAY,"ruleset_version":"x"})
    state=classify_market_state(current)
    events=detect_significant_events(current,previous,state,None,RULES)
    event=next(item for item in events if item.dimension=="location")
    assert event.significance=="CRITICAL"
    assert set(event.reason_codes)>={"SUPPORT_BREAK","VOLUME_CONFIRMATION","NEGATIVE_FLOW","LEVERAGE_RISK"}


def test_scenarios_are_three_conditional_structures_without_forecast_or_target():
    current=vector(); state=classify_market_state(current)
    scenarios=build_scenarios(current,state,RULES)
    assert {item.scenario_type for item in scenarios}=={"POSITIVE_CONTINUATION","NEUTRAL_UNRESOLVED","NEGATIVE_DETERIORATION"}
    assert all(item.conditions and item.confirmation_events and item.invalidation_events and item.evidence_dependencies for item in scenarios)
    text=" ".join(item.model_dump_json() for item in scenarios).lower()
    assert "probability" not in text and "target_price" not in text
    positive=next(item for item in scenarios if item.scenario_type=="POSITIVE_CONTINUATION")
    assert positive.current_status=="SUPPORTED" and positive.relevant_levels
