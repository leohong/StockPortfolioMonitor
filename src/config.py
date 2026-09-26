from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from src.models import Holding

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    database: Path
    cache_dir: Path
    history_months: int = Field(default=15, ge=13, le=120)
    stale_days: int = Field(default=7, ge=1)
    pivot_left_bars: int = Field(default=3, ge=1, le=20)
    pivot_right_bars: int = Field(default=3, ge=1, le=20)
    level_tolerance_pct: float = Field(default=2.0, gt=0, le=10)
    trend_extended_distance_pct: float = Field(default=8.0, gt=0, le=30)
    trend_persistence_min: float = Field(default=0.7, ge=0.5, le=1)
    rs_leading_20d_pct: float = Field(default=3.0, ge=0, le=30)
    rs_leading_60d_pct: float = Field(default=5.0, ge=0, le=50)


def load_config(root: Path = ROOT):
    settings = Settings(**yaml.safe_load((root / "config/settings.yaml").read_text("utf-8")))
    settings.database = root / settings.database
    settings.cache_dir = root / settings.cache_dir
    holdings = [Holding(**h) for h in yaml.safe_load((root / "config/holdings.yaml").read_text("utf-8"))["holdings"]]
    if not holdings or len(holdings) > 100 or len({h.ticker for h in holdings}) != len(holdings):
        raise ValueError("Holdings must contain 1–100 unique tickers")
    source = yaml.safe_load((root / "config/sources.yaml").read_text("utf-8"))["twse"]
    if source["endpoint"] != "https://www.twse.com.tw/exchangeReport/STOCK_DAY":
        raise ValueError("Phase 1 supports the official TWSE STOCK_DAY endpoint only")
    return settings, holdings, source
