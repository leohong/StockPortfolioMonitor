from datetime import date, timedelta

from src.evaluation.event_study import _label, _median
from src.evaluation.performance import benchmark
from src.evaluation.robustness import classify_stability, state_agreement
from src.evaluation.walk_forward import _agreement, _observations, _profile


class State:
    def __init__(self, day, state, participant=None):
        self.market_date = day
        self.state = state
        self.participant = participant


def test_robustness_agreement_flags_small_parameter_collapse():
    day = date(2026, 1, 1)
    baseline = [State(day + timedelta(days=i), "A") for i in range(10)]
    stable = [State(day + timedelta(days=i), "B" if i == 0 else "A") for i in range(10)]
    sensitive = [State(day + timedelta(days=i), "B" if i < 4 else "A") for i in range(10)]
    assert classify_stability(state_agreement(baseline, stable)) == "STABLE"
    assert classify_stability(state_agreement(baseline, sensitive)) == "SENSITIVE"


def test_walk_forward_helpers_are_chronological_and_do_not_shuffle():
    day = date(2025, 1, 1)
    rows = [(day + timedelta(days=i), 100 + i, '{"market_state":"S4_TREND"}') for i in range(30)]
    observations = _observations(rows, horizon=5)
    assert observations[0]["date"] < observations[-1]["date"]
    profile = _profile(observations[:10])
    agreement, count = _agreement(observations[10:], profile)
    assert count == len(observations[10:])
    assert agreement == 1


def test_event_study_labels_and_distribution_median_are_deterministic():
    assert _label("location", "BREAKDOWN_ZONE") == "support_break"
    assert _label("momentum", "NEGATIVE") == "momentum:NEGATIVE"
    assert _median([4, 1, 3, 2]) == 2.5


def test_performance_benchmark_records_repeatable_operation_shape():
    result = benchmark("sample", lambda: [1, 2, 3], repeats=2)
    assert result["operation"] == "sample"
    assert result["repeats"] == 2
    assert result["result_size"] == 3
    assert 0 <= result["median_ms"] <= result["max_ms"]
