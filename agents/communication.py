"""
communication.py

Defines the SHARED message format used by every agent in every
architecture (Centralized, Hierarchical, Decentralized), and a simple
CommunicationLog to record every message exchanged during a simulation
run - this is what powers the "Agent Communication Log" panel in the
Streamlit UI and proves multi-agent communication is actually happening.
"""

from datetime import datetime
from typing import Dict, List


def create_message(
    sender: str,
    receiver: str,
    message_type: str,
    request: str = "",
    response: str = "",
    status: str = "PENDING",
    **traffic_info,
) -> Dict:
    """
    Builds one message dictionary in the standard shared format:
        sender, receiver, message_type, traffic info, request,
        response, timestamp, status

    Any extra traffic-related keyword arguments (vehicle_count,
    waiting_time, traffic_density, etc.) are merged directly into
    the message dict for flexibility.
    """
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "sender": sender,
        "receiver": receiver,
        "message_type": message_type,
        "request": request,
        "response": response,
        "status": status,
        **traffic_info,
    }


class CommunicationLog:
    """Stores every message exchanged during one simulation run, in order."""

    def __init__(self):
        self.messages: List[Dict] = []

    def add(self, message: Dict) -> None:
        self.messages.append(message)

    def clear(self) -> None:
        self.messages = []

    def as_list(self) -> List[Dict]:
        return self.messages

    def __len__(self) -> int:
        return len(self.messages)
