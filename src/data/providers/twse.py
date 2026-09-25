import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.logging_config import event

ENDPOINT = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"


class SourceError(ValueError):
    pass


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=4),
       retry=retry_if_exception_type(httpx.HTTPError), reraise=True)
def fetch_month(ticker: str, month: date, cache_dir: Path) -> dict:
    if not ticker.isdigit() or not 4 <= len(ticker) <= 6:
        raise ValueError("Invalid ticker")
    params = {"response": "json", "date": month.strftime("%Y%m01"), "stockNo": ticker}
    event("DATA_FETCH_START", ticker=ticker, month=month)
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(ENDPOINT, params=params)
        response.raise_for_status()
    retrieved = datetime.now(timezone.utc).isoformat()
    # Preserve even unexpected responses for diagnosis; never invent replacement rows.
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(response.content).hexdigest()
    archive = cache_dir / f"{ticker}_{month:%Y%m}_{digest[:12]}.json"
    archive.write_bytes(response.content)
    try:
        payload = response.json()
    except ValueError as exc:
        raise SourceError(f"TWSE returned non-JSON; archived at {archive}") from exc
    envelope = {"source": str(response.url), "source_type": "official_exchange", "is_official": True,
                "retrieved_at": retrieved, "sha256": digest, "archive": str(archive), "payload": payload}
    (cache_dir / f"{ticker}_{month:%Y%m}_{digest[:12]}.metadata.json").write_text(json.dumps({k:v for k,v in envelope.items() if k != "payload"}, indent=2), "utf-8")
    if payload.get("stat") != "OK" or not payload.get("data"):
        raise SourceError(f"TWSE unavailable/empty for {ticker} {month:%Y-%m}: {payload.get('stat')}")
    if payload.get("date") != month.strftime("%Y%m01") or ticker not in payload.get("title", ""):
        raise SourceError("TWSE response does not match requested ticker/month")
    event("DATA_FETCH_SUCCESS", ticker=ticker, month=month, rows=len(payload["data"]), sha256=digest)
    return envelope
