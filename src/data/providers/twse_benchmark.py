from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.data.providers.twse import SourceError


TAIEX_OHLC_ENDPOINT = "https://www.twse.com.tw/indicesReport/MI_5MINS_HIST"
TAIEX_MARKET_ENDPOINT = "https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK"
SECTOR_CLASSIFICATION_ENDPOINT = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"


def _json(response: httpx.Response):
    try:
        return json.loads(response.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceError(f"TWSE returned invalid UTF-8 JSON from {response.url}") from exc


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=4),
       retry=retry_if_exception_type(httpx.HTTPError), reraise=True)
def fetch_taiex_month(month: date, cache_dir: Path, client: httpx.Client | None = None, force: bool = False) -> dict:
    target = cache_dir / "benchmark" / "taiex"
    target.mkdir(parents=True, exist_ok=True)
    if not force:
        cached = sorted(path for path in target.glob(f"{month:%Y%m}_*.json") if ".metadata." not in path.name)
        if cached:
            archive = cached[-1]
            payload = json.loads(archive.read_text("utf-8"))
            metadata = json.loads(archive.with_name(f"{archive.stem}.metadata.json").read_text("utf-8"))
            return {**metadata, "payload": payload}
    owns_client = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=True)
    params = {"date": month.strftime("%Y%m01"), "response": "json"}
    try:
        ohlc_response = client.get(TAIEX_OHLC_ENDPOINT, params=params)
        market_response = client.get(TAIEX_MARKET_ENDPOINT, params=params)
        ohlc_response.raise_for_status(); market_response.raise_for_status()
    finally:
        if owns_client:
            client.close()
    ohlc, market = _json(ohlc_response), _json(market_response)
    if ohlc.get("stat") != "OK" or market.get("stat") != "OK":
        raise SourceError(f"TWSE TAIEX unavailable for {month:%Y-%m}")
    if ohlc.get("date") != params["date"] or market.get("date") != params["date"]:
        raise SourceError("TWSE TAIEX response month mismatch")
    payload = {"ohlc": ohlc, "market": market}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    archive = target / f"{month:%Y%m}_{digest[:12]}.json"
    archive.write_bytes(raw)
    metadata = {"source": f"{ohlc_response.url} | {market_response.url}", "source_type": "official_exchange",
        "is_official": True, "retrieved_at": datetime.now(timezone.utc).isoformat(), "sha256": digest, "archive": str(archive)}
    archive.with_name(f"{archive.stem}.metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), "utf-8")
    return {**metadata, "payload": payload}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=4),
       retry=retry_if_exception_type(httpx.HTTPError), reraise=True)
def fetch_sector_classification(cache_dir: Path, client: httpx.Client | None = None, force: bool = False) -> dict:
    target = cache_dir / "classification"
    target.mkdir(parents=True, exist_ok=True)
    if not force:
        cached = sorted(path for path in target.glob("twse_listed_*.json") if ".metadata." not in path.name)
        if cached:
            archive = cached[-1]
            payload = json.loads(archive.read_text("utf-8"))
            metadata = json.loads(archive.with_name(f"{archive.stem}.metadata.json").read_text("utf-8"))
            return {**metadata, "payload": payload}
    owns_client = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=True)
    try:
        response = client.get(SECTOR_CLASSIFICATION_ENDPOINT)
        response.raise_for_status()
    finally:
        if owns_client:
            client.close()
    payload = _json(response)
    if not isinstance(payload, list) or not payload:
        raise SourceError("TWSE sector classification is empty")
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    retrieved = datetime.now(timezone.utc)
    archive = target / f"twse_listed_{retrieved:%Y%m%d}_{digest[:12]}.json"
    archive.write_bytes(raw)
    metadata = {"source": str(response.url), "source_type": "official_exchange", "is_official": True,
        "retrieved_at": retrieved.isoformat(), "sha256": digest, "archive": str(archive)}
    archive.with_name(f"{archive.stem}.metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), "utf-8")
    return {**metadata, "payload": payload}
