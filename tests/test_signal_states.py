"""
test_signal_states.py

Tests for the RED / YELLOW / GREEN state machine.

These exist specifically because faculty reported that every signal was
stuck on RED. Each test below maps to one of the scenarios raised in that
review, so they double as proof the reported problems are actually fixed.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from agents.traffic_agent import TrafficSignalAgent
from simulation.signal_controller import SignalPhaseController, GREEN, YELLOW, RED
from simulation.simulation_engine import run_simulation


def make(agent_id, vehicles, waiting=20, emergency=False):
    return TrafficSignalAgent(agent_id, vehicles, waiting, emergency)


# ---------------------------------------------------------------------
# Core state machine
# ---------------------------------------------------------------------
def test_exactly_one_junction_has_right_of_way_at_any_time():
    """Two junctions must never be GREEN simultaneously - that would crash cars."""
    agents = [make("S1", 75, 65), make("S2", 25, 15), make("S3", 50, 40), make("S4", 35, 25)]
    c = SignalPhaseController(agents)

    for t in range(0, c.cycle_length() + 5):
        states = c.states_at(t)
        assert list(states.values()).count(GREEN) <= 1
        assert sum(1 for v in states.values() if v in (GREEN, YELLOW)) == 1


def test_all_three_colours_appear_across_a_full_cycle():
    """RED, YELLOW and GREEN must all actually occur - not just RED."""
    agents = [make("S1", 75, 65), make("S2", 25, 15)]
    c = SignalPhaseController(agents)

    seen = set()
    for t in range(c.cycle_length()):
        seen.update(c.states_at(t).values())

    assert seen == {RED, YELLOW, GREEN}


def test_yellow_occurs_at_the_end_of_a_green_phase():
    """YELLOW is the transition between GREEN and RED, not a density label."""
    agents = [make("S1", 75, 65), make("S2", 25, 15)]
    c = SignalPhaseController(agents)
    phase = c.schedule[0]

    assert c.states_at(phase["green_end"] - 1)[phase["agent_id"]] == GREEN
    assert c.states_at(phase["green_end"])[phase["agent_id"]] == YELLOW
    assert c.states_at(phase["yellow_end"] - 1)[phase["agent_id"]] == YELLOW
    assert c.states_at(phase["yellow_end"])[phase["agent_id"]] == RED


def test_cycle_repeats_after_it_completes():
    agents = [make("S1", 75, 65), make("S2", 25, 15)]
    c = SignalPhaseController(agents)
    assert c.states_at(0) == c.states_at(c.cycle_length())


# ---------------------------------------------------------------------
# Faculty scenario 3: reducing vehicle count must NOT force RED
# ---------------------------------------------------------------------
def test_low_density_junction_still_gets_green_on_its_turn():
    """
    A LOW-density junction must still receive a GREEN phase when its turn
    arrives. It simply gets a SHORTER green phase, not a permanent RED.
    """
    agents = [make("S1", 75, 65), make("S2", 10, 5)]   # S2 is LOW density
    c = SignalPhaseController(agents)

    greens = [c.states_at(t)["S2"] for t in range(c.cycle_length())]
    assert GREEN in greens, "LOW-density junction never turned GREEN"


def test_reducing_vehicle_count_does_not_force_red():
    """Lowering the vehicle count must not flip a served junction to RED."""
    for vehicles in [80, 50, 20, 5]:
        agents = [make("S1", vehicles, 20), make("S2", 1, 1)]
        c = SignalPhaseController(agents)
        colours = {c.states_at(t)["S1"] for t in range(c.cycle_length())}
        assert GREEN in colours, f"S1 never turned GREEN at {vehicles} vehicles"


def test_density_does_not_map_directly_to_colour():
    """
    Explicitly guards against the wrong fix (LOW=RED, MEDIUM=YELLOW, HIGH=GREEN).
    Every density level must be able to show GREEN at some point.
    """
    for vehicles, density in [(10, "LOW"), (45, "MEDIUM"), (90, "HIGH")]:
        agents = [make("S1", vehicles, 20), make("S2", 30, 20)]
        assert agents[0].density == density
        c = SignalPhaseController(agents)
        colours = {c.states_at(t)["S1"] for t in range(c.cycle_length())}
        assert GREEN in colours, f"{density} density never showed GREEN"


# ---------------------------------------------------------------------
# Faculty scenario 4: HIGH traffic gets GREEN when it holds priority
# ---------------------------------------------------------------------
def test_high_traffic_junction_receives_green_and_a_longer_phase():
    agents = [make("S1", 90, 70), make("S2", 15, 10)]
    c = SignalPhaseController(agents)

    assert c.states_at(0)["S1"] == GREEN        # busiest is served first
    assert c.states_at(0)["S2"] == RED

    phases = {p["agent_id"]: p["green_seconds"] for p in c.schedule}
    assert phases["S1"] > phases["S2"], "HIGH density should get a longer green phase"


# ---------------------------------------------------------------------
# Faculty scenario 5: emergency priority (must keep working)
# ---------------------------------------------------------------------
def test_emergency_vehicle_gets_green_immediately_and_others_red():
    agents = [make("S1", 90, 70), make("S2", 20, 10, emergency=True), make("S3", 50, 30)]
    c = SignalPhaseController(agents)
    states = c.states_at(0)

    assert states["S2"] == GREEN, "Emergency junction must be GREEN immediately"
    assert states["S1"] == RED and states["S3"] == RED
    assert c.schedule[0]["agent_id"] == "S2"    # served first in the cycle


def test_emergency_beats_a_busier_non_emergency_junction():
    agents = [make("S1", 200, 200), make("S2", 5, 5, emergency=True)]
    c = SignalPhaseController(agents)
    assert c.states_at(0)["S2"] == GREEN


# ---------------------------------------------------------------------
# Integration with the wider simulation
# ---------------------------------------------------------------------
def test_signal_states_change_as_simulation_time_advances():
    """The exact bug faculty saw: colours stuck on RED forever."""
    scenario = [
        {"agent_id": "Signal_1", "vehicle_count": 75, "waiting_time": 65, "emergency_vehicle": False},
        {"agent_id": "Signal_2", "vehicle_count": 25, "waiting_time": 15, "emergency_vehicle": False},
    ]
    seen = set()
    for t in range(0, 200, 5):
        result = run_simulation(scenario, "Decentralized", elapsed_seconds=t)
        seen.update(a.signal_state for a in result["agents"])

    assert GREEN in seen and RED in seen, "Signals never changed over time"


def test_all_architectures_produce_valid_signal_states():
    scenario = [
        {"agent_id": "Signal_1", "vehicle_count": 75, "waiting_time": 65, "emergency_vehicle": False},
        {"agent_id": "Signal_2", "vehicle_count": 25, "waiting_time": 15, "emergency_vehicle": False},
        {"agent_id": "Signal_3", "vehicle_count": 50, "waiting_time": 40, "emergency_vehicle": False},
    ]
    for arch in ["Centralized", "Hierarchical", "Decentralized"]:
        result = run_simulation(scenario, arch, elapsed_seconds=0)
        states = [a.signal_state for a in result["agents"]]
        assert all(s in (RED, YELLOW, GREEN) for s in states)
        assert states.count(GREEN) == 1, f"{arch} must have exactly one GREEN"


def test_controller_rejects_empty_agent_list():
    try:
        SignalPhaseController([]); assert False
    except ValueError:
        pass


def test_negative_elapsed_time_rejected():
    c = SignalPhaseController([make("S1", 30, 20)])
    try:
        c.states_at(-5); assert False
    except ValueError:
        pass
