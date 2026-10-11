"""
traffic_agent.py

TrafficSignalAgent represents ONE independent traffic junction.

- In the Decentralized architecture, these agents talk to each other
  DIRECTLY, with no controller at all.
- In the Centralized and Hierarchical architectures, these same agent
  objects are treated as "workers" that a Central Controller or
  Area/Traffic Manager coordinates.

Using the SAME agent class across all three architectures (only the
coordination logic around them changes) is intentional - it mirrors
your original Multi-Agent Communication Framework's design.
"""

from decision.decision_engine import (base_decision, priority_score, MIN_GREEN_TIME,
                                       WAITING_TIME_ALERT)


class TrafficSignalAgent:
    """One independent traffic-signal junction agent."""

    def __init__(self, agent_id: str, vehicle_count: int, waiting_time: int,
                 emergency_vehicle: bool = False):
        if vehicle_count < 0:
            raise ValueError(f"{agent_id}: vehicle_count cannot be negative.")
        if waiting_time < 0:
            raise ValueError(f"{agent_id}: waiting_time cannot be negative.")

        self.agent_id = agent_id
        self.vehicle_count = vehicle_count
        self.waiting_time = waiting_time
        self.emergency_vehicle = emergency_vehicle

        decision = base_decision(vehicle_count, waiting_time, emergency_vehicle)
        self.density = decision["density"]
        self.green_time = decision["green_time"]
        self.initial_green_time = decision["green_time"]   # kept for before/after comparison
        self.reason = decision["reason"]
        # -------------------------------------------------------------
        # SIGNAL STATE (RED / YELLOW / GREEN)
        # -------------------------------------------------------------
        # This starts as RED and is NOT decided here. The colour depends on
        # whose TURN it is right now across the whole network, which a
        # single agent cannot know on its own. SignalPhaseController (in
        # simulation/signal_controller.py) builds the right-of-way cycle
        # and then overwrites this value via apply_to_agents().
        #
        # This is the line that used to read:
        #     self.signal_state = "GREEN" if emergency_vehicle else "RED"
        # which hard-coded every non-emergency junction to RED forever,
        # no matter what the vehicle count or the simulation was doing.
        self.signal_state = "RED"

        # Whether this junction is being prioritised in the service order.
        # Emergency junctions are always served first in the cycle.
        self.has_priority = emergency_vehicle

    def priority(self) -> float:
        """Higher = more urgent need for additional green time."""
        return priority_score(self.vehicle_count, self.waiting_time)

    def can_donate(self, amount: int) -> bool:
        """
        A junction can donate green time to a neighbor ONLY if:
        - it currently has LOW density (it doesn't need the time itself)
        - donating won't drop it below the safety floor (MIN_GREEN_TIME)
        - it doesn't have an emergency vehicle waiting
        - it is not itself waiting longer than the alert threshold (a junction
          that needs more time must never give time away)
        """
        return (
            self.density == "LOW"
            and not self.emergency_vehicle
            and self.waiting_time <= WAITING_TIME_ALERT
            and (self.green_time - amount) >= MIN_GREEN_TIME
        )

    def donate(self, amount: int) -> None:
        self.green_time -= amount

    def receive_donation(self, amount: int, reason_suffix: str = "") -> None:
        self.green_time += amount
        self.reason += f" Received an additional +{amount}s of green time.{reason_suffix}"

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "vehicle_count": self.vehicle_count,
            "waiting_time": self.waiting_time,
            "density": self.density,
            "green_time": self.green_time,
            "initial_green_time": self.initial_green_time,
            "emergency_vehicle": self.emergency_vehicle,
            "signal_state": self.signal_state,
            "has_priority": self.has_priority,
            "reason": self.reason,
        }

    def __repr__(self) -> str:
        return f"TrafficSignalAgent({self.agent_id}, green={self.green_time}s, density={self.density})"
