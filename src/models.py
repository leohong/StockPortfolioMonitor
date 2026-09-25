from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Holding(BaseModel):
    ticker: str = Field(pattern=r"^\d{4,6}$")
    name: str
    cost: float | None = Field(default=None, ge=0)
    quantity_lots: float | None = Field(default=None, ge=0)
    horizon: str = "swing"


class OHLCV(BaseModel):
    ticker: str
    market_date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None
    turnover: int | None
    source: str
    source_type: Literal["official_exchange"] = "official_exchange"
    is_official: bool = True
    retrieved_at: datetime
    volume_unit: str = "shares"
    turnover_unit: str = "TWD"
    source_note: str = ""


class QualityResult(BaseModel):
    status: Literal["PASS", "PASS_WITH_WARNINGS", "FAIL"]
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class InstitutionalDaily(BaseModel):
    ticker: str
    market_date: date
    foreign_net: int
    investment_trust_net: int
    dealer_net: int
    institutional_total_net: int
    source: str
    source_type: Literal["official_exchange"] = "official_exchange"
    is_official: bool = True
    retrieved_at: datetime
    unit: Literal["shares"] = "shares"


class MarginDaily(BaseModel):
    ticker: str
    market_date: date
    margin_buy: int
    margin_sell: int
    margin_cash_repayment: int
    margin_balance: int
    short_sell: int
    short_cover: int
    short_stock_repayment: int
    short_balance: int
    source: str
    source_type: Literal["official_exchange"] = "official_exchange"
    is_official: bool = True
    retrieved_at: datetime
    unit: Literal["trading_units"] = "trading_units"
    source_note: str = ""


class PricePivot(BaseModel):
    ticker: str
    pivot_date: date
    confirmation_date: date
    pivot_kind: Literal["HIGH", "LOW"]
    price: float
    structure_label: Literal["HH", "HL", "LH", "LL"] | None = None
    comparison_date: date | None = None
    comparison_price: float | None = None
    signal_type: Literal["REAL_TIME_SIGNAL"] = "REAL_TIME_SIGNAL"
    annotation_type: Literal["RETROSPECTIVE_ANNOTATION"] = "RETROSPECTIVE_ANNOTATION"


class StructureSnapshot(BaseModel):
    ticker: str
    market_date: date
    state: Literal["UPTREND_STRUCTURE", "DOWNTREND_STRUCTURE", "POSSIBLE_BASE", "POSSIBLE_TOP", "RANGE", "UNCONFIRMED"]
    high_label: str | None = None
    high_pivot_date: date | None = None
    high_price: float | None = None
    low_label: str | None = None
    low_pivot_date: date | None = None
    low_price: float | None = None


class PriceLevel(BaseModel):
    ticker: str
    market_date: date
    level_type: Literal["SUPPORT", "RESISTANCE"]
    rank: int
    price: float
    derivation: str
    evidence_date: date
    source_confirmation_date: date | None = None
