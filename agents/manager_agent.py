"""
manager_agent.py

Implements the HIERARCHICAL architecture.

Traffic_Manager
    |
    +-- Area_Manager_1
    |       +-- Signal_1
    |       +-- Signal_2
    |
    +-- Area_Manager_2
            +-- Signal_3
            +-- Signal_4

The Traffic Manager DELEGATES optimization to Area Managers, each of
which only reallocates green time WITHIN its own group of signals
(regional optimization) - a middle ground between Centralized's
global view and Decentralized's fully local, peer-to-peer negotiation.
"""

from typing import List

from agents.communication import create_message, CommunicationLog
from agents.traffic_agent import TrafficSignalAgent
from decision.decision_engine import MAX_DONATION


class AreaManagerAgent:
    """Manages reallocation within ONE region/group of traffic signals."""

    def __init__(self, name: str, agents: List[TrafficSignalAgent]):
        self.name = name
        self.agents = agents

    def run(self, comm_log: CommunicationLog, manager_name: str) -> None:
        comm_log.add(create_message(
            manager_name, self.name, "DELEGATE_TASK",
            request="OPTIMIZE_AREA", status="RECEIVED",
        ))

        needy = sorted(
            [a for a in self.agents if a.density == "HIGH" or a.waiting_time > 60],
            key=lambda a: a.priority(), reverse=True,
        )
        donors = sorted(
            [a for a in self.agents if a.can_donate(MAX_DONATION)],
            key=lambda a: a.priority(),
        )

        for needy_agent in needy:
            if needy_agent.emergency_vehicle:
                continue
            for donor in donors:
                if donor.can_donate(MAX_DONATION):
                    donor.donate(MAX_DONATION)
                    needy_agent.receive_donation(MAX_DONATION, f" (via {self.name})")
                    comm_log.add(create_message(
                        donor.agent_id, needy_agent.agent_id, "AREA_REALLOCATE",
                        request=f"DONATE_{MAX_DONATION}s", status="COMPLETED",
                    ))
                    break

        comm_log.add(create_message(
            self.name, manager_name, "AREA_REPORT",
            response=f"{self.name} optimization complete for {[a.agent_id for a in self.agents]}.",
            status="COMPLETED",
        ))


class TrafficManagerAgent:
    """Top-level manager that delegates work to Area Managers."""

    def __init__(self, name: str = "Traffic_Manager"):
        self.name = name

    def run(self, agents: List[TrafficSignalAgent], comm_log: CommunicationLog) -> List[TrafficSignalAgent]:
        comm_log.add(create_message(
            "User", self.name, "SIMULATION_START",
            request="RUN_HIERARCHICAL", status="RECEIVED",
        ))

        mid = max(1, len(agents) // 2)
        area1 = AreaManagerAgent("Area_Manager_1", agents[:mid])
        area2 = AreaManagerAgent("Area_Manager_2", agents[mid:])

        area1.run(comm_log, self.name)
        if area2.agents:
            area2.run(comm_log, self.name)

        comm_log.add(create_message(
            self.name, "User", "SIMULATION_END",
            response="Hierarchical optimization complete.", status="COMPLETED",
        ))

        return agents
