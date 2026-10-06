"""End-to-end tests for the full simulation across all three architectures."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from simulation.simulation_engine import run_simulation, VALID_ARCHITECTURES
from simulation.traffic_generator import get_default_scenario, generate_random_scenario
from visualization.charts import architecture_diagram


def test_all_architectures_run_without_error():
    sc = get_default_scenario()
    for arch in VALID_ARCHITECTURES:
        r = run_simulation(sc, arch)
        assert r["comm_log"] and r["avg_waiting_before"] > 0


def test_negotiation_actually_improves_waiting_time():
    """Regression test: donation constants must allow donation to happen."""
    sc = get_default_scenario()
    for arch in VALID_ARCHITECTURES:
        assert run_simulation(sc, arch)["improvement_pct"] > 0, f"{arch} gave no improvement"


def test_decentralized_has_no_controller_in_the_message_log():
    r = run_simulation(get_default_scenario(), "Decentralized")
    parties = {m["sender"] for m in r["comm_log"]} | {m["receiver"] for m in r["comm_log"]}
    assert "Central_Controller" not in parties
    assert "Traffic_Manager" not in parties


def test_invalid_architecture_raises():
    try:
        run_simulation(get_default_scenario(), "NotReal"); assert False
    except ValueError:
        pass


def test_empty_junction_data_raises():
    try:
        run_simulation([], "Centralized"); assert False
    except ValueError:
        pass


def test_architecture_diagram_scales_to_any_junction_count():
    for n in [2, 3, 4, 5, 6]:
        ids = [j["agent_id"] for j in generate_random_scenario(n, seed=1)]
        for arch in VALID_ARCHITECTURES:
            fig = architecture_diagram(arch, ids)
            text = [t for tr in fig.data if tr.text for t in tr.text]
            for aid in ids:
                assert aid in text, f"{aid} missing from {arch} diagram (n={n})"


def test_generate_random_scenario_respects_count():
    sc = generate_random_scenario(5, seed=42)
    assert len(sc) == 5
    assert all(j["vehicle_count"] >= 0 and j["waiting_time"] >= 0 for j in sc)
