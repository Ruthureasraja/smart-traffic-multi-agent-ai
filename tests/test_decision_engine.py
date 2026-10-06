"""Tests for the pure decision logic (no agents, no UI, no randomness)."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from decision.decision_engine import (base_decision, classify_density,
                                       estimate_waiting_time_after, priority_score)


def test_density_boundaries():
    assert classify_density(0) == "LOW"
    assert classify_density(30) == "LOW"
    assert classify_density(31) == "MEDIUM"
    assert classify_density(60) == "MEDIUM"
    assert classify_density(61) == "HIGH"


def test_negative_vehicle_count_raises():
    try:
        classify_density(-1); assert False
    except ValueError:
        pass


def test_base_decision_high_density_with_waiting_boost():
    r = base_decision(75, 65)
    assert r["density"] == "HIGH"
    assert r["green_time"] == 65          # 50 base + 15 boost
    assert "priority boost" in r["reason"]


def test_base_decision_no_boost_below_threshold():
    r = base_decision(25, 15)
    assert r["density"] == "LOW"
    assert r["green_time"] == 20
    assert "priority boost" not in r["reason"]


def test_emergency_overrides_everything():
    r = base_decision(10, 5, emergency_vehicle=True)
    assert r["green_time"] == 60
    assert "Emergency" in r["reason"]


def test_priority_score_weights_waiting_time_higher():
    assert priority_score(50, 90) > priority_score(50, 30)


def test_estimate_waiting_time_no_change_if_green_not_increased():
    assert estimate_waiting_time_after(60, 20, 20) == 60.0


def test_estimate_waiting_time_improves_with_more_green():
    assert estimate_waiting_time_after(60, 20, 40) == 30.0


def test_estimate_waiting_time_rejects_zero_green():
    try:
        estimate_waiting_time_after(60, 20, 0); assert False
    except ValueError:
        pass
