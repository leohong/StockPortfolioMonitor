from __future__ import annotations

import json
from src.database.db import connect


def _observations(rows, horizon=20):
    output = []
    for index, row in enumerate(rows):
        if index + horizon >= len(rows):
            break
        payload = json.loads(row[2])
        output.append({"date": row[0], "state": payload["market_state"],
                       "return": (rows[index + horizon][1] / row[1] - 1) * 100})
    return output


def _profile(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["state"], []).append(row["return"])
    return {state: sum(values) / len(values) for state, values in grouped.items()}


def _agreement(rows, profile):
    usable = [row for row in rows if row["state"] in profile and profile[row["state"]] != 0]
    if not usable:
        return None, 0
    matches = sum((row["return"] > 0) == (profile[row["state"]] > 0) for row in usable)
    return matches / len(usable), len(usable)


def walk_forward(settings, ticker: str, train_size=120, validation_size=40, forward_size=40,
                 horizon=20) -> list[dict]:
    """Expanding chronological evaluation; observations are never shuffled."""
    with connect(settings.database) as db:
        rows = db.execute("SELECT s.market_date,o.close,s.payload_json FROM snapshot_v3_daily s "
            "JOIN ohlcv_daily o USING(ticker,market_date) WHERE s.ticker=? "
            "AND s.ruleset_version='m6-evidence-market-state-v1' ORDER BY s.market_date", [ticker]).fetchall()
    observations = _observations(rows, horizon)
    results = []
    train_end = train_size
    while train_end + validation_size + forward_size <= len(observations):
        train = observations[:train_end]
        validation = observations[train_end:train_end + validation_size]
        forward = observations[train_end + validation_size:train_end + validation_size + forward_size]
        profile = _profile(train)
        validation_agreement, validation_n = _agreement(validation, profile)
        forward_agreement, forward_n = _agreement(forward, profile)
        results.append({"fold": len(results) + 1, "train_start": str(train[0]["date"]),
            "train_end": str(train[-1]["date"]), "validation_start": str(validation[0]["date"]),
            "validation_end": str(validation[-1]["date"]), "forward_start": str(forward[0]["date"]),
            "forward_end": str(forward[-1]["date"]), "horizon": horizon,
            "validation_direction_agreement": validation_agreement, "validation_samples": validation_n,
            "forward_direction_agreement": forward_agreement, "forward_samples": forward_n,
            "states_profiled": len(profile), "shuffled": False,
            "interpretation": "descriptive out-of-sample association; not a trading strategy"})
        train_end += forward_size
    return results
