from datetime import date,timedelta
import pandas as pd
import pytest

from src.analysis.location import calculate_location
from src.analysis.volatility import calculate_volatility
from src.models import PricePivot

RULES="m5-test"


def stock(count=130):
    days=[date(2026,1,1)+timedelta(days=i) for i in range(count)]
    close=[100+i*.1 for i in range(count)]
    return pd.DataFrame({"ticker":"3702","market_date":days,"open":close,
        "high":[x+1 for x in close],"low":[x-1 for x in close],"close":close,
        "volume":[1000+i for i in range(count)],"turnover":[100000]*count})


def test_volatility_has_atr_historical_vol_and_directionless_state():
    result=calculate_volatility(stock(),RULES)[-1]
    assert result.atr14==pytest.approx(2)
    assert result.historical_volatility_20d is not None
    assert result.state in {"COMPRESSED","NORMAL","EXPANDING","HIGH","SHOCK"}
    assert all("direction" not in item for item in result.observations)


def test_avwap_waits_for_confirmation_and_is_auditable():
    data=stock(40); days=data.market_date.tolist()
    pivot=PricePivot(ticker="3702",pivot_date=days[10],confirmation_date=days[13],pivot_kind="LOW",price=float(data.low.iloc[10]))
    avwaps,zones,states=calculate_location(data,[pivot],RULES)
    assert not [x for x in avwaps if x.market_date < pivot.confirmation_date]
    first=next(x for x in avwaps if x.market_date==pivot.confirmation_date)
    history=data[(data.market_date>=pivot.pivot_date)&(data.market_date<=pivot.confirmation_date)]
    expected=((((history.high+history.low+history.close)/3)*history.volume).sum()/history.volume.sum())
    assert first.avwap==pytest.approx(expected)
    assert first.anchor_date==pivot.pivot_date and first.confirmation_date==pivot.confirmation_date
    assert first.source_dates[0]==pivot.pivot_date


def test_future_confirmed_pivot_cannot_affect_historical_zones():
    data=stock(40); days=data.market_date.tolist(); cutoff=days[25]
    safe=PricePivot(ticker="3702",pivot_date=days[10],confirmation_date=days[13],pivot_kind="LOW",price=99)
    future=PricePivot(ticker="3702",pivot_date=days[20],confirmation_date=days[30],pivot_kind="HIGH",price=500)
    _,zones_with,states_with=calculate_location(data,[safe,future],RULES)
    _,zones_safe,states_safe=calculate_location(data,[safe],RULES)
    before=lambda rows:[x.model_dump(exclude={"created_at"}) for x in rows if x.market_date<=cutoff]
    assert before(zones_with)==before(zones_safe)
    assert before(states_with)==before(states_safe)


def test_zones_keep_derivations_and_tick_precision():
    data=stock(); days=data.market_date.tolist()
    pivots=[PricePivot(ticker="3702",pivot_date=days[80],confirmation_date=days[83],pivot_kind="LOW",price=108.03)]
    _,zones,_=calculate_location(data,pivots,RULES,tolerance_pct=3)
    latest=[x for x in zones if x.market_date==days[-1]]
    assert latest and all(zone.derivations and zone.level_types for zone in latest)
    assert all((zone.zone_low*2).is_integer() and (zone.zone_high*2).is_integer() for zone in latest)
