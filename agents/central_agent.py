"""
central_agent.py

Implements the CENTRALIZED architecture.

    User
      |
      v
Central Controller Agent
      |
  +---+---+---+---+
  v   v   v   v
Signal_1 Signal_2 Signal_3 Signal_4

The Central Controller has a GLOBAL view of every junction at once and
reallocates green time across ALL of them - not just neighbor pairs.
This is why Centralized can find the best overall improvement, at the
cost of being a single point of failure (if it goes down, nothing works).
"""

from typing import List

from agents.communication import create_message, CommunicationLog
from agents.traffic_agent import TrafficSignalAgent
from decision.decision_engine import MAX_DONATION


class CentralControllerAgent:
    """Coordinates ALL traffic signal agents from one central point."""

    def __init__(self, name: str = "Central_Controller"):
        self.name = name

    def run(self, agents: List[TrafficSignalAgent], comm_log: CommunicationLog) -> List[TrafficSignalAgent]:
        comm_log.add(create_message(
            "User", self.name, "SIMULATION_START",
            request="RUN_CENTRALIZED", status="RECEIVED",
        ))

        # Step 1: every signal reports its status to the Central Controller
        for agent in agents:
            comm_log.add(create_message(
                agent.agent_id, self.name, "TRAFFIC_UPDATE",
                vehicle_count=agent.vehicle_count,
                waiting_time=agent.waiting_time,
                traffic_density=agent.density,
                status="SENT",
            ))

        # Step 2: Central Controller identifies junctions that NEED more green time
        needy = sorted(
            [a for a in agents if a.density == "HIGH" or a.waiting_time > 60],
            key=lambda a: a.priority(),
            reverse=True,
        )
        # ...and junctions that CAN spare some green time
        donors = sorted(
            [a for a in agents if a.density == "LOW" and not a.emergency_vehicle],
            key=lambda a: a.priority(),
        )

        # Step 3: global reallocation across the WHOLE network
        for needy_agent in needy:
            if needy_agent.emergency_vehicle:
                comm_log.add(create_message(
                    self.name, needy_agent.agent_id, "DECISION",
                    response="Emergency priority already granted - no donation needed.",
                    status="COMPLETED",
                ))
                continue

            for donor in donors:
                if donor.can_donate(MAX_DONATION):
                    donor.donate(MAX_DONATION)
                    needy_agent.receive_donation(
                        MAX_DONATION,
                        f" (via {self.name} global reallocation from {donor.agent_id})",
                    )
                    comm_log.add(create_message(
                        self.name, donor.agent_id, "REALLOCATE",
                        request=f"DONATE_{MAX_DONATION}s_TO_{needy_agent.agent_id}",
                        status="COMPLETED",
                    ))
                    comm_log.add(create_message(
                        self.name, needy_agent.agent_id, "REALLOCATE",
                        response=f"+{MAX_DONATION}s granted from {donor.agent_id}",
                        status="COMPLETED",
                    ))
                    break

        comm_log.add(create_message(
            self.name, "User", "SIMULATION_END",
            response="Centralized global reallocation complete.", status="COMPLETED",
        ))

        return agents
