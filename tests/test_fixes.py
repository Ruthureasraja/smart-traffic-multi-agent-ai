"""Regression tests for fixes made after the first review."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from agents.traffic_agent import TrafficSignalAgent
from simulation.simulation_engine import run_simulation, VALID_ARCHITECTURES
from simulation.traffic_generator import (get_default_scenario, load_scenario_from_csv,
                                          perturb_scenario, MAX_INPUT_VALUE)


def test_junction_that_needs_time_never_donates():
    """LOW density but waiting > 60s: it is itself needy, so it must not donate."""
    a = TrafficSignalAgent("S", 10, 80)
    assert a.density == "LOW"
    assert a.can_donate(10) is False


def test_all_architectures_do_not_drain_a_needy_low_density_junction():
    sc = [
        {"agent_id": "Signal_1", "vehicle_count": 90, "waiting_time": 70, "emergency_vehicle": False},
        {"agent_id": "Signal_2", "vehicle_count": 10, "waiting_time": 80, "emergency_vehicle": False},
    ]
    for arch in VALID_ARCHITECTURES:
        agents = {a.agent_id: a for a in run_simulation(sc, arch)["agents"]}
        assert agents["Signal_2"].green_time >= agents["Signal_2"].initial_green_time


def test_total_green_time_is_conserved():
    """Negotiation only moves time between junctions; it never creates or destroys it."""
    sc = get_default_scenario()
    for arch in VALID_ARCHITECTURES:
        agents = run_simulation(sc, arch)["agents"]
        assert sum(a.green_time for a in agents) == sum(a.initial_green_time for a in agents)


def test_csv_matches_default_scenario():
    assert load_scenario_from_csv() == get_default_scenario()


def test_csv_missing_columns_raises(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("agent_id,vehicle_count\nS1,10\n")
    try:
        load_scenario_from_csv(str(p)); assert False
    except ValueError:
        pass


def test_perturb_respects_dashboard_limits():
    data = [{"agent_id": "S", "vehicle_count": MAX_INPUT_VALUE, "waiting_time": 0, "emergency_vehicle": False}]
    for _ in range(200):
        data = perturb_scenario(data, max_change=8)
        assert 0 <= data[0]["vehicle_count"] <= MAX_INPUT_VALUE
        assert 0 <= data[0]["waiting_time"] <= MAX_INPUT_VALUE
