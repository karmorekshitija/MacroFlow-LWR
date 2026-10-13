# MacroFlow-LWR: Continuum Traffic Shockwave PDE Simulator & Signal Timing Optimizer

**Author:** Kshitija Karmore (B.Tech Civil Engineering, IIT Delhi)  
**Course Grounding:** `CVL2601` (Introduction to Traffic and Transportation Planning)  
**Paper Reproduction:** Daganzo, C. F. (1994). *"The Cell Transmission Model: A Dynamic Representation of Highway Traffic Consistent with the Hydrodynamic Theory."* Transportation Research Part B: Methodological, 28(4), 269–287.

---

## 1. Overview & Mathematical Formulation

`MacroFlow-LWR` is a self-contained finite-volume solver and signal control optimizer for the **Lighthill–Whitham–Richards (LWR)** macroscopic traffic conservation partial differential equation:

$$\frac{\partial k(x,t)}{\partial t} + \frac{\partial q(k(x,t))}{\partial x} = 0$$

where $k(x,t)$ is traffic density ($\text{veh/km}$) and $q(k)$ is the macroscopic flow rate ($\text{veh/h}$). Using a **Trapezoidal / Triangular Fundamental Diagram** with free-flow speed $v_f = 60\text{ km/h}$, backward congestion wave speed $w = 20\text{ km/h}$, jam density $k_j = 160\text{ veh/km}$, and critical density $k_c = 40\text{ veh/km}$ ($q_{\max} = 2400\text{ veh/h}$), the PDE is discretized via **Godunov's 1st-Order Upwind Scheme** (equivalent to Daganzo's Cell Transmission Model):

$$S_i^n = \min\left(v_f k_i^n,\; q_{\max}\right), \qquad R_i^n = \min\left(q_{\max},\; w\left(k_j - k_i^n\right)\right)$$

$$q_{i+1/2}^n = \min\left(S_i^n,\; R_{i+1}^n,\; C_{i+1/2}(t^n)\right), \qquad k_i^{n+1} = k_i^n - \frac{\Delta t}{\Delta x}\left(q_{i+1/2}^n - q_{i-1/2}^n\right)$$

where $C_{i+1/2}(t^n)$ enforces dynamic red/green signal phase capacity constraints at signalized intersections while strictly satisfying the **Courant–Friedrichs–Lewy (CFL)** stability condition:

$$\text{CFL} = \frac{\max(v_f, w)\,\Delta t}{\Delta x} = \frac{16.67\text{ m/s} \times 2.0\text{ s}}{50.0\text{ m}} = 0.6667 \le 1.0$$

---

## 2. Verified Benchmark Results (`run_traffic_sim_and_tests.py`)

Running `python run_traffic_sim_and_tests.py` executes 5 automated physics & conservation verification checks and evaluates 3 signal control regimes across a $2.0\text{ km}$ urban arterial corridor ($N = 40$ cells, $\Delta x = 50\text{ m}$, $T = 1800\text{ s}$) with a rush-hour demand surge ($2100\text{ veh/h}$ peak) and a signalized intersection at $x = 1250\text{ m}$ ($C = 90\text{ s}$ cycle):

### A. Rankine–Hugoniot Shockwave & Conservation Verification
| Verification Check | Analytical / Target | Godunov / CTM Numerical | Status |
| :--- | :--- | :--- | :--- |
| **CFL Stability Number** | $\le 1.0000$ | **`0.6667`** | PASS |
| **Vehicle Mass Conservation Error** | $< 10^{-9}\text{ veh}$ | **`0.00e+00 veh`** | PASS |
| **Rankine–Hugoniot Shock Speed ($v_s = \Delta q / \Delta k$)** | `-11.1111 km/h` (`-3.0864 m/s`) | **`-11.1111 km/h` (`0.0000%` error)** | PASS |

### B. Signal Timing Optimization & Queue Spillback Mitigation
| Control Strategy | Effective Green Ratio ($g/C$) | Mean Travel Delay ($\text{s/veh}$) | Delay Reduction vs. Baseline | Max Queue Length ($\text{m}$) | Queue Reduction vs. Baseline | Corridor Throughput Ratio |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Baseline Fixed-Time Signal** | `0.420` | `202.73 s/veh` | — | `1250.0 m` *(Spillback)* | — | `83.49%` |
| **2. Webster / Grid-Optimized Fixed Signal** | `0.620` | **`27.59 s/veh`** | **`-86.39%`** | **`550.0 m`** | **`-56.00%`** | **`99.05%`** |
| **3. Queue-Responsive Adaptive Signal** | `0.587` *(avg)* | **`22.14 s/veh`** | **`-89.08%`** | **`400.0 m`** | **`-68.00%`** | **`99.00%`** |

---

## 3. Repository Structure & Reproduction

```text
macroflow_lwr_traffic_simulator/
├── run_traffic_sim_and_tests.py      # Godunov/CTM PDE solver, Rankine-Hugoniot verifier & signal optimizer
├── interactive_shockwave_viewer.html # Interactive HTML5 Canvas spacetime shockwave heatmap & signal controller
├── README.md                         # Mathematical documentation & benchmark summary
├── data/
│   ├── spacetime_baseline_g042.csv   # 2D spacetime density matrix k(x,t) under baseline fixed signal
│   ├── spacetime_optimized_g062.csv  # 2D spacetime density matrix k(x,t) under optimized fixed signal
│   └── spacetime_adaptive_control.csv# 2D spacetime density matrix k(x,t) under queue-responsive control
└── reports/
    └── traffic_simulation_report.json# Complete machine-readable verification & performance report
```

### Quick Start
```bash
python run_traffic_sim_and_tests.py
```
Open `interactive_shockwave_viewer.html` in any browser to inspect the spacetime shockwave fan, adjust $g/C$ or demand surge parameters in real time, and compare fixed vs. adaptive signal control.
