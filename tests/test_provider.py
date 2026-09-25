import json
from datetime import date

import httpx
import pytest

from src.data.providers.twse import fetch_month, SourceError


@pytest.mark.parametrize("mode", ["valid", "empty", "wrong_ticker", "wrong_month", "html"])
def test_provider_archive_and_source_contract(tmp_path, envelope, monkeypatch, mode):
    payload = envelope["payload"]
    if mode == "empty":
        payload["stat"] = "No data"
    elif mode == "wrong_ticker":
        payload["title"] = "2330"
    elif mode == "wrong_month":
        payload["date"] = "20260701"
    class Client:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, url, params):
            request = httpx.Request("GET", url, params=params)
            return httpx.Response(200, content=b"<html>Unavailable</html>" if mode == "html" else json.dumps(payload).encode(), request=request)
    monkeypatch.setattr("src.data.providers.twse.httpx.Client", Client)
    if mode == "valid":
        result = fetch_month("3702", date(2026, 8, 1), tmp_path)
        assert result["is_official"] is True
        assert result["retrieved_at"].endswith("+00:00")
        assert len(result["sha256"]) == 64
    else:
        with pytest.raises(SourceError):
            fetch_month("3702", date(2026, 8, 1), tmp_path)
    assert list(tmp_path.glob("3702_202608_*.json"))
