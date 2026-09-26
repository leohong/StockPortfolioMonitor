from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from src.models_v3 import EvidenceVectorV3, MarketStateV3, SignificantEventV3


def _event_id(ticker,day,dimension,previous,current):
    raw=f"{ticker}|{day}|{dimension}|{previous}|{current}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def detect_significant_events(current: EvidenceVectorV3, previous: EvidenceVectorV3 | None,
                              state: MarketStateV3, previous_market_state: str | None,
                              ruleset_version: str) -> list[SignificantEventV3]:
    if previous is None: return []
    changes=[]
    for dimension,item in current.dimensions.items():
        prior=previous.dimensions[dimension].state
        if prior!=item.state: changes.append((dimension,prior,item.state))
    if previous_market_state and previous_market_state!=state.state:
        changes.append(("market_state",previous_market_state,state.state))
    output=[]
    for dimension,prior,present in changes:
        context={name:current.dimensions[name].state for name in ("structure","trend","participation","capital_flow","positioning","location")}
        critical=(present=="BREAKDOWN_ZONE" and context["structure"]=="DOWNTREND_STRUCTURE"
            and context["participation"] in {"STRONG_CONFIRMATION","CONFIRMING"}
            and context["capital_flow"]=="NEGATIVE" and context["positioning"] in {"LEVERAGE_EXPANDING","CROWDED","STRESS"})
        reasons=["STATE_CHANGED"]
        if critical: significance="CRITICAL"; reasons += ["SUPPORT_BREAK","VOLUME_CONFIRMATION","NEGATIVE_FLOW","LEVERAGE_RISK"]
        elif dimension=="structure" or present in {"BREAKDOWN_ZONE","S8_STRUCTURE_FAILURE"}:
            significance="HIGH"; reasons.append("STRUCTURAL_CHANGE")
        elif dimension in {"market_state","regime","sector_regime","trend","capital_flow","positioning","location"}:
            significance="MEDIUM"; reasons.append("CONTEXT_CHANGE")
        else: significance="LOW"; reasons.append("SECONDARY_EVIDENCE_CHANGE")
        features=[{"dimension":name,"state":value} for name,value in context.items()]
        output.append(SignificantEventV3(event_id=_event_id(current.ticker,current.market_date,dimension,prior,present),
            ticker=current.ticker,market_date=current.market_date,dimension=dimension,previous_state=prior,
            current_state=present,significance=significance,context_features=features,reason_codes=reasons,
            explanation=f"{dimension} changed from {prior} to {present}; significance is attention priority, not trade advice.",
            ruleset_version=ruleset_version,created_at=datetime.now(timezone.utc)))
    return output
