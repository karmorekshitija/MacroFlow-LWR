import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_traffic_sim_and_tests as traffic


class TrafficTests(unittest.TestCase):
    def test_greenshields_uses_its_own_signal_capacity(self):
        reference, _ = traffic.run_corridor_simulation("greenshields", 1.0, diagram="greenshields")
        with patch.object(traffic, "QMAX_VEH_S", 0.0):
            independent, _ = traffic.run_corridor_simulation("greenshields", 1.0, diagram="greenshields")
        self.assertEqual(reference.total_outflow_veh, independent.total_outflow_veh)
        self.assertLess(independent.network_conservation_error_veh, 1e-7)

    def test_causal_policy_uses_same_budget(self):
        for demand in (0.0, 0.75, 1.25):
            fixed, _ = traffic.run_corridor_simulation("fixed", 0.52, demand_scale=demand)
            causal, _ = traffic.run_corridor_simulation("causal", 0.52, demand_scale=demand, causal_phase_control=True)
            self.assertEqual(fixed.actual_green_seconds_by_cycle, causal.actual_green_seconds_by_cycle)
            self.assertLess(causal.network_conservation_error_veh, 1e-7)
        with self.assertRaises(ValueError):
            traffic.run_corridor_simulation("invalid", 0.52, causal_phase_control=True, adaptive_queue_control=True)

    def test_matched_cycle_budgets(self):
        adaptive, _ = traffic.run_corridor_simulation("adaptive", 0.52, adaptive_queue_control=True)
        replay, _ = traffic.run_corridor_simulation("replay", 0.52, green_seconds_by_cycle=adaptive.actual_green_seconds_by_cycle)
        self.assertEqual(adaptive.actual_green_seconds_by_cycle, replay.actual_green_seconds_by_cycle)
        self.assertAlmostEqual(replay.green_split_ratio, sum(replay.actual_green_seconds_by_cycle) / traffic.SIM_DURATION_S, places=4)
        self.assertLess(replay.network_conservation_error_veh, 1e-7)
        with self.assertRaises(ValueError):
            traffic.run_corridor_simulation("invalid", 0.52, green_seconds_by_cycle=[1.0] * 20)

    def test_free_flow_has_zero_delay(self):
        metrics, _ = traffic.run_corridor_simulation("free", 1.0, demand_scale=0.5)
        self.assertAlmostEqual(metrics.total_delay_veh_h, 0.0, places=8)
        self.assertAlmostEqual(metrics.final_external_queue_veh, 0.0, places=8)

    def test_blocked_arrivals_are_retained(self):
        metrics, _ = traffic.run_corridor_simulation("blocked", 0.0, demand_scale=1.25)
        self.assertGreater(metrics.final_external_queue_veh, 0.0)
        self.assertGreater(metrics.external_wait_veh_h, 0.0)
        self.assertLess(metrics.network_conservation_error_veh, 1e-7)
        self.assertAlmostEqual(metrics.total_demand_veh, metrics.total_inflow_veh + metrics.final_external_queue_veh, places=2)
        self.assertGreaterEqual(metrics.total_delay_veh_h + 0.0001, metrics.external_wait_veh_h)

    def test_front_tracking_refinement(self):
        results = traffic.run_shock_grid_refinement()
        self.assertLess(results[0]["relative_error_pct"], 3.0)
        self.assertLess(results[-1]["relative_error_pct"], 1.0)
        self.assertLess(results[-1]["relative_error_pct"], results[0]["relative_error_pct"])
        self.assertGreater(results[0]["relative_error_pct"], 0.0)

    def test_conservation_and_density_bounds(self):
        for multiplier in (0.0, 0.75, 1.25):
            with self.subTest(demand=multiplier):
                metrics, snapshots = traffic.run_corridor_simulation("test", 0.42, demand_scale=multiplier)
                self.assertLess(metrics.mass_conservation_error_veh, 1e-7)
                self.assertLess(metrics.network_conservation_error_veh, 1e-7)
                self.assertTrue(all(0 <= value <= traffic.KJ_VEH_KM for row in snapshots for value in row))

    def test_invalid_inputs(self):
        for options in ({"diagram": "typo"}, {"demand_scale": -1}, {"demand_scale": float("nan")}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                traffic.run_corridor_simulation("invalid", 0.42, **options)
        with self.assertRaises(ValueError):
            traffic.verify_rankine_hugoniot_shockwave(target_cfl=0)


if __name__ == "__main__":
    unittest.main()
