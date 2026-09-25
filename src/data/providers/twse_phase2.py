import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.data.providers.twse import SourceError
from src.logging_config import event

INSTITUTIONAL_ENDPOINT = "https://www.twse.com.tw/rwd/zh/fund/T86"
MARGIN_ENDPOINT = "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"


@retry(stop=stop_after_attempt(8), wait=wait_exponential(min=5, max=30),
       retry=retry_if_exception_type(httpx.HTTPError), reraise=True)
def fetch_daily(dataset: str, market_date: date, cache_dir: Path, client: httpx.Client | None = None,
                force: bool = False) -> dict:
    if dataset not in {"institutional", "margin"}:
        raise ValueError("Unsupported Phase 2 dataset")
    endpoint = INSTITUTIONAL_ENDPOINT if dataset == "institutional" else MARGIN_ENDPOINT
    params = {"date": market_date.strftime("%Y%m%d"), "response": "json",
              "selectType": "ALLBUT0999" if dataset == "institutional" else "ALL"}
    target = cache_dir / dataset
    target.mkdir(parents=True, exist_ok=True)
    if not force:
        cached = sorted(path for path in target.glob(f"{market_date:%Y%m%d}_*.json") if ".metadata." not in path.name)
        if cached:
            archive = cached[-1]
            payload = json.loads(archive.read_text("utf-8"))
            if payload.get("stat") == "OK" and payload.get("date") == market_date.strftime("%Y%m%d"):
                metadata_path = archive.with_name(f"{archive.stem}.metadata.json")
                metadata = json.loads(metadata_path.read_text("utf-8"))
                return {**metadata, "payload": payload}
    event("DATA_FETCH_START", dataset=dataset, market_date=market_date)
    owns_client = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=True)
    try:
        response = client.get(endpoint, params=params)
        response.raise_for_status()
    finally:
        if owns_client:
            client.close()
    retrieved_at = datetime.now(timezone.utc).isoformat()
    digest = hashlib.sha256(response.content).hexdigest()
    archive = target / f"{market_date:%Y%m%d}_{digest[:12]}.json"
    archive.write_bytes(response.content)
    try:
        payload = response.json()
    except ValueError as exc:
        raise SourceError(f"TWSE returned non-JSON; archived at {archive}") from exc
    envelope = {"source": str(response.url), "source_type": "official_exchange", "is_official": True,
                "retrieved_at": retrieved_at, "sha256": digest, "archive": str(archive), "payload": payload}
    metadata = {key: value for key, value in envelope.items() if key != "payload"}
    (target / f"{market_date:%Y%m%d}_{digest[:12]}.metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), "utf-8")
    if payload.get("stat") != "OK" or payload.get("date") != market_date.strftime("%Y%m%d"):
        raise SourceError(f"TWSE {dataset} unavailable or date mismatch for {market_date}: {payload.get('stat')}")
    event("DATA_FETCH_SUCCESS", dataset=dataset, market_date=market_date, sha256=digest)
    return envelope
