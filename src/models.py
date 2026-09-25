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
