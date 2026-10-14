"""
MacroFlow-LWR: Continuum Traffic Shockwave PDE Simulator (Lighthill-Whitham-Richards
and Daganzo-style Cell Transmission Model) with synthetic signal-control scenarios.

Author: Kshitija Karmore (B.Tech Civil Engineering, 2nd Year, IIT Delhi)
Coursework Grounding:
  - CVL2601: Traffic and Transportation Planning (Fundamental diagram, LWR conservation PDE,
    Rankine-Hugoniot shockwaves, Webster signal delay & green-split optimization)
  - MTL: Differential Equations & Numerical Conservation Laws
  - COL: Computer Science & Programming

Reference Grounding:
  - Daganzo, C. F. (1994). "The cell transmission model: A dynamic representation of
    highway traffic consistent with the hydrodynamic theory." Transportation Research
    Part B: Methodological, 28(4), 269-287.
  - Lighthill, M. J., & Whitham, G. B. (1955) / Richards, P. I. (1956). LWR Traffic PDE.
"""

import csv
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ---------------------------------------------------------------------------
# Corridor & Fundamental Diagram Parameters (2-Lane Urban Arterial, CVL2601)
# ---------------------------------------------------------------------------
CORRIDOR_LENGTH_M = 2000.0        # L = 2.0 km arterial corridor
NUM_CELLS = 40                    # N = 40 spatial cells
DX_M = CORRIDOR_LENGTH_M / NUM_CELLS  # dx = 50.0 m per cell
DT_S = 2.0                        # dt = 2.0 s time step
SIM_DURATION_S = 1800.0           # T = 1800 s (30-minute peak-hour window)
NUM_STEPS = int(SIM_DURATION_S / DT_S)  # 900 time steps

# Traffic Physics Constants (2-lane urban arterial approach)
VF_KMH = 60.0                     # Free-flow speed v_f = 60 km/h
VF_MS = VF_KMH / 3.6              # 16.6667 m/s
W_KMH = 20.0                      # Backward congestion wave speed w = 20 km/h
W_MS = W_KMH / 3.6                # 5.5556 m/s
KJ_VEH_KM = 160.0                 # Jam density k_j = 160 veh/km (2 lanes * 80 veh/km/lane)
KJ_VEH_M = KJ_VEH_KM / 1000.0     # 0.160 veh/m

# Critical density k_c = (w * k_j) / (v_f + w) = 40.0 veh/km (0.040 veh/m)
KC_VEH_M = (W_MS * KJ_VEH_M) / (VF_MS + W_MS)
KC_VEH_KM = KC_VEH_M * 1000.0

# Capacity q_max = v_f * k_c = 2400 veh/h = 0.6667 veh/s
QMAX_VEH_S = VF_MS * KC_VEH_M
QMAX_VEH_H = QMAX_VEH_S * 3600.0

# CFL condition check: cfl = v_f * dt / dx = 16.6667 * 2.0 / 50.0 = 0.6667 <= 1.0
CFL_NUMBER = VF_MS * DT_S / DX_M

# Signalized Intersection Location: Cell index 24 (x = 1200 m to 1250 m stop-bar)
SIGNAL_CELL_IDX = 24
CYCLE_TIME_S = 90.0


@dataclass
class SimulationMetrics:
    scenario_name: str
    fundamental_diagram: str
    green_split_ratio: float
    green_time_s: float
    cycle_time_s: float
    total_inflow_veh: float
    total_outflow_veh: float
    throughput_efficiency_pct: float
    total_travel_time_veh_h: float
    free_flow_travel_time_veh_h: float
    total_delay_veh_h: float
    mean_delay_per_veh_s: float
    max_queue_length_m: float
    max_queue_cells: int
    mass_conservation_error_veh: float
    total_demand_veh: float
    final_external_queue_veh: float
    external_wait_veh_h: float
    network_conservation_error_veh: float
    actual_green_seconds_by_cycle: List[float]


# ---------------------------------------------------------------------------
# 1. Fundamental Diagrams & Godunov Supply-Demand Functions (CVL2601)
# ---------------------------------------------------------------------------
def sending_demand_triangular(k_veh_m: float) -> float:
    """Daganzo (1994) CTM upstream sending (demand) function S(k) in veh/s."""
    k_clamped = max(0.0, min(KJ_VEH_M, k_veh_m))
    return min(VF_MS * k_clamped, QMAX_VEH_S)


def receiving_supply_triangular(k_veh_m: float) -> float:
    """Daganzo (1994) CTM downstream receiving (supply) function R(k) in veh/s."""
    k_clamped = max(0.0, min(KJ_VEH_M, k_veh_m))
    return min(QMAX_VEH_S, W_MS * (KJ_VEH_M - k_clamped))


def greenshields_flux(k_veh_m: float) -> float:
    """Greenshields (1935) parabolic flux q(k) = v_f * k * (1 - k / k_j) in veh/s."""
    k_clamped = max(0.0, min(KJ_VEH_M, k_veh_m))
    return VF_MS * k_clamped * (1.0 - (k_clamped / KJ_VEH_M))


def sending_demand_greenshields(k_veh_m: float) -> float:
    """Godunov sending function for Greenshields diagram (critical density at k_j / 2)."""
    k_crit_gs = 0.5 * KJ_VEH_M
    q_max_gs = greenshields_flux(k_crit_gs)
    if k_veh_m <= k_crit_gs:
        return greenshields_flux(k_veh_m)
    return q_max_gs


def receiving_supply_greenshields(k_veh_m: float) -> float:
    """Godunov receiving function for Greenshields diagram."""
    k_crit_gs = 0.5 * KJ_VEH_M
    q_max_gs = greenshields_flux(k_crit_gs)
    if k_veh_m <= k_crit_gs:
        return q_max_gs
    return greenshields_flux(k_veh_m)


# ---------------------------------------------------------------------------
# 2. Rankine-Hugoniot Shockwave Speed Verifier (CVL2601)
# ---------------------------------------------------------------------------
def verify_rankine_hugoniot_shockwave(
    num_cells: int = NUM_CELLS,
    target_cfl: float = 0.65,
    simulation_time_s: float = 120.0,
) -> Dict[str, float]:
    """
    Tracks the numerical Godunov shock front and compares its speed with the analytical
    Rankine-Hugoniot jump condition:
        u_shock = (q(k_R) - q(k_L)) / (k_R - k_L)
    Scenario: Free-flowing upstream state k_L = 0.025 veh/m (25 veh/km, q_L = 1500 veh/h)
    meets a standing jam queue k_R = k_j = 0.160 veh/m (160 veh/km, q_R = 0).
    """
    k_L = 0.025  # 25 veh/km
    k_R = KJ_VEH_M  # 160 veh/km (jam)
    q_L = sending_demand_triangular(k_L)  # 16.6667 * 0.025 = 0.41667 veh/s (1500 veh/h)
    q_R = 0.0

    # Analytical Rankine-Hugoniot shockwave speed (negative = moving upstream)
    u_shock_analytical_ms = (q_R - q_L) / (k_R - k_L)

    if isinstance(num_cells, bool) or not isinstance(num_cells, int) or num_cells < 8:
        raise ValueError("num_cells must be an integer >= 8")
    if not math.isfinite(target_cfl) or not 0.0 < target_cfl <= 1.0:
        raise ValueError("target_cfl must be in (0, 1]")
    if not math.isfinite(simulation_time_s) or not 0.0 < simulation_time_s <= 120.0:
        raise ValueError("simulation_time_s must be in (0, 120]")
    dx_m = CORRIDOR_LENGTH_M / num_cells
    nominal_dt_s = target_cfl * dx_m / VF_MS
    sim_steps = math.ceil(simulation_time_s / nominal_dt_s)
    dt_s = simulation_time_s / sim_steps
    initial_shock_index = int(0.75 * num_cells)
    k = [k_L if i < initial_shock_index else k_R for i in range(num_cells)]
    x_shock_0 = initial_shock_index * dx_m

    for _ in range(sim_steps):
        fluxes = [0.0] * (num_cells + 1)
        fluxes[0] = q_L  # steady upstream inflow
        fluxes[num_cells] = 0.0  # blocked downstream boundary
        for i in range(1, num_cells):
            fluxes[i] = min(sending_demand_triangular(k[i - 1]), receiving_supply_triangular(k[i]))
        for i in range(num_cells):
            k[i] = k[i] + (dt_s / dx_m) * (fluxes[i] - fluxes[i + 1])

    midpoint_density = 0.5 * (k_L + k_R)
    transition_indices = [
        i for i in range(num_cells - 1) if k[i] <= midpoint_density <= k[i + 1]
    ]
    if not transition_indices:
        raise RuntimeError("Unable to locate the numerical shock front")
    shock_index = max(transition_indices, key=lambda i: k[i + 1] - k[i])
    density_fraction = (midpoint_density - k[shock_index]) / (k[shock_index + 1] - k[shock_index])
    shock_x_numerical = (shock_index + 0.5 + density_fraction) * dx_m
    u_shock_numerical_ms = (shock_x_numerical - x_shock_0) / simulation_time_s
    rel_error_pct = abs(u_shock_numerical_ms - u_shock_analytical_ms) / abs(u_shock_analytical_ms) * 100.0

    jam_mass_upstream = sum(
        max(0.0, k[i] - k_L) * dx_m for i in range(initial_shock_index)
    )
    integral_speed_ms = (-jam_mass_upstream / (k_R - k_L)) / simulation_time_s

    return {
        "k_L_veh_km": round(k_L * 1000.0, 2),
        "k_R_veh_km": round(k_R * 1000.0, 2),
        "q_L_veh_h": round(q_L * 3600.0, 2),
        "num_cells": num_cells,
        "dx_m": round(dx_m, 4),
        "dt_s": round(dt_s, 4),
        "cfl_number": round(VF_MS * dt_s / dx_m, 4),
        "analytical_shock_speed_ms": round(u_shock_analytical_ms, 5),
        "analytical_shock_speed_kmh": round(u_shock_analytical_ms * 3.6, 4),
        "numerical_shock_speed_ms": round(u_shock_numerical_ms, 5),
        "numerical_shock_speed_kmh": round(u_shock_numerical_ms * 3.6, 4),
        "integral_conservation_speed_ms": round(integral_speed_ms, 5),
        "tracked_shock_position_m": round(shock_x_numerical, 3),
        "relative_error_pct": round(rel_error_pct, 6),
    }


def run_shock_grid_refinement() -> List[Dict[str, float]]:
    return [verify_rankine_hugoniot_shockwave(num_cells=n) for n in (40, 80, 160)]


# ---------------------------------------------------------------------------
# 3. Peak-Hour Demand Profile & Corridor Godunov Simulator
# ---------------------------------------------------------------------------
def upstream_demand_profile_veh_s(t_s: float) -> float:
    """
    Time-varying upstream arrival demand q_in(t) over the 30-min (1800 s) window:
      - 0 to 300 s (Warm-up): 1,150 veh/h (0.3194 veh/s)
      - 300 to 1,100 s (Peak Rush Surge): 1,620 veh/h (0.4500 veh/s)
      - 1,100 to 1,800 s (Post-Peak Recovery): 900 veh/h (0.2500 veh/s)
    """
    if t_s < 300.0:
        return 1150.0 / 3600.0
    elif t_s < 1100.0:
        return 1620.0 / 3600.0
    else:
        return 900.0 / 3600.0


def run_corridor_simulation(
    scenario_name: str,
    green_split_ratio: float,
    diagram: str = "triangular",
    adaptive_queue_control: bool = False,
    demand_scale: float = 1.0,
    export_spacetime_csv: Path = None,
    green_seconds_by_cycle: List[float] = None,
    causal_phase_control: bool = False,
) -> Tuple[SimulationMetrics, List[List[float]]]:
    """
    Simulates the 40-cell (2.0 km) signalized arterial corridor using the Godunov
    LWR / Cell Transmission Model.
    """
    if diagram not in ("triangular", "greenshields"):
        raise ValueError("Unknown fundamental diagram")
    if not math.isfinite(green_split_ratio) or not 0 <= green_split_ratio <= 1:
        raise ValueError("green_split_ratio must be in [0, 1]")
    if not math.isfinite(demand_scale) or demand_scale < 0:
        raise ValueError("demand_scale must be finite and nonnegative")
    assert CFL_NUMBER <= 1.0 + 1e-9, f"CFL condition violated: {CFL_NUMBER}"
    if causal_phase_control and (adaptive_queue_control or green_seconds_by_cycle is not None):
        raise ValueError("Causal phase control cannot be combined with extension or replay")
    if green_seconds_by_cycle is not None:
        if adaptive_queue_control or len(green_seconds_by_cycle) != math.ceil(SIM_DURATION_S / CYCLE_TIME_S):
            raise ValueError("Replay requires one budget per cycle and adaptive control disabled")
        if any(not math.isfinite(value) or not 0 <= value <= CYCLE_TIME_S or abs(value / DT_S - round(value / DT_S)) > 1e-9 for value in green_seconds_by_cycle):
            raise ValueError("Green budgets must be timestep multiples within each cycle")

    k = [0.012] * NUM_CELLS  # Initial light density: 12 veh/km
    initial_vehicles = sum(cell_k * DX_M for cell_k in k)

    total_inflow_veh = 0.0
    total_outflow_veh = 0.0
    total_vehicle_seconds = 0.0
    total_distance_veh_m = 0.0
    total_demand_veh = 0.0
    external_queue_veh = 0.0
    external_wait_seconds = 0.0
    max_queue_cells = 0

    spacetime_grid: List[List[float]] = []

    send_fn = sending_demand_triangular if diagram == "triangular" else sending_demand_greenshields
    recv_fn = receiving_supply_triangular if diagram == "triangular" else receiving_supply_greenshields
    critical_density = KC_VEH_M if diagram == "triangular" else KJ_VEH_M/2
    diagram_capacity = QMAX_VEH_S if diagram == "triangular" else greenshields_flux(critical_density)
    k_cong_threshold = critical_density * 1.15

    effective_green_ratios = []
    phase_start_s = 0.0
    green_budget_s = math.ceil(green_split_ratio * CYCLE_TIME_S / DT_S) * DT_S
    actual_green_seconds = [0.0] * math.ceil(SIM_DURATION_S / CYCLE_TIME_S)

    for step in range(NUM_STEPS):
        t_s = step * DT_S
        cycle_phase_s = t_s % CYCLE_TIME_S

        # Adaptive queue-responsive signal extension: adjusts green ratio based on upstream queue
        if adaptive_queue_control:
            # Measure average density in 6 cells (300 m) immediately upstream of the signal
            upstream_avg_k = sum(k[SIGNAL_CELL_IDX - 6 : SIGNAL_CELL_IDX]) / 6.0
            if upstream_avg_k > critical_density * 1.25:
                active_g_ratio = min(0.72, green_split_ratio + 0.14)
            elif upstream_avg_k > critical_density * 0.85:
                active_g_ratio = min(0.68, green_split_ratio + 0.08)
            else:
                active_g_ratio = green_split_ratio
        else:
            active_g_ratio = green_split_ratio

        effective_green_ratios.append(active_g_ratio)
        green_time_s = active_g_ratio * CYCLE_TIME_S
        is_green = cycle_phase_s < green_time_s
        cycle_index = int(t_s // CYCLE_TIME_S)
        if causal_phase_control:
            if cycle_phase_s == 0.0:
                local_density = sum(k[SIGNAL_CELL_IDX - 5:SIGNAL_CELL_IDX + 1]) / 6.0
                phase_start_s = 0.0 if local_density >= critical_density else min(10.0, CYCLE_TIME_S - green_budget_s)
            is_green = phase_start_s <= cycle_phase_s < phase_start_s + green_budget_s
        if green_seconds_by_cycle is not None:
            is_green = cycle_phase_s < green_seconds_by_cycle[cycle_index]
        actual_green_seconds[cycle_index] += DT_S if is_green else 0.0

        # Compute inter-cell fluxes F_{i-1/2} for i = 0 .. NUM_CELLS
        fluxes = [0.0] * (NUM_CELLS + 1)

        # Upstream boundary inflow at x = 0
        q_demand_in = demand_scale * upstream_demand_profile_veh_s(t_s)
        arrivals = q_demand_in * DT_S
        total_demand_veh += arrivals
        external_queue_veh += arrivals
        fluxes[0] = min(external_queue_veh / DT_S, recv_fn(k[0]))
        external_queue_veh = max(0.0, external_queue_veh - fluxes[0] * DT_S)
        external_wait_seconds += external_queue_veh * DT_S

        # Internal cell boundaries
        for i in range(1, NUM_CELLS):
            s_up = send_fn(k[i - 1])
            r_down = recv_fn(k[i])
            if i - 1 == SIGNAL_CELL_IDX:
                # Signalized stop-bar between SIGNAL_CELL_IDX and SIGNAL_CELL_IDX + 1
                sig_capacity = diagram_capacity if is_green else 0.0
                fluxes[i] = min(s_up, r_down, sig_capacity)
            else:
                fluxes[i] = min(s_up, r_down)

        # Downstream free-outflow boundary at x = L
        fluxes[NUM_CELLS] = send_fn(k[NUM_CELLS - 1])

        total_vehicle_seconds += sum(k) * DX_M * DT_S
        total_distance_veh_m += sum(fluxes[1:]) * DX_M * DT_S

        # Conservative Godunov state update
        for i in range(NUM_CELLS):
            k[i] = k[i] + (DT_S / DX_M) * (fluxes[i] - fluxes[i + 1])

        total_inflow_veh += fluxes[0] * DT_S
        total_outflow_veh += fluxes[NUM_CELLS] * DT_S


        # Count queued cells upstream of the signal
        queued_cells_now = sum(1 for idx in range(SIGNAL_CELL_IDX + 1) if k[idx] >= k_cong_threshold)
        if queued_cells_now > max_queue_cells:
            max_queue_cells = queued_cells_now

        # Save spacetime snapshot every 10 seconds (every 5 steps)
        if step % 5 == 0:
            spacetime_grid.append([round(cell_k * 1000.0, 2) for cell_k in k])

    final_vehicles = sum(cell_k * DX_M for cell_k in k)
    mass_error = abs((initial_vehicles + total_inflow_veh - total_outflow_veh) - final_vehicles)

    # Travel time and delay calculations
    total_travel_time_veh_h = (total_vehicle_seconds + external_wait_seconds) / 3600.0
    effective_veh_served = initial_vehicles + total_demand_veh
    free_flow_travel_time_veh_h = total_distance_veh_m / VF_MS / 3600.0

    total_delay_veh_h = max(0.0, total_travel_time_veh_h - free_flow_travel_time_veh_h)
    mean_delay_per_veh_s = (total_delay_veh_h * 3600.0) / max(1.0, effective_veh_served)
    throughput_efficiency_pct = (total_outflow_veh / effective_veh_served) * 100.0 if effective_veh_served else 0.0
    avg_g_ratio = sum(actual_green_seconds) / SIM_DURATION_S

    if export_spacetime_csv is not None:
        export_spacetime_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(export_spacetime_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = ["time_s"] + [f"cell_{i}_x_{int(i*DX_M)}m_veh_km" for i in range(NUM_CELLS)]
            writer.writerow(header)
            for row_idx, row_vals in enumerate(spacetime_grid):
                writer.writerow([row_idx * 10 + DT_S] + row_vals)

    metrics = SimulationMetrics(
        scenario_name=scenario_name,
        fundamental_diagram=diagram,
        green_split_ratio=round(avg_g_ratio, 4),
        green_time_s=round(avg_g_ratio * CYCLE_TIME_S, 2),
        cycle_time_s=CYCLE_TIME_S,
        total_inflow_veh=round(total_inflow_veh, 2),
        total_outflow_veh=round(total_outflow_veh, 2),
        throughput_efficiency_pct=round(throughput_efficiency_pct, 2),
        total_travel_time_veh_h=round(total_travel_time_veh_h, 4),
        free_flow_travel_time_veh_h=round(free_flow_travel_time_veh_h, 4),
        total_delay_veh_h=round(total_delay_veh_h, 4),
        mean_delay_per_veh_s=round(mean_delay_per_veh_s, 2),
        max_queue_length_m=round(max_queue_cells * DX_M, 1),
        max_queue_cells=max_queue_cells,
        mass_conservation_error_veh=round(mass_error, 10),
        total_demand_veh=total_demand_veh,
        final_external_queue_veh=external_queue_veh,
        external_wait_veh_h=external_wait_seconds / 3600.0,
        network_conservation_error_veh=abs(initial_vehicles + total_demand_veh - total_outflow_veh - final_vehicles - external_queue_veh),
        actual_green_seconds_by_cycle=actual_green_seconds,
    )
    return metrics, spacetime_grid


# ---------------------------------------------------------------------------
# 4. Main Benchmark Suite & Unit Tests
# ---------------------------------------------------------------------------
def main():
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    reports_dir = base_dir / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verify Rankine-Hugoniot shockwave speed
    rh_results = verify_rankine_hugoniot_shockwave()
    assert rh_results["relative_error_pct"] < 3.0, "Shock front error exceeds coarse-grid tolerance"
    refinement = run_shock_grid_refinement()
    assert refinement[-1]["relative_error_pct"] < 1.0
    sensitivity = []
    for demand_multiplier in (0.75, 1.0, 1.25):
        for green_ratio in (0.42, 0.52, 0.62):
            metrics, _ = run_corridor_simulation(
                scenario_name=f"Synthetic demand {demand_multiplier}x, green {green_ratio}",
                green_split_ratio=green_ratio,
                demand_scale=demand_multiplier,
            )
            sensitivity.append({"demand_scale": demand_multiplier, **asdict(metrics)})

    # 2. Run Baseline Unoptimized Fixed-Time Signal (g/C = 0.42 -> 37.8s green / 90s cycle)
    baseline_metrics, baseline_grid = run_corridor_simulation(
        scenario_name="Baseline Fixed-Time Signal (g/C = 0.42)",
        green_split_ratio=0.42,
        diagram="triangular",
        adaptive_queue_control=False,
        export_spacetime_csv=data_dir / "spacetime_baseline_g042.csv",
    )

    # 3. Sweep Green-Split Ratios g/C in [0.38, 0.42, 0.46, 0.50, 0.54, 0.58, 0.62, 0.66]
    #    with cross-street capacity constraint (max arterial g/C <= 0.62 to guarantee cross-street minimum green)
    sweep_results = []
    best_fixed_metrics = None
    for g_ratio in [0.38, 0.42, 0.46, 0.50, 0.54, 0.58, 0.62]:
        m, _ = run_corridor_simulation(
            scenario_name=f"Fixed-Time Sweep (g/C = {g_ratio:.2f})",
            green_split_ratio=g_ratio,
            diagram="triangular",
            adaptive_queue_control=False,
        )
        sweep_results.append(asdict(m))
        if best_fixed_metrics is None or m.mean_delay_per_veh_s < best_fixed_metrics.mean_delay_per_veh_s:
            best_fixed_metrics = m

    # Export optimal fixed-time spacetime grid (g/C = 0.62)
    opt_fixed_metrics, opt_fixed_grid = run_corridor_simulation(
        scenario_name="Fixed Signal Candidate (g/C = 0.62)",
        green_split_ratio=0.62,
        diagram="triangular",
        adaptive_queue_control=False,
        export_spacetime_csv=data_dir / "spacetime_optimized_g062.csv",
    )

    # 4. Run Queue-Responsive Adaptive Signal Control (base g/C = 0.52, dynamic extension up to 0.66)
    adaptive_metrics, adaptive_grid = run_corridor_simulation(
        scenario_name="Queue-Responsive Adaptive Signal Control",
        green_split_ratio=0.52,
        diagram="triangular",
        adaptive_queue_control=True,
        export_spacetime_csv=data_dir / "spacetime_adaptive_control.csv",
    )

    matched_metrics, _ = run_corridor_simulation(
        scenario_name="Retrospective cycle-budget replay, green at cycle start",
        green_split_ratio=0.52,
        green_seconds_by_cycle=adaptive_metrics.actual_green_seconds_by_cycle,
    )
    assert matched_metrics.actual_green_seconds_by_cycle == adaptive_metrics.actual_green_seconds_by_cycle

    # 5. Run Greenshields Parabolic Fundamental Diagram Comparison at g/C = 0.54
    gs_metrics, _ = run_corridor_simulation(
        scenario_name="Greenshields Parabolic Fundamental Diagram (g/C = 0.54)",
        green_split_ratio=0.54,
        diagram="greenshields",
        adaptive_queue_control=False,
    )

    # Compute exact percentage improvements over baseline (g/C = 0.42)
    delay_reduction_fixed_pct = (
        (baseline_metrics.mean_delay_per_veh_s - opt_fixed_metrics.mean_delay_per_veh_s)
        / baseline_metrics.mean_delay_per_veh_s
        * 100.0
    )
    queue_reduction_fixed_pct = (
        (baseline_metrics.max_queue_length_m - opt_fixed_metrics.max_queue_length_m)
        / baseline_metrics.max_queue_length_m
        * 100.0
    )
    delay_reduction_adaptive_pct = (
        (baseline_metrics.mean_delay_per_veh_s - adaptive_metrics.mean_delay_per_veh_s)
        / baseline_metrics.mean_delay_per_veh_s
        * 100.0
    )
    queue_reduction_adaptive_pct = (
        (baseline_metrics.max_queue_length_m - adaptive_metrics.max_queue_length_m)
        / baseline_metrics.max_queue_length_m
        * 100.0
    )

    # Assertions for physical & numerical integrity
    assert baseline_metrics.mass_conservation_error_veh < 1e-7, "Mass conservation violated in baseline!"
    assert opt_fixed_metrics.mass_conservation_error_veh < 1e-7, "Mass conservation violated in optimized!"
    assert adaptive_metrics.mass_conservation_error_veh < 1e-7, "Mass conservation violated in adaptive!"
    assert opt_fixed_metrics.mean_delay_per_veh_s < baseline_metrics.mean_delay_per_veh_s

    prospective_comparisons = []
    for demand_multiplier in (0.75, 1.0, 1.25):
        fixed, _ = run_corridor_simulation("Fixed cycle-start green", 0.52, demand_scale=demand_multiplier)
        causal, _ = run_corridor_simulation("Causal queue-based phase", 0.52, demand_scale=demand_multiplier, causal_phase_control=True)
        assert fixed.actual_green_seconds_by_cycle == causal.actual_green_seconds_by_cycle
        prospective_comparisons.append({
            "demand_scale": demand_multiplier,
            "fixed": asdict(fixed),
            "causal": asdict(causal),
            "causal_minus_fixed_delay_veh_h": causal.total_delay_veh_h - fixed.total_delay_veh_h,
        })

    report = {
        "prospective_equal_budget_comparison": prospective_comparisons,
        "corridor_parameters": {
            "corridor_length_m": CORRIDOR_LENGTH_M,
            "num_cells": NUM_CELLS,
            "dx_m": DX_M,
            "dt_s": DT_S,
            "cfl_number": round(CFL_NUMBER, 4),
            "free_flow_speed_kmh": VF_KMH,
            "backward_wave_speed_kmh": W_KMH,
            "jam_density_veh_km": KJ_VEH_KM,
            "critical_density_veh_km": round(KC_VEH_KM, 2),
            "capacity_veh_h": round(QMAX_VEH_H, 1),
            "signal_stopbar_x_m": (SIGNAL_CELL_IDX + 1) * DX_M,
            "cycle_time_s": CYCLE_TIME_S,
        },
        "evidence_scope": "Synthetic corridor. Finite-window delay = pre-update cell occupancy time + residual external queue waiting time - cell-outflow distance / free-flow speed. Arrivals are available for admission at each step start; residual queue waits a full step. Mean is accumulated delay per initial plus arriving vehicle, not completed-trip delay. Throughput denominator includes initial vehicles and all arrivals. Adaptive and fixed green budgets differ; no cross-street model or field validation.",
        "rankine_hugoniot_verification": rh_results,
        "shock_grid_refinement": refinement,
        "equal_green_budget_comparison": {
            "scope": "Retrospective ablation: replay adaptive realized green seconds at each cycle start. Uses future knowledge; not a deployable fixed-time policy or evidence of controller superiority.",
            "adaptive": asdict(adaptive_metrics),
            "cycle_budget_replay": asdict(matched_metrics),
            "adaptive_minus_replay_delay_veh_h": adaptive_metrics.total_delay_veh_h - matched_metrics.total_delay_veh_h,
        },
        "demand_sensitivity": sensitivity,
        "key_scenarios": {
            "baseline_g042": asdict(baseline_metrics),
            "optimized_fixed_g062": asdict(opt_fixed_metrics),
            "queue_responsive_adaptive": asdict(adaptive_metrics),
            "greenshields_comparison_g054": asdict(gs_metrics),
        },
        "optimization_improvements_vs_baseline": {
            "optimized_fixed_delay_reduction_pct": round(delay_reduction_fixed_pct, 2),
            "optimized_fixed_queue_reduction_pct": round(queue_reduction_fixed_pct, 2),
            "adaptive_control_delay_reduction_pct": round(delay_reduction_adaptive_pct, 2),
            "adaptive_control_queue_reduction_pct": round(queue_reduction_adaptive_pct, 2),
        },
        "green_split_sweep": sweep_results,
    }

    report_path = reports_dir / "traffic_simulation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== MacroFlow-LWR Benchmark & Verification Summary ===")
    print(f"CFL Number: {CFL_NUMBER:.4f} (<= 1.0 Stable)")
    print(
        f"Rankine-Hugoniot Shock Speed: Analytical = {rh_results['analytical_shock_speed_kmh']:.4f} km/h | "
        f"Numerical = {rh_results['numerical_shock_speed_kmh']:.4f} km/h (Error = {rh_results['relative_error_pct']:.6f}%)"
    )
    print(
        f"Baseline Signal (g/C=0.42): Window delay per vehicle = {baseline_metrics.mean_delay_per_veh_s:.2f} s/veh | "
        f"Max Queue = {baseline_metrics.max_queue_length_m:.1f} m | Throughput = {baseline_metrics.throughput_efficiency_pct:.2f}% | "
        f"Mass Error = {baseline_metrics.mass_conservation_error_veh:.2e} veh"
    )
    print(
        f"Optimized Signal (g/C=0.62): Window delay per vehicle = {opt_fixed_metrics.mean_delay_per_veh_s:.2f} s/veh "
        f"(-{delay_reduction_fixed_pct:.2f}%) | Max Queue = {opt_fixed_metrics.max_queue_length_m:.1f} m "
        f"(-{queue_reduction_fixed_pct:.2f}%) | Throughput = {opt_fixed_metrics.throughput_efficiency_pct:.2f}%"
    )
    print(
        f"Adaptive Queue Control (avg g/C={adaptive_metrics.green_split_ratio:.3f}): Window delay per vehicle = {adaptive_metrics.mean_delay_per_veh_s:.2f} s/veh "
        f"(-{delay_reduction_adaptive_pct:.2f}%) | Max Queue = {adaptive_metrics.max_queue_length_m:.1f} m "
        f"(-{queue_reduction_adaptive_pct:.2f}%) | Throughput = {adaptive_metrics.throughput_efficiency_pct:.2f}%"
    )
    print(f"Saved report to: {report_path}")


if __name__ == "__main__":
    main()
