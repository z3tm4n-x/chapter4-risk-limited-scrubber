#!/usr/bin/env python3

import unittest

from model.envelope import (
    ARCHITECTURE_CHANGE_REQUIRED,
    BANDWIDTH_OR_TAU_MIN_INSUFFICIENT,
    SCRUB_PERIOD_SELECTABLE,
    classify_feasibility,
    compute_g_d,
    evaluate_feasibility_case,
    residual_budget_e,
)
from model.risk_exact import MemoryGeometry, risk_from_mission_probability


class EnvelopeTests(unittest.TestCase):
    def test_compute_g_d(self):
        pm = {1: 0.97, 2: 0.02, 3: 0.01}
        hmd = {2: 0.1, 3: 0.5}
        self.assertAlmostEqual(compute_g_d(pm, hmd), 0.007)

    def test_residual_budget(self):
        self.assertAlmostEqual(residual_budget_e(1.0, 0.25), 0.75)

    def test_classify_architecture_change_required(self):
        self.assertEqual(
            classify_feasibility(target_e=1.0, e_inst=1.0, e_acc_at_tau_min=0.0),
            ARCHITECTURE_CHANGE_REQUIRED,
        )

    def test_classify_bandwidth_insufficient(self):
        self.assertEqual(
            classify_feasibility(target_e=1.0, e_inst=0.1, e_acc_at_tau_min=0.95),
            BANDWIDTH_OR_TAU_MIN_INSUFFICIENT,
        )

    def test_classify_selectable(self):
        self.assertEqual(
            classify_feasibility(target_e=1.0, e_inst=0.1, e_acc_at_tau_min=0.5),
            SCRUB_PERIOD_SELECTABLE,
        )

    def test_evaluate_selectable_case(self):
        geometry = MemoryGeometry(word_bits=39, codeword_count=4096)
        target_e = risk_from_mission_probability(0.001)

        result = evaluate_feasibility_case(
            case_name="selectable",
            description="safe mapping plus low accumulated risk",
            target_e=target_e,
            event_count=1000.0,
            pm={1: 0.97, 2: 0.02, 3: 0.01},
            hmd={2: 0.0, 3: 0.0},
            nu_values=[1.0, 30.0, 1.0],
            dt_hours=[1.0, 1.0, 1.0],
            tau_min_seconds=1.0,
            geometry=geometry,
        )

        self.assertEqual(result.status, SCRUB_PERIOD_SELECTABLE)
        self.assertGreaterEqual(result.risk_slack_after_tau_min, 0.0)


if __name__ == "__main__":
    unittest.main()
