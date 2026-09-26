from __future__ import annotations

from datetime import date, datetime, timezone
import json

from src.models_v3 import EvidenceDimensionV3, EvidenceVectorV3, MarketStateV3


DIMENSIONS=("regime","sector_regime","structure","trend","momentum","relative_strength",
            "participation","capital_flow","positioning","volatility","location","fundamental_context")
POSITIVE={"RISK_ON_TREND","RISK_ON_EXTENDED","UPTREND_STRUCTURE","TREND_EMERGING","TREND_HEALTHY",
          "ACCELERATING","POSITIVE","LEADING","IMPROVING","STRONG_CONFIRMATION","CONFIRMING",
          "PERSISTENT_BUYING","BUYING","REVERSING_POSITIVE","HEALTHY","BREAKOUT_ZONE"}
NEGATIVE={"RISK_OFF","DOWNTREND_STRUCTURE","TREND_BROKEN","WEAKENING","NEGATIVE","LAGGING",
          "CONTRADICTORY","PERSISTENT_SELLING","SELLING","REVERSING_NEGATIVE","CROWDED","STRESS",
          "BREAKDOWN_ZONE"}


def _decoded(value):
    if value is None: return []
    if isinstance(value,str):
        try: return json.loads(value)
        except (json.JSONDecodeError,TypeError): return []
    return value


def _dimension(name, component, market_date):
    if component is None:
        return EvidenceDimensionV3(state="INSUFFICIENT_DATA",headline=f"{name}: data unavailable",
            missing_data=[name],calculation_version="unavailable")
    if name=="capital_flow":
        rows=component
        states=[row["state"] for row in rows]
        positive=sum(state in POSITIVE for state in states); negative=sum(state in NEGATIVE for state in states)
        state="POSITIVE" if positive>negative else "NEGATIVE" if negative>positive else "MIXED"
        observations=[{"participant":row["participant"],"state":row["state"],"net_flow_5d":row.get("net_flow_5d"),"net_flow_20d":row.get("net_flow_20d")} for row in rows]
        version=rows[0].get("ruleset_version","unknown") if rows else "unavailable"
        source=sorted({d for row in rows for d in _decoded(row.get("source_dates_json"))})
        missing=[] if rows else ["capital_flow"]
    else:
        row=component; state=row.get("state") or row.get("regime") or "INSUFFICIENT_DATA"
        version=row.get("ruleset_version","v2-structure" if name=="structure" else "unknown")
        source=_decoded(row.get("source_dates_json")) or [row.get("market_date",market_date)]
        missing=_decoded(row.get("missing_inputs_json"))
        excluded={"ticker","market_date","analysis_version","ruleset_version","created_at","observations_json","source_dates_json","missing_inputs_json"}
        observations=_decoded(row.get("observations_json")) or [{key:value for key,value in row.items() if key not in excluded and value is not None}]
    source=[date.fromisoformat(value[:10]) if isinstance(value,str) else value for value in source if value is not None]
    if any(value>market_date for value in source):
        state="INSUFFICIENT_DATA"; missing=sorted(set(missing+["future_source_date_rejected"])); observations=[]
    evidence={"state":state,"reason":"deterministic state from persisted point-in-time observations"}
    return EvidenceDimensionV3(state=state,headline=f"{name}: {state}",observations=observations,
        evidence_for=[evidence] if state in POSITIVE else [],evidence_against=[evidence] if state in NEGATIVE else [],
        missing_data=missing,source_dates=source,calculation_version=version)


def build_evidence_vector(ticker,market_date,components,ruleset_version,data_quality_status="PASS"):
    dimensions={name:_dimension(name,components.get(name),market_date) for name in DIMENSIONS}
    return EvidenceVectorV3(ticker=ticker,market_date=market_date,dimensions=dimensions,
        data_quality_status=data_quality_status,ruleset_version=ruleset_version,created_at=datetime.now(timezone.utc))


def _ref(vector,name):
    item=vector.dimensions[name]
    return {"dimension":name,"state":item.state,"headline":item.headline}


def classify_market_state(vector: EvidenceVectorV3, previous_state: str | None=None) -> MarketStateV3:
    d=vector.dimensions; structure=d["structure"].state; trend=d["trend"].state; momentum=d["momentum"].state
    participation=d["participation"].state; flow=d["capital_flow"].state; positioning=d["positioning"].state
    location=d["location"].state
    if vector.data_quality_status=="FAIL": state="UNCLASSIFIED"; primary=[_ref(vector,"structure")]
    elif location=="BREAKDOWN_ZONE" or (structure=="DOWNTREND_STRUCTURE" and trend=="TREND_BROKEN" and momentum in {"WEAKENING","NEGATIVE"}):
        state="S8_STRUCTURE_FAILURE"; primary=[_ref(vector,"structure"),_ref(vector,"trend"),_ref(vector,"location")]
    elif structure=="DOWNTREND_STRUCTURE" and trend=="TREND_BROKEN": state="S0_DECLINE"; primary=[_ref(vector,"structure"),_ref(vector,"trend")]
    elif participation in {"CONTRADICTORY","ABNORMAL"} and (flow=="NEGATIVE" or positioning in {"CROWDED","STRESS"}):
        state="S6_DISTRIBUTION_RISK"; primary=[_ref(vector,"participation"),_ref(vector,"capital_flow"),_ref(vector,"positioning")]
    elif structure=="UPTREND_STRUCTURE" and trend in {"TREND_DECELERATING","TREND_BROKEN"}:
        state="S7_CORRECTION"; primary=[_ref(vector,"structure"),_ref(vector,"trend")]
    elif trend=="TREND_EXTENDED" and momentum in {"ACCELERATING","POSITIVE"}:
        state="S5_EXTENSION"; primary=[_ref(vector,"trend"),_ref(vector,"momentum")]
    elif location=="BREAKOUT_ZONE" or (participation in {"STRONG_CONFIRMATION","CONFIRMING"} and any(o.get("metric")=="breakout" and o.get("value") is True for o in d["participation"].observations)):
        state="S3_BREAKOUT"; primary=[_ref(vector,"participation"),_ref(vector,"location")]
    elif structure=="UPTREND_STRUCTURE" and trend in {"TREND_HEALTHY","TREND_EMERGING"}:
        state="S4_TREND"; primary=[_ref(vector,"structure"),_ref(vector,"trend")]
    elif structure=="POSSIBLE_BASE" and momentum in {"RESET","POSITIVE","ACCELERATING"}:
        state="S2_BASE"; primary=[_ref(vector,"structure"),_ref(vector,"momentum")]
    elif structure in {"DOWNTREND_STRUCTURE","POSSIBLE_BASE"} and trend in {"TREND_DECELERATING","RANGE"}:
        state="S1_STABILIZATION"; primary=[_ref(vector,"structure"),_ref(vector,"trend")]
    else: state="TRANSITION"; primary=[_ref(vector,"structure"),_ref(vector,"trend"),_ref(vector,"momentum")]
    primary_names={item["dimension"] for item in primary}
    supporting=[_ref(vector,name) for name,item in d.items() if name not in primary_names and item.state in POSITIVE]
    contradicting=[_ref(vector,name) for name,item in d.items() if name not in primary_names and item.state in NEGATIVE]
    invalidations={
        "S4_TREND":[{"condition":"structure_state != UPTREND_STRUCTURE","depends_on":"structure"},{"condition":"trend_state == TREND_BROKEN","depends_on":"trend"}],
        "S5_EXTENSION":[{"condition":"momentum_state not in [ACCELERATING, POSITIVE]","depends_on":"momentum"}],
        "S3_BREAKOUT":[{"condition":"location_state in [AT_RESISTANCE, BREAKDOWN_ZONE]","depends_on":"location"}],
        "S2_BASE":[{"condition":"structure_state == DOWNTREND_STRUCTURE","depends_on":"structure"}],
        "S1_STABILIZATION":[{"condition":"trend_state == TREND_BROKEN","depends_on":"trend"}],
    }.get(state,[{"condition":"primary evidence changes","depends_on":item["dimension"]} for item in primary])
    unresolved=sorted({missing for item in d.values() for missing in item.missing_data})
    transition=None if previous_state is None or previous_state==state else f"{previous_state} -> {state}"
    return MarketStateV3(ticker=vector.ticker,market_date=vector.market_date,state=state,previous_state=previous_state,
        transition=transition,primary_evidence=primary,supporting_evidence=supporting,
        contradicting_evidence=contradicting,invalidation_conditions=invalidations,
        unresolved_questions=unresolved,ruleset_version=vector.ruleset_version,created_at=datetime.now(timezone.utc))
