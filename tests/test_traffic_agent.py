"""Tests for TrafficSignalAgent: validation and green-time donation rules."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from agents.traffic_agent import TrafficSignalAgent


def test_agent_does_not_decide_its_own_colour():
    """
    REGRESSION TEST for the bug faculty reported.
    An agent must NOT set its own light colour - it cannot know whose turn
    it is. It always starts RED and SignalPhaseController assigns the real
    colour. The old buggy line was:
        self.signal_state = "GREEN" if emergency_vehicle else "RED"
    """
    for vc in [5, 25, 50, 80, 150]:
        assert TrafficSignalAgent("S", vc, 20).signal_state == "RED"


def test_emergency_agent_is_flagged_for_priority():
    a = TrafficSignalAgent("S", 80, 70, emergency_vehicle=True)
    assert a.has_priority is True
    assert a.green_time == 60


def test_negative_inputs_raise_errors():
    for kwargs in [dict(vehicle_count=-5, waiting_time=10),
                   dict(vehicle_count=10, waiting_time=-5)]:
        try:
            TrafficSignalAgent("S", **kwargs); assert False
        except ValueError:
            pass


def test_can_donate_only_when_low_density_and_above_floor():
    low = TrafficSignalAgent("S1", 10, 5)          # green_time = 20
    assert low.can_donate(10) is True              # 20-10 = 10 >= floor(10)
    assert low.can_donate(15) is False             # 20-15 = 5  <  floor(10)
    assert TrafficSignalAgent("S2", 80, 5).can_donate(5) is False   # HIGH never donates


def test_donate_and_receive_update_green_time():
    donor, needy = TrafficSignalAgent("S1", 10, 5), TrafficSignalAgent("S2", 80, 65)
    d0, n0 = donor.green_time, needy.green_time
    donor.donate(10); needy.receive_donation(10)
    assert donor.green_time == d0 - 10
    assert needy.green_time == n0 + 10
    assert "Received an additional" in needy.reason
