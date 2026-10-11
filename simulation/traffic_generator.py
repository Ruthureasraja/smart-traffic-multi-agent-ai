"""
traffic_generator.py

Generates junction traffic data - either the fixed demonstration
scenario described in the project brief, or randomized values for
further testing/exploration.
"""

import csv
import random
from pathlib import Path
from typing import List, Dict

MAX_INPUT_VALUE = 300   # matches the dashboard number_input limits


DEFAULT_SCENARIO: List[Dict] = [
    {"agent_id": "Signal_1", "vehicle_count": 75, "waiting_time": 65, "emergency_vehicle": False},
    {"agent_id": "Signal_2", "vehicle_count": 25, "waiting_time": 15, "emergency_vehicle": False},
    {"agent_id": "Signal_3", "vehicle_count": 50, "waiting_time": 40, "emergency_vehicle": False},
    {"agent_id": "Signal_4", "vehicle_count": 35, "waiting_time": 25, "emergency_vehicle": False},
]


def get_default_scenario() -> List[Dict]:
    """Returns a fresh COPY of the fixed demonstration scenario (Signal_1 = HIGH traffic)."""
    return [dict(j) for j in DEFAULT_SCENARIO]


def generate_random_scenario(num_junctions: int = 4, seed: int = None) -> List[Dict]:
    """
    Generates random but realistic traffic data for `num_junctions` signals.
    Useful for testing the system beyond the fixed demo scenario.
    """
    if num_junctions < 1:
        raise ValueError("num_junctions must be at least 1.")

    rng = random.Random(seed)

    return [
        {
            "agent_id": f"Signal_{i + 1}",
            "vehicle_count": rng.randint(5, 100),
            "waiting_time": rng.randint(5, 90),
            "emergency_vehicle": False,
        }
        for i in range(num_junctions)
    ]


def perturb_scenario(junction_data: List[Dict], max_change: int = 10, seed: int = None) -> List[Dict]:
    """
    Slightly randomly changes existing traffic values (used by the
    Streamlit app's 'continuous simulation' mode to simulate traffic
    naturally evolving over time, rather than staying static).
    """
    rng = random.Random(seed)
    updated = []

    for j in junction_data:
        new_vehicle_count = min(MAX_INPUT_VALUE, max(0, j["vehicle_count"] + rng.randint(-max_change, max_change)))
        new_waiting_time = min(MAX_INPUT_VALUE, max(0, j["waiting_time"] + rng.randint(-max_change, max_change)))
        updated.append({
            "agent_id": j["agent_id"],
            "vehicle_count": new_vehicle_count,
            "waiting_time": new_waiting_time,
            "emergency_vehicle": j.get("emergency_vehicle", False),
        })

    return updated


def load_scenario_from_csv(path: str = None) -> List[Dict]:
    """
    Loads a junction scenario from a CSV file with the columns
    agent_id, vehicle_count, waiting_time, emergency_vehicle.
    Defaults to data/sample_traffic.csv (the demonstration scenario).
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent / "data" / "sample_traffic.csv"

    required = {"agent_id", "vehicle_count", "waiting_time"}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain the columns: {sorted(required)}")
        rows = []
        for r in reader:
            rows.append({
                "agent_id": r["agent_id"].strip(),
                "vehicle_count": int(r["vehicle_count"]),
                "waiting_time": int(r["waiting_time"]),
                "emergency_vehicle": str(r.get("emergency_vehicle", "False")).strip().lower() == "true",
            })
    if not rows:
        raise ValueError("CSV contains no junction rows.")
    return rows
