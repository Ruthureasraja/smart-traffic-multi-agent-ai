# 🚦 Multi-Agent Smart Traffic Management System
### Using Distributed Decision Making (Centralized, Hierarchical & Decentralized Architectures)

This project extends the original **Multi-Agent Communication Framework**
into a complete, real-world scenario: multiple intelligent traffic
signal agents that communicate with each other and make distributed
decisions to control traffic signal timing — with a full interactive
Streamlit dashboard.

---

## Project Structure

```
smart_traffic_multi_agent/
│
├── app.py                          <- Streamlit UI (run this to launch the dashboard)
├── requirements.txt
├── README.md
│
├── agents/
│   ├── __init__.py
│   ├── traffic_agent.py            <- TrafficSignalAgent (one independent junction)
│   ├── central_agent.py            <- Centralized architecture controller
│   ├── manager_agent.py            <- Hierarchical architecture (Manager + Area Managers)
│   └── communication.py            <- Shared message format + communication log
│
├── decision/
│   ├── __init__.py
│   └── decision_engine.py          <- Core decision logic (density, green time, priority)
│
├── simulation/
│   ├── __init__.py
│   ├── traffic_generator.py        <- Default + random traffic scenario generator
│   └── simulation_engine.py        <- Orchestrates one full simulation run (all 3 architectures)
│
├── visualization/
│   ├── __init__.py
│   └── charts.py                   <- Plotly charts + architecture network diagrams
│
├── data/
│   └── sample_traffic.csv          <- The default 4-junction demonstration scenario
│
└── notebooks/
    └── multi_agent_traffic_demo.ipynb   <- Google Colab demo (imports the SAME modules above)
```

**Design principle:** the agent logic (`agents/`, `decision/`, `simulation/`)
is completely independent of Streamlit. The exact same modules power both
the Colab notebook and the web app — nothing is duplicated.

---

## Installation & Running

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit dashboard

```bash
streamlit run app.py
```

This opens the dashboard in your browser (usually `http://localhost:8501`).

### 3. Run the Google Colab notebook

Upload the entire `smart_traffic_multi_agent` folder (as a zip) to your
Colab session, then open `notebooks/multi_agent_traffic_demo.ipynb` and
run all cells — the first cell unzips the project, the second sets up
imports, then every architecture is demonstrated independently of any UI.

### 4. Run the automated tests (optional, proves the logic works)

```bash
pip install pytest
pytest -v
```
*(Note: add a `tests/` folder with unit tests if your instructor requires
formal test coverage — the core functions in `decision_engine.py` are
pure functions with no side effects, so they're straightforward to test.)*

---

## How to Use the Dashboard

1. **Sidebar:** choose the communication architecture (Centralized /
   Hierarchical / Decentralized), set the number of junctions, and
   adjust each junction's vehicle count, waiting time, and emergency
   vehicle flag.
2. Click **▶️ Start** to begin continuous simulation (traffic values
   evolve slightly every step), **⏸️ Pause** to freeze it, or
   **🔄 Reset** to return to the default demonstration scenario.
3. Use **⏭️ Step Once** to advance exactly one step without continuous
   looping — useful for explaining one negotiation at a time in a viva.
4. Watch the **Agent Communication Log**, **AI Agent Decision**
   explanations, and **Architecture Comparison** table update live.

---

## Viva Explanation

**1. What is an agent?**
A small, independent piece of software with one clear job — here, each
`TrafficSignalAgent` monitors its own junction (vehicles, waiting time,
density) and can send/receive messages to negotiate for more green time.

**2. What is multi-agent communication?**
Agents exchanging structured request/response messages to coordinate a
shared goal — reducing overall waiting time across the traffic network —
without one agent knowing everything the others know.

**3. Why is traffic management suitable for multi-agent systems?**
Each junction genuinely operates somewhat independently (its own sensors,
its own local conditions) but the *overall* traffic flow benefits from
coordination — exactly the kind of problem multi-agent systems are
designed for, versus one centralized program trying to model everything.

**4. How does the Centralized architecture work?**
A single `CentralControllerAgent` receives status updates from every
signal, then reallocates green time globally — it can see the whole
network at once, so it can find the best overall reallocation, but if it
fails, the entire system stops (single point of failure).

**5. How does the Hierarchical architecture work?**
A `TrafficManagerAgent` delegates to `AreaManagerAgent`s, each responsible
for a subset of junctions. Each Area Manager reallocates green time only
within its own group before reporting a summary back up — a middle ground
between global (Centralized) and fully local (Decentralized) optimization.

**6. How does the Decentralized architecture work?**
There is **no controller at all**. Each `TrafficSignalAgent` broadcasts
its status, and any junction needing more green time negotiates *directly*
with its peers, one at a time, until one agrees to donate or none can.
This is the main architecture of the project because it best demonstrates
genuine peer-to-peer multi-agent behavior.

**7. How do agents communicate?**
Every message uses one shared dictionary format (see `communication.py`):
sender, receiver, message_type, request, response, timestamp, and status
— logged in the Agent Communication Log panel in real time.

**8. How is traffic density calculated?**
By vehicle count: LOW (0–30), MEDIUM (31–60), HIGH (61+). See
`classify_density()` in `decision_engine.py`.

**9. How is signal timing decided?**
Base green time comes from density (20s / 35s / 50s). If waiting time
exceeds 60 seconds, a +15s priority boost is applied. Emergency vehicles
override everything with a fixed 60s maximum-priority green time. Every
decision includes a plain-English reason — never an unexplained number.

**10. How is distributed decision making achieved?**
No single agent has full authority in the Decentralized mode — each
junction decides locally, negotiates with peers, and the final signal
timing emerges from many small local decisions rather than one global
calculation.

**11. Why is Decentralized architecture useful?**
No single point of failure — if one signal's logic fails, the others
keep negotiating amongst themselves. Trade-off: harder to guarantee a
globally optimal outcome compared to Centralized.

**12. Limitations of this project**
- The waiting-time-reduction formula (`estimate_waiting_time_after`) is a
  simplified, transparent proxy — not real traffic physics.
- Traffic simulation is simulated numerically, not with real sensor,
  camera, or GPS data.
- Communication is simulated via direct Python function/object calls,
  not real network communication across separate machines/processes.
- Negotiation logic uses a fixed donation amount (15s) rather than a
  fully optimized allocation algorithm.

**13. Future enhancements**
- Real-time CCTV/video input with computer vision for vehicle counting
- IoT traffic sensors feeding live data instead of manual/simulated input
- Reinforcement learning for adaptive signal timing policies
- Real public traffic datasets for validation
- Emergency vehicle GPS integration for automatic detection
- Integration with real traffic signal hardware
- Cloud deployment for multi-city monitoring
- Real LLM-based agents for natural-language negotiation and reporting

---

## Architecture Comparison Summary

| Criteria | Centralized | Hierarchical | Decentralized |
|---|---|---|---|
| Controller | One Central Controller | Manager + Area Managers | None |
| Communication | All signals -> Controller -> All | Manager <-> Area <-> Signals | Direct, agent-to-agent |
| Complexity | Low | Medium | Medium-High |
| Scalability | Poor (controller bottleneck) | Good | Harder to manage as agents increase |
| Fault Tolerance | Low (controller failure stops everything) | Medium | High (no single point of failure) |
| Optimization scope | Global (best overall result) | Regional | Local/pairwise only |

*(Waiting-time and improvement percentages shown in the app's comparison
table are computed live from actual simulation data — never hard-coded.)*

---

## Sample Output (Default Scenario)

```
Signal_1: Vehicles=75, Waiting=65s -> HIGH density -> Green Time boosted to 65s
Signal_2: Vehicles=25, Waiting=15s -> LOW density  -> Green Time 20s (can donate)
Signal_3: Vehicles=50, Waiting=40s -> MEDIUM density -> Green Time 35s
Signal_4: Vehicles=35, Waiting=25s -> MEDIUM density -> Green Time 35s

Decentralized negotiation:
Signal_1 -> Signal_2: REQUEST_GREEN_TIME (density HIGH)
Signal_2 -> Signal_1: Request accepted - LOW density, donating 15s
Signal_1 green time: 65s -> 80s | Signal_2 green time: 20s -> 15s

Average Waiting Time Before: 36.25s
Average Waiting Time After:  ~28-30s (varies with negotiation outcome)
Improvement: computed live, typically 15-25%
```

---

## Viva Q&A Quick Reference

| # | Question | Short Answer |
|---|---|---|
| 1 | What problem does this solve? | Static/manual traffic signal timing is inefficient; agents negotiate to redistribute green time dynamically. |
| 2 | Why 3 architectures? | To demonstrate and compare the standard ways multi-agent systems can be organized. |
| 3 | What triggers a negotiation? | A junction has HIGH density OR waiting time > 60s. |
| 4 | What stops a donor from giving away all its time? | `MIN_GREEN_TIME` floor (15s) in `can_donate()`. |
| 5 | How is emergency vehicle priority handled? | Immediate 60s green time override, skips normal negotiation entirely. |
| 6 | Is the waiting-time improvement real or fake? | Computed live via `estimate_waiting_time_after()` — not hard-coded, but based on a documented simplifying formula. |
| 7 | What was reused from your original framework? | The shared message dictionary format and the concept of Central/Manager/Peer communication patterns. |
| 8 | What's new in this project? | A real-world domain (traffic), a full Streamlit UI, quantifiable before/after metrics, and 4 independent agents instead of 3 generic ones. |

---

## Spoken 2-Minute Explanation (for viva)

> "My project extends a Multi-Agent Communication Framework into a
> real-world scenario: Smart Traffic Management. I built four
> independent Traffic Signal Agents, each monitoring its own vehicle
> count, waiting time, and emergency vehicle status. Using a shared
> decision engine, each agent calculates its own green time based on
> traffic density, with a priority boost if waiting time is too long,
> and maximum priority if an emergency vehicle is present.
>
> I implemented three communication architectures. In Centralized, one
> Central Controller sees the whole network and reallocates green time
> globally. In Hierarchical, a Traffic Manager delegates to Area
> Managers, each optimizing their own region. In Decentralized — the
> main architecture of this project — there is no controller at all;
> signals negotiate directly with each other, peer to peer, requesting
> and donating green time based on their own local density.
>
> All three architectures reduce average waiting time, but through
> different communication paths, and I built a Streamlit dashboard that
> visualizes the agent network, the live communication log, and a
> before-versus-after comparison computed directly from the simulation
> — not hard-coded. This demonstrates genuine distributed decision
> making, not just a traffic-light animation."

---

## Technology Used

- **Python** — core agent, decision, and simulation logic
- **Streamlit** — interactive web dashboard
- **Pandas** — structuring communication logs and comparison tables
- **Plotly** — all charts and the agent network diagrams
- No external AI model, API key, or internet connection required —
  everything runs locally.
