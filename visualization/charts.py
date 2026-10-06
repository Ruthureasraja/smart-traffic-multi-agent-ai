"""
charts.py

Plotly chart builders for the Streamlit dashboard - kept separate from
app.py so chart logic is reusable/testable independently of the UI.
"""

from typing import List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from agents.traffic_agent import TrafficSignalAgent

DENSITY_COLORS = {"LOW": "#2ecc71", "MEDIUM": "#f39c12", "HIGH": "#e74c3c"}


def agents_to_dataframe(agents: List[TrafficSignalAgent]) -> pd.DataFrame:
    return pd.DataFrame([a.to_dict() for a in agents])


def vehicle_count_chart(agents: List[TrafficSignalAgent]):
    df = agents_to_dataframe(agents)
    return px.bar(
        df, x="agent_id", y="vehicle_count", color="density",
        title="Vehicle Count by Junction",
        color_discrete_map=DENSITY_COLORS,
        labels={"agent_id": "Junction", "vehicle_count": "Vehicles"},
    )


def waiting_time_chart(agents: List[TrafficSignalAgent]):
    df = agents_to_dataframe(agents)
    return px.bar(
        df, x="agent_id", y="waiting_time",
        title="Waiting Time by Junction (sec)",
        color="waiting_time", color_continuous_scale="Reds",
        labels={"agent_id": "Junction", "waiting_time": "Waiting Time (s)"},
    )


def green_time_chart(agents: List[TrafficSignalAgent]):
    df = agents_to_dataframe(agents)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["agent_id"], y=df["initial_green_time"], name="Before Negotiation"))
    fig.add_trace(go.Bar(x=df["agent_id"], y=df["green_time"], name="After Negotiation"))
    fig.update_layout(
        title="Green Time Allocation: Before vs After Agent Negotiation",
        barmode="group", yaxis_title="Green Time (s)", xaxis_title="Junction",
    )
    return fig


def density_chart(agents: List[TrafficSignalAgent]):
    df = agents_to_dataframe(agents)
    counts = df["density"].value_counts().reset_index()
    counts.columns = ["density", "count"]
    return px.pie(
        counts, names="density", values="count", title="Traffic Density Distribution",
        color="density", color_discrete_map=DENSITY_COLORS,
    )


def before_after_chart(avg_before: float, avg_after: float):
    fig = go.Figure(data=[go.Bar(
        x=["Before Communication", "After Communication"],
        y=[avg_before, avg_after],
        marker_color=["#e74c3c", "#2ecc71"],
        text=[f"{avg_before}s", f"{avg_after}s"],
        textposition="outside",
    )])
    fig.update_layout(
        title="Average Waiting Time: Before vs After Multi-Agent Communication",
        yaxis_title="Seconds",
    )
    return fig


def architecture_diagram(architecture: str, agent_ids: list = None):
    """
    Draws the communication topology for the selected architecture.
    Scales automatically to however many junctions are configured (2-6),
    instead of assuming exactly four.
    """
    import math
    agent_ids = agent_ids or ["Signal_1", "Signal_2", "Signal_3", "Signal_4"]
    n = len(agent_ids)
    fig = go.Figure()

    def spread_x(count, width=3.0):
        if count == 1:
            return [0.0]
        step = width / (count - 1)
        return [-width / 2 + i * step for i in range(count)]

    if architecture == "Centralized":
        xs = spread_x(n)
        nodes = {"Central_Controller": (0, 2)}
        nodes.update({aid: (x, 0) for aid, x in zip(agent_ids, xs)})
        edges = [("Central_Controller", aid) for aid in agent_ids]

    elif architecture == "Hierarchical":
        # Mirrors the exact split used in TrafficManagerAgent.run()
        mid = max(1, n // 2)
        a1, a2 = agent_ids[:mid], agent_ids[mid:]
        nodes = {"Traffic_Manager": (0, 3),
                 "Area_Manager_1": (-1.2, 1.5), "Area_Manager_2": (1.2, 1.5)}
        edges = [("Traffic_Manager", "Area_Manager_1"),
                 ("Traffic_Manager", "Area_Manager_2")]
        for aid, x in zip(a1, [v - 1.8 for v in spread_x(len(a1), 1.2 * max(1, len(a1) - 1) or 0.1)]):
            nodes[aid] = (x, 0)
            edges.append(("Area_Manager_1", aid))
        for aid, x in zip(a2, [v + 1.8 for v in spread_x(len(a2), 1.2 * max(1, len(a2) - 1) or 0.1)]):
            nodes[aid] = (x, 0)
            edges.append(("Area_Manager_2", aid))

    else:  # Decentralized - peer-to-peer ring, no controller node at all
        radius = 1.5
        nodes = {aid: (radius * math.cos(2 * math.pi * i / n),
                       radius * math.sin(2 * math.pi * i / n))
                 for i, aid in enumerate(agent_ids)}
        edges = [(agent_ids[i], agent_ids[(i + 1) % n]) for i in range(n)]
        if n == 4:
            edges += [(agent_ids[0], agent_ids[2]), (agent_ids[1], agent_ids[3])]

    for a, b in edges:
        x0, y0 = nodes[a]
        x1, y1 = nodes[b]
        fig.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines",
                                 line=dict(color="lightgray", width=2),
                                 showlegend=False, hoverinfo="none"))

    fig.add_trace(go.Scatter(
        x=[p[0] for p in nodes.values()], y=[p[1] for p in nodes.values()],
        mode="markers+text", text=list(nodes.keys()), textposition="top center",
        marker=dict(size=34, color="#3498db", line=dict(width=2, color="white")),
        showlegend=False,
    ))
    fig.update_layout(
        title=f"{architecture} Architecture - Agent Communication Network ({n} junctions)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=400, plot_bgcolor="white", margin=dict(t=50, b=10),
    )
    return fig
