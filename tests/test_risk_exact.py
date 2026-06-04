#!/usr/bin/env python3

import unittest

from model.risk_exact import (
    MemoryGeometry,
    accumulated_risk_for_schedule,
    mission_probability_from_risk,
    p_acc_given_k,
    q_acc_exact,
    q_acc_quadratic,
    risk_from_mission_probability,
    scrub_pass_count,
)


class RiskExactTests(unittest.TestCase):
    def test_alpha_for_default_geometry(self):
        geometry = MemoryGeometry()
        expected = (39 - 1) / (2.0 * (39 * 1_935_832 - 1))
        self.assertAlmostEqual(geometry.alpha, expected)

    def test_p_acc_zero_for_less_than_two_errors(self):
        geometry = MemoryGeometry(word_bits=39, codeword_count=100)
        self.assertEqual(p_acc_given_k(0, geometry), 0.0)
        self.assertEqual(p_acc_given_k(1, geometry), 0.0)

    def test_p_acc_two_errors_matches_pair_probability(self):
        geometry = MemoryGeometry(word_bits=39, codeword_count=1000)
        expected = (geometry.word_bits - 1) / (geometry.physical_bits - 1)
        self.assertAlmostEqual(p_acc_given_k(2, geometry), expected, places=14)

    def test_p_acc_is_one_when_errors_exceed_codewords(self):
        geometry = MemoryGeometry(word_bits=39, codeword_count=4)
        self.assertEqual(p_acc_given_k(5, geometry), 1.0)

    def test_q_exact_zero_at_zero_lambda(self):
        self.assertEqual(q_acc_exact(0.0), 0.0)

    def test_q_exact_matches_quadratic_for_small_lambda(self):
        geometry = MemoryGeometry()
        for lambda_value in (1e-4, 3e-4, 1e-3, 3e-3, 1e-2):
            exact = q_acc_exact(lambda_value, geometry)
            approx = q_acc_quadratic(lambda_value, geometry)
            rel_error = abs(exact - approx) / exact if exact else 0.0
            self.assertLess(rel_error, 1e-4)

    def test_risk_probability_conversion_roundtrip(self):
        p = 0.01
        e = risk_from_mission_probability(p)
        self.assertAlmostEqual(mission_probability_from_risk(e), p)

    def test_accumulated_risk_exact_and_quadratic_close_for_small_values(self):
        geometry = MemoryGeometry()
        nu = [0.1, 0.2, 0.3]
        tau = [1.0 / 3600.0, 2.0 / 3600.0, 5.0 / 3600.0]
        dt = [1.0, 1.0, 1.0]

        exact = accumulated_risk_for_schedule(nu, tau, dt, geometry, kernel="exact")
        approx = accumulated_risk_for_schedule(nu, tau, dt, geometry, kernel="quadratic")

        rel_error = abs(exact - approx) / exact if exact else 0.0
        self.assertLess(rel_error, 1e-4)

    def test_scrub_pass_count(self):
        tau = [1.0, 2.0, 4.0]
        dt = [4.0, 4.0, 4.0]
        self.assertEqual(scrub_pass_count(tau, dt), 7.0)


if __name__ == "__main__":
    unittest.main()
