"""
simulation_engine.py

Orchestrates ONE full simulation run for a chosen architecture and
computes the Before/After waiting-time comparison. This is the single
function the Streamlit UI (and the Colab notebook) both call - it is
completely independent of any UI framework.
"""

from typing import List, Dict

from agents.central_agent import CentralControllerAgent
from agents.communication import CommunicationLog, create_message
from agents.manager_agent import TrafficManagerAgent
from agents.traffic_agent import TrafficSignalAgent
from decision.decision_engine import estimate_waiting_time_after, MAX_DONATION
from simulation.signal_controller import SignalPhaseController

VALID_ARCHITECTURES = ("Centralized", "Hierarchical", "Decentralized")


def build_agents(junction_data: List[Dict]) -> List[TrafficSignalAgent]:
    """Converts raw junction dicts into TrafficSignalAgent objects."""
    return [
        TrafficSignalAgent(
            agent_id=j["agent_id"],
            vehicle_count=j["vehicle_count"],
            waiting_time=j["waiting_time"],
            emergency_vehicle=j.get("emergency_vehicle", False),
        )
        for j in junction_data
    ]


def run_decentralized(agents: List[TrafficSignalAgent], comm_log: CommunicationLog) -> List[TrafficSignalAgent]:
    """
    Implements the DECENTRALIZED architecture.

    Signal_1 <-> Signal_2
        ^           ^
        v           v
    Signal_3 <-> Signal_4

    THERE IS NO CONTROLLER OBJECT ANYWHERE IN THIS FUNCTION - that
    absence is the entire point. Each needy agent negotiates directly,
    one-on-one, with its peers until one agrees to donate, or none can.
    """
    # Step 1: every agent broadcasts its status to all peers
    for agent in agents:
        comm_log.add(create_message(
            agent.agent_id, "ALL", "TRAFFIC_UPDATE",
            vehicle_count=agent.vehicle_count,
            waiting_time=agent.waiting_time,
            traffic_density=agent.density,
            status="BROADCAST",
        ))

    # Step 2: each needy agent negotiates directly, peer to peer
    for needy in agents:
        if needy.emergency_vehicle:
            continue
        if not (needy.density == "HIGH" or needy.waiting_time > 60):
            continue

        satisfied = False
        for donor in agents:
            if donor.agent_id == needy.agent_id:
                continue

            comm_log.add(create_message(
                needy.agent_id, donor.agent_id, "TRAFFIC_UPDATE",
                traffic_density=needy.density,
                request="REQUEST_GREEN_TIME", status="PENDING",
            ))

            if donor.can_donate(MAX_DONATION):
                donor.donate(MAX_DONATION)
                needy.receive_donation(MAX_DONATION, f" (direct peer negotiation with {donor.agent_id})")
                comm_log.add(create_message(
                    donor.agent_id, needy.agent_id, "RESPONSE",
                    response="Request accepted - LOW density, donating green time.",
                    status="COMPLETED",
                ))
                satisfied = True
                break
            else:
                comm_log.add(create_message(
                    donor.agent_id, needy.agent_id, "RESPONSE",
                    response="Cannot donate - insufficient spare capacity or not LOW density.",
                    status="REJECTED",
                ))

        if not satisfied:
            comm_log.add(create_message(
                needy.agent_id, "ALL", "REQUEST_GREEN_TIME",
                response="No neighboring signal could donate green time.",
                status="UNRESOLVED",
            ))

    return agents


def run_simulation(junction_data: List[Dict], architecture: str,
                    elapsed_seconds: int = 0) -> Dict:
    """
    Runs ONE full simulation for the given architecture.

    Args:
        junction_data: list of dicts, each with agent_id, vehicle_count,
                        waiting_time, and optionally emergency_vehicle.
        architecture: one of "Centralized", "Hierarchical", "Decentralized".
        elapsed_seconds: how far into the signal cycle the simulation is.
                          Determines which junction currently has the
                          right of way (GREEN). Advancing this value is
                          what makes the lights actually change.

    Returns:
        dict with keys:
            agents              -> list of TrafficSignalAgent (post-negotiation)
            comm_log            -> list of message dicts
            avg_waiting_before  -> float
            avg_waiting_after   -> float
            improvement_pct     -> float (computed, never hard-coded)

    Raises:
        ValueError: for an invalid architecture name or empty junction_data.
    """
    if architecture not in VALID_ARCHITECTURES:
        raise ValueError(
            f"Invalid architecture '{architecture}'. Must be one of {VALID_ARCHITECTURES}."
        )
    if not junction_data:
        raise ValueError("At least one junction is required to run a simulation.")

    agents = build_agents(junction_data)
    before_waiting = {a.agent_id: a.waiting_time for a in agents}
    before_green = {a.agent_id: a.green_time for a in agents}

    comm_log = CommunicationLog()

    if architecture == "Centralized":
        CentralControllerAgent().run(agents, comm_log)
    elif architecture == "Hierarchical":
        TrafficManagerAgent().run(agents, comm_log)
    else:
        run_decentralized(agents, comm_log)

    after_waiting = []
    for a in agents:
        est = estimate_waiting_time_after(
            waiting_before=before_waiting[a.agent_id],
            green_before=before_green[a.agent_id],
            green_after=a.green_time,
        )
        after_waiting.append(est)

    avg_before = sum(before_waiting.values()) / len(before_waiting)
    avg_after = sum(after_waiting) / len(after_waiting)
    improvement_pct = ((avg_before - avg_after) / avg_before * 100) if avg_before > 0 else 0.0

    # -----------------------------------------------------------------
    # TRAFFIC LIGHT STATE (RED / YELLOW / GREEN)
    # -----------------------------------------------------------------
    # This happens AFTER negotiation, because each junction's green phase
    # length depends on the green time it ended up with (including any
    # time donated to it). The controller then decides whose TURN it is
    # at this moment in the simulation and writes RED/YELLOW/GREEN onto
    # each agent. Density never sets the colour directly - it only sets
    # how long that junction's green phase lasts.
    controller = SignalPhaseController(agents)
    controller.apply_to_agents(elapsed_seconds)

    return {
        "agents": agents,
        "comm_log": comm_log.as_list(),
        "avg_waiting_before": round(avg_before, 2),
        "avg_waiting_after": round(avg_after, 2),
        "improvement_pct": round(improvement_pct, 2),
        "signal_schedule": controller.schedule,
        "phase": controller.phase_summary(elapsed_seconds),
    }
