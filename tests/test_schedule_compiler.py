#!/usr/bin/env python3

import unittest

from model.risk_exact import MemoryGeometry, risk_from_mission_probability
from model.schedule_compiler import (
    compile_adaptive_current_schedule,
    compile_fixed_allowed_schedule,
    floor_down_to_period_set,
    normalize_period_set,
    tau_schedule_from_c_over_estimate,
)


class ScheduleCompilerTests(unittest.TestCase):
    def test_normalize_period_set(self):
        self.assertEqual(normalize_period_set([10, 1, 5, 5, 2]), (1.0, 2.0, 5.0, 10.0))

    def test_floor_down_to_period_set(self):
        periods = (1.0, 2.0, 5.0, 10.0)
        self.assertEqual(floor_down_to_period_set(0.1, periods), 1.0)
        self.assertEqual(floor_down_to_period_set(1.0, periods), 1.0)
        self.assertEqual(floor_down_to_period_set(4.9, periods), 2.0)
        self.assertEqual(floor_down_to_period_set(5.0, periods), 5.0)
        self.assertEqual(floor_down_to_period_set(9.9, periods), 5.0)
        self.assertEqual(floor_down_to_period_set(100.0, periods), 10.0)

    def test_tau_schedule_from_c_over_estimate(self):
        periods = (1.0, 2.0, 5.0, 10.0, 30.0)
        tau, indices = tau_schedule_from_c_over_estimate(
            estimate_values=[10.0, 1.0],
            c_value=10.0 / 3600.0,
            period_set_seconds=periods,
        )

        self.assertEqual(tau, [1.0, 10.0])
        self.assertEqual(indices, [0, 3])

    def test_saturation_flags(self):
        geometry = MemoryGeometry(word_bits=39, codeword_count=4096)
        nu_values = [1.0, 30.0, 1.0, 30.0]
        dt_hours = [1.0 for _ in nu_values]
        target_e = risk_from_mission_probability(0.001)
        periods = (1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)

        result = compile_adaptive_current_schedule(
            nu_values=nu_values,
            dt_hours=dt_hours,
            target_e=target_e,
            period_set_seconds=periods,
            geometry=geometry,
        )

        self.assertEqual(result.stats.saturated_at_tau_min, min(result.tau_seconds) == min(periods))
        self.assertEqual(result.stats.saturated_at_tau_max, max(result.tau_seconds) == max(periods))

    def test_adaptive_schedule_respects_exact_target(self):
        geometry = MemoryGeometry(word_bits=39, codeword_count=4096)
        nu_values = [1.0, 30.0, 1.0, 30.0, 1.0, 30.0]
        dt_hours = [1.0 for _ in nu_values]
        target_e = risk_from_mission_probability(0.001)
        periods = (1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)

        result = compile_adaptive_current_schedule(
            nu_values=nu_values,
            dt_hours=dt_hours,
            target_e=target_e,
            period_set_seconds=periods,
            geometry=geometry,
        )

        self.assertLessEqual(result.stats.risk_e, target_e)
        self.assertTrue(all(tau in periods for tau in result.tau_seconds))

    def test_adaptive_not_worse_than_fixed_on_variable_series(self):
        geometry = MemoryGeometry(word_bits=39, codeword_count=4096)
        nu_values = [1.0, 30.0, 1.0, 30.0, 1.0, 30.0]
        dt_hours = [1.0 for _ in nu_values]
        target_e = risk_from_mission_probability(0.001)
        periods = (1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)

        adaptive = compile_adaptive_current_schedule(
            nu_values=nu_values,
            dt_hours=dt_hours,
            target_e=target_e,
            period_set_seconds=periods,
            geometry=geometry,
        )

        fixed = compile_fixed_allowed_schedule(
            nu_values=nu_values,
            dt_hours=dt_hours,
            target_e=target_e,
            period_set_seconds=periods,
            geometry=geometry,
        )

        self.assertLessEqual(adaptive.stats.risk_e, target_e)
        self.assertLessEqual(fixed.stats.risk_e, target_e)
        self.assertLessEqual(adaptive.stats.pass_count, fixed.stats.pass_count)


if __name__ == "__main__":
    unittest.main()
