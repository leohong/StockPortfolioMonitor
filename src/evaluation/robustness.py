from __future__ import annotations


def state_agreement(baseline, candidate) -> dict:
    base = {(item.market_date, getattr(item, "participant", None)): item.state for item in baseline}
    other = {(item.market_date, getattr(item, "participant", None)): item.state for item in candidate}
    keys = sorted(set(base) & set(other))
    matches = sum(base[key] == other[key] for key in keys)
    return {"observations": len(keys), "agreement": matches / len(keys) if keys else None,
            "changed": len(keys) - matches}


def classify_stability(result: dict, threshold=.8) -> str:
    agreement = result.get("agreement")
    return "INSUFFICIENT_DATA" if agreement is None else "STABLE" if agreement >= threshold else "SENSITIVE"
