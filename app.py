"""
app.py

Streamlit dashboard for the Multi-Agent Smart Traffic Management System.

Run with:
    streamlit run app.py
"""

import time

import pandas as pd
import streamlit as st

from decision.decision_engine import MAX_DONATION
from simulation.simulation_engine import run_simulation, VALID_ARCHITECTURES
from simulation.traffic_generator import (get_default_scenario,
                                          generate_random_scenario, perturb_scenario)
from visualization.charts import (
    architecture_diagram,
    before_after_chart,
    density_chart,
    green_time_chart,
    vehicle_count_chart,
    waiting_time_chart,
)

st.set_page_config(
    page_title="Multi-Agent Smart Traffic Management",
    page_icon="🚦",
    layout="wide",
)

SIGNAL_COLOR = {"GREEN": "#2ecc71", "YELLOW": "#f1c40f", "RED": "#e74c3c"}


# ----------------------------------------------------------------------
# Session state initialization
# ----------------------------------------------------------------------
def init_state():
    if "junction_data" not in st.session_state:
        st.session_state.junction_data = get_default_scenario()
    if "running" not in st.session_state:
        st.session_state.running = False
    if "step_count" not in st.session_state:
        st.session_state.step_count = 0
    if "elapsed_seconds" not in st.session_state:
        # How far into the traffic-light cycle we are. Advancing this
        # is what makes RED/YELLOW/GREEN actually change over time.
        st.session_state.elapsed_seconds = 0
    if "last_result" not in st.session_state:
        st.session_state.last_result = None


init_state()


def sync_widget_keys(data):
    """
    Pushes values directly into the number_input/checkbox widget keys
    (vc_i, wt_i, ev_i) BEFORE those widgets are instantiated later in
    this same script run.

    Why this exists: once a Streamlit widget with a given `key` has been
    created, that widget's `value=` argument is ignored on every future
    rerun - Streamlit uses whatever is already in st.session_state[key]
    instead. Without this function, changing st.session_state.junction_data
    (e.g. from Randomize Traffic, Reset, or Step Once) would update the
    data, but the sidebar number_inputs would keep silently showing their
    old cached numbers forever - the traffic values would change in the
    simulation but never visibly change on screen.
    """
    for i, j in enumerate(data):
        st.session_state[f"vc_{i}"] = int(j["vehicle_count"])
        st.session_state[f"wt_{i}"] = int(j["waiting_time"])
        st.session_state[f"ev_{i}"] = bool(j.get("emergency_vehicle", False))


# ----------------------------------------------------------------------
# Sidebar - configuration
# ----------------------------------------------------------------------
st.sidebar.title("⚙️ Configuration")

architecture = st.sidebar.selectbox(
    "Communication Architecture",
    VALID_ARCHITECTURES,
    help="Choose how the traffic signal agents coordinate with each other.",
)

num_junctions = st.sidebar.slider("Number of Junctions", min_value=2, max_value=6, value=4)

sim_speed = st.sidebar.slider(
    "Simulation Speed (sec/step)", min_value=0.5, max_value=3.0, value=1.5, step=0.5
)

# ---- Control buttons + their handling MUST come before the number_input
# ---- widget loop below, so that any session_state change they make is
# ---- visible to those widgets on the same run (see sync_widget_keys above).
st.sidebar.markdown("---")
start_clicked = st.sidebar.button("▶️ Start Simulation", use_container_width=True)
pause_clicked = st.sidebar.button("⏸️ Pause Simulation", use_container_width=True)
step_clicked = st.sidebar.button("⏭️ Step Once", use_container_width=True)
randomize_clicked = st.sidebar.button("🎲 Randomize Traffic", use_container_width=True)
reset_clicked = st.sidebar.button("🔄 Reset to Default", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Traffic Light Cycle")
seconds_per_step = st.sidebar.slider(
    "Seconds advanced per step", min_value=1, max_value=20, value=5,
    help="How far the traffic-light cycle moves each step. This is what "
         "makes the RED/YELLOW/GREEN lights change.",
)

if start_clicked:
    st.session_state.running = True
if pause_clicked:
    st.session_state.running = False
if randomize_clicked:
    st.session_state.junction_data = generate_random_scenario(num_junctions)
    sync_widget_keys(st.session_state.junction_data)
if reset_clicked:
    st.session_state.junction_data = get_default_scenario()
    st.session_state.running = False
    st.session_state.step_count = 0
    st.session_state.elapsed_seconds = 0
    st.session_state.last_result = None
    sync_widget_keys(st.session_state.junction_data)

# Advancing the simulation (Step Once, or every tick of continuous "running"
# mode) MUST also happen here, before any widget is instantiated - doing it
# after the widget loop (as the original code did) raises
# StreamlitWidgetAlreadyInstantiatedError the moment Step Once is clicked,
# because Streamlit forbids writing to a widget's session_state key once
# that widget has already been drawn in the same run.
if step_clicked or st.session_state.running:
    st.session_state.step_count += 1
    st.session_state.elapsed_seconds += seconds_per_step
    st.session_state.junction_data = perturb_scenario(st.session_state.junction_data, max_change=8)
    sync_widget_keys(st.session_state.junction_data)

st.sidebar.markdown("---")
st.sidebar.subheader("Junction Inputs")

# Keep junction_data in sync WITHOUT discarding values the user edited.
current_data = st.session_state.junction_data
if len(current_data) < num_junctions:
    for i in range(len(current_data), num_junctions):
        current_data.append({
            "agent_id": f"Signal_{i + 1}", "vehicle_count": 30,
            "waiting_time": 20, "emergency_vehicle": False,
        })
    st.session_state.junction_data = current_data
    sync_widget_keys(current_data)
elif len(current_data) > num_junctions:
    st.session_state.junction_data = current_data[:num_junctions]

updated_data = []
for i, j in enumerate(st.session_state.junction_data):
    with st.sidebar.expander(f"🚦 {j['agent_id']}", expanded=(i == 0)):
        try:
            vehicle_count = st.number_input(
                f"Vehicle Count - {j['agent_id']}", min_value=0, max_value=300,
                value=int(j["vehicle_count"]), key=f"vc_{i}",
            )
            waiting_time = st.number_input(
                f"Waiting Time (s) - {j['agent_id']}", min_value=0, max_value=300,
                value=int(j["waiting_time"]), key=f"wt_{i}",
            )
            emergency = st.checkbox(
                f"🚨 Emergency Vehicle - {j['agent_id']}",
                value=j.get("emergency_vehicle", False), key=f"ev_{i}",
            )
            updated_data.append({
                "agent_id": j["agent_id"], "vehicle_count": vehicle_count,
                "waiting_time": waiting_time, "emergency_vehicle": emergency,
            })
        except Exception as e:
            st.error(f"Invalid input for {j['agent_id']}: {e}")
            updated_data.append(j)

st.session_state.junction_data = updated_data


# ----------------------------------------------------------------------
# Run one simulation step (with error handling)
# ----------------------------------------------------------------------
def run_step(junction_data, architecture, elapsed_seconds=0):
    try:
        return run_simulation(junction_data, architecture, elapsed_seconds), None
    except ValueError as e:
        return None, str(e)
    except ZeroDivisionError:
        return None, "Division by zero encountered - check that all junctions have valid data."
    except Exception as e:
        return None, f"Unexpected error: {e}"


result, error = run_step(st.session_state.junction_data, architecture,
                          st.session_state.elapsed_seconds)

if error:
    st.error(f"⚠️ Simulation error: {error}")
    st.stop()

st.session_state.last_result = result
agents = result["agents"]
comm_log = result["comm_log"]


# ----------------------------------------------------------------------
# Header + Dashboard metrics
# ----------------------------------------------------------------------
st.title("🚦 Multi-Agent Smart Traffic Management System")
st.markdown(
    "Distributed Decision Making using Centralized, Hierarchical &amp; Decentralized "
    f"agent communication &nbsp;|&nbsp; **Active Architecture:** `{architecture}`"
)

total_vehicles = sum(a.vehicle_count for a in agents)
avg_waiting = sum(a.waiting_time for a in agents) / len(agents)
high_traffic_count = sum(1 for a in agents if a.density == "HIGH")
emergency_count = sum(1 for a in agents if a.emergency_vehicle)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Vehicles", total_vehicles)
m2.metric("Avg Waiting Time", f"{avg_waiting:.1f}s")
m3.metric("Active Junctions", len(agents))
m4.metric("High Traffic Junctions", high_traffic_count)
m5.metric("Emergency Vehicles", emergency_count)

st.markdown("---")


# ----------------------------------------------------------------------
# Traffic Network - per-junction cards
# ----------------------------------------------------------------------
st.subheader("🚦 Traffic Network — Live Signal States")

phase = result["phase"]
st.info(
    f"**Cycle second {phase['cycle_second']} of {phase['cycle_length']}**  |  "
    f"Right of way: **{phase['active_junction']}** ({phase['active_state']})  |  "
    f"Service order this cycle: {' → '.join(phase['order'])}"
)

# ---- LEGEND (required so the meaning of each colour is explicit) ----
st.markdown(
    """
    <div style="display:flex; gap:22px; flex-wrap:wrap; padding:10px 14px;
                background:#f7f9fb; border:1px solid #e1e6ea; border-radius:8px;
                margin-bottom:14px;">
      <div><span style="display:inline-block;width:14px;height:14px;border-radius:50%;
           background:#e74c3c;margin-right:7px;vertical-align:middle;"></span>
           <b>RED — Stop</b> (waiting for its turn)</div>
      <div><span style="display:inline-block;width:14px;height:14px;border-radius:50%;
           background:#f1c40f;margin-right:7px;vertical-align:middle;"></span>
           <b>YELLOW — Transition</b> (green phase ending)</div>
      <div><span style="display:inline-block;width:14px;height:14px;border-radius:50%;
           background:#2ecc71;margin-right:7px;vertical-align:middle;"></span>
           <b>GREEN — Go</b> (has right of way now)</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "The light colour shows **whose turn it is right now**, not how busy the junction is. "
    "Density decides how LONG a junction's green phase lasts; the cycle decides WHEN it happens."
)

cols = st.columns(len(agents))
for col, agent in zip(cols, agents):
    with col:
        color = SIGNAL_COLOR.get(agent.signal_state, "#e74c3c")
        label = {"GREEN": "GO", "YELLOW": "TRANSITION", "RED": "STOP"}[agent.signal_state]
        priority_txt = "🚨 EMERGENCY PRIORITY" if agent.emergency_vehicle else (
            "⭐ Served first" if agent.agent_id == phase["order"][0] else "Normal")
        st.markdown(
            f"""
            <div style="border:2px solid {color}; border-radius:10px; padding:12px;
                        text-align:center; background:#ffffff;">
                <h4 style="margin:0 0 8px 0;">{agent.agent_id}</h4>
                <div style="width:34px;height:34px;border-radius:50%;background:{color};
                            margin:0 auto 6px auto;
                            box-shadow:0 0 10px {color};"></div>
                <div style="font-weight:700;color:{color};margin-bottom:8px;">
                    {agent.signal_state} — {label}</div>
                <div style="text-align:left;font-size:0.9em;line-height:1.6;">
                <b>Vehicles:</b> {agent.vehicle_count}<br>
                <b>Density:</b> {agent.density}<br>
                <b>Waiting:</b> {agent.waiting_time}s<br>
                <b>Green Time:</b> {agent.green_time}s<br>
                <b>Emergency:</b> {"Yes" if agent.emergency_vehicle else "No"}<br>
                <b>Priority:</b> {priority_txt}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Agent decision"):
            st.caption(agent.reason)

st.markdown("---")


# ----------------------------------------------------------------------
# Agent Network Visualization
# ----------------------------------------------------------------------
st.subheader("🕸️ Agent Network Visualization")
st.plotly_chart(
    architecture_diagram(architecture, [a.agent_id for a in agents]),
    use_container_width=True,
)

st.markdown("---")


# ----------------------------------------------------------------------
# Agent Communication Log
# ----------------------------------------------------------------------
st.subheader("📨 Agent Communication Log")
if comm_log:
    log_df = pd.DataFrame(comm_log)
    display_cols = [c for c in ["timestamp", "sender", "receiver", "message_type",
                                 "request", "response", "status"] if c in log_df.columns]
    st.dataframe(log_df[display_cols], use_container_width=True, height=280)
else:
    st.info("No messages exchanged in this run.")

st.markdown("---")


# ----------------------------------------------------------------------
# AI Agent Decision explanations
# ----------------------------------------------------------------------
st.subheader("🧠 AI Agent Decision Explanation")
for agent in agents:
    st.markdown(f"**{agent.agent_id}:** {agent.reason}")

st.markdown("---")


# ----------------------------------------------------------------------
# Analytics
# ----------------------------------------------------------------------
st.subheader("📊 Analytics")
c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(vehicle_count_chart(agents), use_container_width=True)
with c2:
    st.plotly_chart(waiting_time_chart(agents), use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    st.plotly_chart(green_time_chart(agents), use_container_width=True)
with c4:
    st.plotly_chart(density_chart(agents), use_container_width=True)

st.markdown("---")


# ----------------------------------------------------------------------
# Before vs After comparison
# ----------------------------------------------------------------------
st.subheader("📈 Traffic Optimization Results")
b1, b2, b3 = st.columns(3)
b1.metric("Before Communication", f'{result["avg_waiting_before"]}s')
b2.metric("After Communication", f'{result["avg_waiting_after"]}s')
b3.metric("Improvement", f'{result["improvement_pct"]}%')
st.plotly_chart(before_after_chart(result["avg_waiting_before"], result["avg_waiting_after"]),
                use_container_width=True)
st.caption(
    "Improvement % = ((Before − After) / Before) × 100 — computed directly from this run's "
    "simulation data, not hard-coded."
)

st.markdown("---")


# ----------------------------------------------------------------------
# Architecture Comparison (runs all 3 on the SAME current data)
# ----------------------------------------------------------------------
st.subheader("⚖️ Architecture Comparison")
st.caption("All three architectures are run on the SAME current junction data for a fair comparison.")

conceptual_info = {
    "Centralized": {"Controller": "Single Central Controller", "Communication": "All -> Controller -> All",
                     "Scalability": "Poor (bottleneck)", "Fault Tolerance": "Low (single point of failure)"},
    "Hierarchical": {"Controller": "Manager + Area Managers", "Communication": "Manager <-> Area <-> Signals",
                      "Scalability": "Good", "Fault Tolerance": "Medium"},
    "Decentralized": {"Controller": "None", "Communication": "Direct peer-to-peer",
                       "Scalability": "Harder to coordinate at scale", "Fault Tolerance": "High (no single point of failure)"},
}

computed_rows, conceptual_rows = [], []
for arch in VALID_ARCHITECTURES:
    res, err = run_step(st.session_state.junction_data, arch)
    if err:
        continue
    computed_rows.append({
        "Architecture": arch,
        "Avg Waiting Before (s)": res["avg_waiting_before"],
        "Avg Waiting After (s)": res["avg_waiting_after"],
        "Improvement (%)": res["improvement_pct"],
    })
    conceptual_rows.append({"Architecture": arch, **conceptual_info[arch]})

st.markdown("**Computed Results** (from actual simulation data)")
st.dataframe(pd.DataFrame(computed_rows), use_container_width=True, hide_index=True)

with st.expander("📖 Conceptual Properties (Controller, Communication, Scalability, Fault Tolerance)"):
    st.dataframe(pd.DataFrame(conceptual_rows), use_container_width=True, hide_index=True)
    st.caption(
        "These four columns are standard distributed-systems trade-offs (conceptual, not computed from "
        "simulation data) - the Computed Results table above is what actually comes from this run."
    )

st.markdown("---")
st.caption(
    f"Step count: {st.session_state.step_count} | "
    f"Cycle time elapsed: {st.session_state.elapsed_seconds}s | "
    f"Donation size per negotiation: {MAX_DONATION}s"
)


# ----------------------------------------------------------------------
# Continuous simulation loop (Start/Pause)
# ----------------------------------------------------------------------
if st.session_state.running:
    time.sleep(sim_speed)
    st.rerun()
