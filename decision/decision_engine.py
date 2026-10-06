"""
decision_engine.py

Core decision-making logic shared by ALL THREE architectures
(Centralized, Hierarchical, Decentralized). Kept completely independent
of Streamlit and of any specific agent class, so it can be imported and
tested directly in Google Colab with zero UI dependencies.

IMPORTANT ACADEMIC NOTE (state this in your viva):
The waiting-time-reduction model used here (estimate_waiting_time_after)
is a simplified, transparent proxy formula - NOT real traffic physics.
It exists to demonstrate, in an explainable way, that giving a junction
more green time reduces its waiting time. This is appropriate for an
academic multi-agent COMMUNICATION demo, where the focus is the agent
negotiation, not a physically accurate traffic simulator.
"""

# --- Tunable constants (change these here, not scattered across files) ---
DENSITY_THRESHOLDS = {"LOW": 30, "MEDIUM": 60}   # vehicle count boundaries
BASE_GREEN_TIME = {"LOW": 20, "MEDIUM": 35, "HIGH": 50}   # seconds
WAITING_TIME_ALERT = 60      # seconds - above this, priority boost applies
PRIORITY_BOOST = 15          # seconds added when waiting time alert triggers
EMERGENCY_GREEN_TIME = 60    # seconds - max green time for emergency vehicles
MIN_GREEN_TIME = 10          # a junction can never donate below this floor
MAX_DONATION = 10            # seconds transferred per negotiation


def classify_density(vehicle_count: int) -> str:
    """
    Classifies traffic density from vehicle count.

    LOW    : 0-30 vehicles
    MEDIUM : 31-60 vehicles
    HIGH   : 61+ vehicles
    """
    if vehicle_count < 0:
        raise ValueError("Vehicle count cannot be negative.")

    if vehicle_count <= DENSITY_THRESHOLDS["LOW"]:
        return "LOW"
    elif vehicle_count <= DENSITY_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "HIGH"


def base_decision(vehicle_count: int, waiting_time: int, emergency_vehicle: bool = False) -> dict:
    """
    Computes the INITIAL (pre-negotiation) green time for one junction,
    with a plain-English reason - every decision must be explainable,
    never a random/unexplained number.

    Returns:
        dict with keys: density, green_time, reason
    """
    if waiting_time < 0:
        raise ValueError("Waiting time cannot be negative.")

    density = classify_density(vehicle_count)

    if emergency_vehicle:
        return {
            "density": density,
            "green_time": EMERGENCY_GREEN_TIME,
            "reason": (
                f"Emergency vehicle detected at this junction. "
                f"Maximum priority green time ({EMERGENCY_GREEN_TIME}s) granted immediately, "
                f"overriding normal density-based rules."
            ),
        }

    green_time = BASE_GREEN_TIME[density]
    reason = (
        f"Vehicle count is {vehicle_count}, which classifies as {density} density. "
        f"Base green time set to {green_time}s."
    )

    if waiting_time > WAITING_TIME_ALERT:
        green_time += PRIORITY_BOOST
        reason += (
            f" Waiting time of {waiting_time}s exceeds the {WAITING_TIME_ALERT}s alert threshold, "
            f"so a priority boost of +{PRIORITY_BOOST}s was applied "
            f"(new green time: {green_time}s)."
        )

    return {"density": density, "green_time": green_time, "reason": reason}


def priority_score(vehicle_count: int, waiting_time: int) -> float:
    """
    A single number representing how urgently a junction needs more
    green time. Used to decide WHICH needy junction gets served first
    when multiple junctions are competing for donated green time.

    Formula: vehicle_count + 2 x (extra waiting time beyond 60s)
    Waiting time is weighted higher because long queues cause driver
    frustration and safety risk disproportionate to raw vehicle count.
    """
    return vehicle_count * 1.0 + max(0, waiting_time - WAITING_TIME_ALERT) * 2.0


def estimate_waiting_time_after(waiting_before: int, green_before: int, green_after: int) -> float:
    """
    Simplified, explainable model: waiting time scales inversely with
    the green time allocated to a junction. If green time increases,
    waiting time is estimated to drop proportionally.

    This is a documented simplifying assumption for the academic
    demonstration - see the module docstring above.
    """
    if green_after <= 0:
        raise ValueError("green_after must be greater than 0.")
    if green_after <= green_before:
        return float(waiting_before)   # no improvement, no change
    return round(waiting_before * (green_before / green_after), 1)
