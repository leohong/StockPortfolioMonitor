from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

from src.models import PricePivot
from src.models_v3 import AnchoredVWAP, LocationState, LocationZone


def _tick(price: float) -> float:
    if price < 10: return .01
    if price < 50: return .05
    if price < 100: return .1
    if price < 500: return .5
    if price < 1000: return 1.
    return 5.


def _round_tick(price: float) -> float:
    tick=_tick(price)
    return round(round(price/tick)*tick,2)


def _avwap(frame: pd.DataFrame, *, anchor_type, anchor_date, confirmation_date, anchor_price,
           derivation, as_of, ruleset) -> AnchoredVWAP | None:
    if confirmation_date > as_of:
        return None
    history=frame[(frame.market_date>=anchor_date)&(frame.market_date<=as_of)]
    valid=history.dropna(subset=["high","low","close","volume"])
    denominator=valid.volume.sum()
    if valid.empty or denominator <= 0:
        return None
    value=(((valid.high+valid.low+valid.close)/3)*valid.volume).sum()/denominator
    return AnchoredVWAP(ticker=str(valid.iloc[-1].ticker),market_date=as_of,anchor_type=anchor_type,
        anchor_date=anchor_date,confirmation_date=confirmation_date,anchor_price=anchor_price,
        avwap=float(value),derivation=derivation+"; typical price × official share volume / official share volume",
        source_dates=valid.market_date.tolist(),ruleset_version=ruleset,created_at=datetime.now(timezone.utc))


def _cluster(candidates, close, zone_type, tolerance):
    side=[c for c in candidates if (c[0] <= close if zone_type=="SUPPORT" else c[0] >= close)]
    if not side: return None
    seed=min(side,key=lambda c:abs(c[0]-close)); group=[c for c in side if abs(c[0]-seed[0])/seed[0] <= tolerance]
    types=sorted({c[1] for c in group}); low=_round_tick(min(c[0] for c in group)); high=_round_tick(max(c[0] for c in group))
    strength="STRONG" if len(types)>=3 else "MODERATE" if len(types)>=2 else "SINGLE"
    return low,high,types,[{"level_type":c[1],"price":_round_tick(c[0]),"derivation":c[2],"source_date":str(c[3])} for c in group],strength


def calculate_location(data: pd.DataFrame, pivots: list[PricePivot], ruleset_version: str, *,
                       tolerance_pct=2., near_pct=2., at_pct=.5):
    frame=data.sort_values("market_date").reset_index(drop=True).copy(); frame["market_date"]=pd.to_datetime(frame.market_date).dt.date
    for window in (20,60,120): frame[f"ma{window}"]=frame.close.rolling(window,min_periods=window).mean()
    frame["prior_high20"]=frame.high.rolling(20,min_periods=20).max().shift(1); frame["prior_low20"]=frame.low.rolling(20,min_periods=20).min().shift(1)
    frame["volume_ratio20"]=frame.volume/frame.volume.rolling(20,min_periods=20).mean().replace(0,pd.NA)
    frame["gap_pct"]=(frame.open/frame.close.shift(1)-1)*100
    avwaps=[]; zones=[]; states=[]
    for index,row in frame.iterrows():
        confirmed=[p for p in pivots if p.confirmation_date<=row.market_date]
        latest=[]
        for kind in ("LOW","HIGH"):
            matches=[p for p in confirmed if p.pivot_kind==kind]
            if matches: latest.append(max(matches,key=lambda p:(p.confirmation_date,p.pivot_date)))
        anchors=[]
        for p in latest:
            anchors.append(("CONFIRMED_SWING_LOW" if p.pivot_kind=="LOW" else "CONFIRMED_SWING_HIGH",
                p.pivot_date,p.confirmation_date,p.price,"confirmed pivot available "+str(p.confirmation_date)))
        history=frame.iloc[:index+1]
        events=(("BREAKOUT_DATE",history[history.close>history.prior_high20],"close crossed prior 20-day high"),
                ("LARGE_VOLUME_EVENT",history[history.volume_ratio20>=1.8],"official volume ratio 20 >= 1.8"),
                ("GAP_EVENT",history[history.gap_pct.abs()>=2],"absolute opening gap >= 2%"))
        for kind,matches,reason in events:
            if not matches.empty:
                event=matches.iloc[-1]; anchors.append((kind,event.market_date,event.market_date,float(event.close),reason))
        daily_avwaps=[item for kind,day,confirmed,price,reason in anchors if (item:=_avwap(frame,
            anchor_type=kind,anchor_date=day,confirmation_date=confirmed,anchor_price=price,
            derivation=reason,as_of=row.market_date,ruleset=ruleset_version))]
        avwaps.extend(daily_avwaps)
        candidates=[]
        for p in confirmed[-12:]: candidates.append((p.price,"CONFIRMED_SWING_"+p.pivot_kind,"confirmed pivot available "+str(p.confirmation_date),p.confirmation_date))
        for window in (20,60,120):
            value=row[f"ma{window}"]
            if pd.notna(value): candidates.append((float(value),f"MA{window}",f"{window}-day moving average",row.market_date))
        for item in daily_avwaps: candidates.append((item.avwap,item.anchor_type+"_AVWAP",item.derivation,item.confirmation_date))
        if pd.notna(row.prior_high20) and row.close>row.prior_high20: candidates.append((float(row.prior_high20),"BREAKOUT_LEVEL","prior 20-day high crossed on close",row.market_date))
        if pd.notna(row.prior_low20) and row.close<row.prior_low20: candidates.append((float(row.prior_low20),"BREAKDOWN_LEVEL","prior 20-day low crossed on close",row.market_date))
        support=_cluster(candidates,float(row.close),"SUPPORT",tolerance_pct/100); resistance=_cluster(candidates,float(row.close),"RESISTANCE",tolerance_pct/100)
        day_zones=[]
        for kind,item in (("SUPPORT",support),("RESISTANCE",resistance)):
            if item:
                zone=LocationZone(ticker=str(row.ticker),market_date=row.market_date,zone_type=kind,rank=1,
                    zone_low=item[0],zone_high=item[1],level_types=item[2],derivations=item[3],strength_class=item[4],
                    source_dates=sorted({pd.to_datetime(d["source_date"]).date() for d in item[3]}),ruleset_version=ruleset_version,
                    created_at=datetime.now(timezone.utc)); zones.append(zone); day_zones.append(zone)
        s=next((z for z in day_zones if z.zone_type=="SUPPORT"),None); r=next((z for z in day_zones if z.zone_type=="RESISTANCE"),None)
        ds=None if not s else (row.close-s.zone_high)/row.close*100; dr=None if not r else (r.zone_low-row.close)/row.close*100
        previous=None if index==0 else frame.iloc[index-1].close
        if r and previous is not None and previous<=r.zone_high<row.close: state="BREAKOUT_ZONE"
        elif s and previous is not None and previous>=s.zone_low>row.close: state="BREAKDOWN_ZONE"
        elif ds is not None and ds<=at_pct: state="AT_SUPPORT"
        elif dr is not None and dr<=at_pct: state="AT_RESISTANCE"
        elif ds is not None and ds<=near_pct: state="NEAR_SUPPORT"
        elif dr is not None and dr<=near_pct: state="NEAR_RESISTANCE"
        elif s and r: state="MID_RANGE"
        else: state="NO_CLEAR_LOCATION"
        observations=[{"metric":"support_zone","low":s.zone_low,"high":s.zone_high} for _ in [0] if s]+[{"metric":"resistance_zone","low":r.zone_low,"high":r.zone_high} for _ in [0] if r]
        states.append(LocationState(ticker=str(row.ticker),market_date=row.market_date,state=state,close=float(row.close),
            support_zone_low=s.zone_low if s else None,support_zone_high=s.zone_high if s else None,
            resistance_zone_low=r.zone_low if r else None,resistance_zone_high=r.zone_high if r else None,
            distance_support_pct=ds,distance_resistance_pct=dr,observations=observations,
            missing_inputs=[] if day_zones else ["auditable_levels"],source_dates=sorted({d for z in day_zones for d in z.source_dates}),
            ruleset_version=ruleset_version,created_at=datetime.now(timezone.utc)))
    return avwaps,zones,states
