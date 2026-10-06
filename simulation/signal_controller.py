"""
signal_controller.py

THE TRAFFIC LIGHT STATE MACHINE (RED / YELLOW / GREEN).

=====================================================================
WHY THIS FILE EXISTS (read this before your review)
=====================================================================
Traffic DENSITY and traffic LIGHT COLOUR are two completely different
things, and this file is what keeps them separate.

- Density (LOW/MEDIUM/HIGH) answers: "how busy is this junction?"
  It decides HOW LONG a junction's green phase lasts.

- Signal state (RED/YELLOW/GREEN) answers: "whose turn is it RIGHT NOW?"
  It decides WHEN that junction's green phase happens.

Only ONE junction may hold the right of way at any moment, otherwise
conflicting traffic would cross at the same time. So this controller
builds a repeating CYCLE: each junction takes its turn, one after
another, and every other junction shows RED while it waits.

    RED    = stopped, waiting for its turn (no right of way)
    YELLOW = transitioning, its green phase is ending
    GREEN  = has the right of way right now, vehicles may pass

A LOW-density junction still gets a GREEN phase when its turn comes —
it is just a SHORTER green phase (20s instead of 50s). This is exactly
why "low density" must never be mapped directly to RED.
"""

from typing import Dict, List

# How long the amber/transition phase lasts at the end of each green phase.
YELLOW_DURATION = 3

# Signal state constants (used instead of loose strings, so a typo fails loudly)
RED = "RED"
YELLOW = "YELLOW"
GREEN = "GREEN"


class SignalPhaseController:
    """
    Builds and evaluates the right-of-way schedule for a set of agents.

    The schedule is a repeating cycle. Each junction gets exactly one
    phase per cycle, made of a GREEN portion followed by a YELLOW
    portion. Whichever junction owns the current moment shows GREEN (or
    YELLOW near the end of its phase); every other junction shows RED.
    """

    def __init__(self, agents: List, yellow_duration: int = YELLOW_DURATION):
        """
        Args:
            agents: list of TrafficSignalAgent objects (already negotiated).
            yellow_duration: seconds of amber at the end of each green phase.
        """
        if not agents:
            raise ValueError("SignalPhaseController needs at least one agent.")
        if yellow_duration < 0:
            raise ValueError("yellow_duration cannot be negative.")

        self.agents = agents
        self.yellow_duration = yellow_duration
        self.schedule = self._build_schedule()

    # -----------------------------------------------------------------
    # Building the schedule
    # -----------------------------------------------------------------
    def _service_order(self) -> List:
        """
        Decides the ORDER in which junctions are served in the cycle.

        Emergency vehicles always go first (they cannot wait their turn).
        After that, the busiest/longest-waiting junction is served first,
        using the same priority_score() the agents already use for
        green-time negotiation — so the light order and the negotiation
        logic stay consistent with each other.
        """
        return sorted(
            self.agents,
            key=lambda a: (0 if a.emergency_vehicle else 1, -a.priority()),
        )

    def _build_schedule(self) -> List[Dict]:
        """
        Creates one phase per agent, laid out end-to-end on a timeline.

        Returns:
            list of dicts, each with agent_id, green_start, green_end,
            yellow_end, and the phase's position in the cycle.
        """
        schedule = []
        cursor = 0

        for position, agent in enumerate(self._service_order()):
            green_seconds = max(1, int(agent.green_time))
            green_start = cursor
            green_end = green_start + green_seconds
            yellow_end = green_end + self.yellow_duration

            schedule.append({
                "agent_id": agent.agent_id,
                "position": position,
                "green_start": green_start,
                "green_end": green_end,
                "yellow_end": yellow_end,
                "green_seconds": green_seconds,
                "emergency": agent.emergency_vehicle,
            })
            cursor = yellow_end

        return schedule

    def cycle_length(self) -> int:
        """Total seconds for one complete cycle through every junction."""
        return self.schedule[-1]["yellow_end"]

    # -----------------------------------------------------------------
    # Evaluating the schedule at a moment in time
    # -----------------------------------------------------------------
    def states_at(self, elapsed_seconds: int) -> Dict[str, str]:
        """
        Works out every junction's light colour at a given moment.

        Args:
            elapsed_seconds: seconds since the simulation started. Values
                             beyond one cycle simply wrap around, because
                             the schedule repeats.

        Returns:
            dict mapping agent_id -> "RED" / "YELLOW" / "GREEN".
        """
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds cannot be negative.")

        t = elapsed_seconds % self.cycle_length()

        # Everyone is RED by default; exactly one junction is then promoted.
        states = {a.agent_id: RED for a in self.agents}

        for phase in self.schedule:
            if phase["green_start"] <= t < phase["green_end"]:
                states[phase["agent_id"]] = GREEN
                break
            if phase["green_end"] <= t < phase["yellow_end"]:
                states[phase["agent_id"]] = YELLOW
                break

        return states

    def active_agent_at(self, elapsed_seconds: int) -> str:
        """Returns the agent_id currently holding the right of way (GREEN or YELLOW)."""
        states = self.states_at(elapsed_seconds)
        for agent_id, state in states.items():
            if state in (GREEN, YELLOW):
                return agent_id
        return ""

    def apply_to_agents(self, elapsed_seconds: int) -> None:
        """
        Writes the computed colour onto each agent object, so the rest of
        the project (dashboard, reports) reads the signal state from the
        agent exactly as before — nothing downstream had to change.
        """
        states = self.states_at(elapsed_seconds)
        for agent in self.agents:
            agent.signal_state = states[agent.agent_id]

    def phase_summary(self, elapsed_seconds: int) -> Dict:
        """Human-readable info about the current phase, for the dashboard."""
        t = elapsed_seconds % self.cycle_length()
        active = self.active_agent_at(elapsed_seconds)
        states = self.states_at(elapsed_seconds)

        return {
            "cycle_second": t,
            "cycle_length": self.cycle_length(),
            "active_junction": active,
            "active_state": states.get(active, RED),
            "order": [p["agent_id"] for p in self.schedule],
        }
