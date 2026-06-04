#!/usr/bin/env python3
"""
Exact and quadratic accumulated-risk kernels for SEC-DED scrub analysis.

This module implements the Chapter 2 accumulated dangerous-state model.

Definitions:
    n  = number of bits in one protected codeword
    W  = number of protected codewords
    N  = n * W physical protected bits
    alpha = (n - 1) / (2 * (N - 1))

For k independent single-bit errors placed uniformly without replacement over
the protected array, the dangerous state occurs if at least two errors fall into
the same codeword.

The exact conditional probability is:

    P_acc(k) = 1 - C(W, k) * n^k / C(N, k),  k <= W

and P_acc(k)=1 for k>W.

The exact per-scrub-cycle probability for Poisson mean lambda is:

    q_acc(lambda) = sum_k Pois(k; lambda) * P_acc(k)

The quadratic rare-event approximation is:

    q_acc(lambda) ~= alpha * lambda^2
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


DEFAULT_WORD_BITS = 39
DEFAULT_CODEWORD_COUNT = 1_935_832


@dataclass(frozen=True)
class MemoryGeometry:
    """Protected memory geometry used by the accumulated-risk model."""

    word_bits: int = DEFAULT_WORD_BITS
    codeword_count: int = DEFAULT_CODEWORD_COUNT

    @property
    def physical_bits(self) -> int:
        return self.word_bits * self.codeword_count

    @property
    def alpha(self) -> float:
        return (self.word_bits - 1) / (2.0 * (self.physical_bits - 1))


def validate_geometry(geometry: MemoryGeometry) -> None:
    if geometry.word_bits <= 1:
        raise ValueError("word_bits must be greater than 1")
    if geometry.codeword_count <= 0:
        raise ValueError("codeword_count must be positive")


def p_acc_given_k(k: int, geometry: MemoryGeometry = MemoryGeometry()) -> float:
    """
    Exact conditional probability of accumulated dangerous placement.

    k is the number of independent single-bit errors present before the next
    scrub check of the affected codewords.

    The implementation uses a stable product for the safe probability instead
    of explicitly evaluating huge binomial coefficients.
    """
    validate_geometry(geometry)

    if k < 0:
        raise ValueError("k must be non-negative")

    if k < 2:
        return 0.0

    word_bits = geometry.word_bits
    word_count = geometry.codeword_count
    physical_bits = geometry.physical_bits

    if k > word_count:
        return 1.0

    safe_probability = 1.0

    for j in range(k):
        numerator = (word_count - j) * word_bits
        denominator = physical_bits - j
        safe_probability *= numerator / denominator

    dangerous_probability = 1.0 - safe_probability

    if dangerous_probability < 0.0 and dangerous_probability > -1e-15:
        return 0.0
    if dangerous_probability > 1.0 and dangerous_probability < 1.0 + 1e-15:
        return 1.0

    return dangerous_probability


def q_acc_quadratic(
    lambda_value: float,
    geometry: MemoryGeometry = MemoryGeometry(),
) -> float:
    """Quadratic rare-event approximation q(lambda) ~= alpha * lambda^2."""
    validate_geometry(geometry)

    if lambda_value < 0.0:
        raise ValueError("lambda_value must be non-negative")

    return geometry.alpha * lambda_value * lambda_value


def q_acc_exact(
    lambda_value: float,
    geometry: MemoryGeometry = MemoryGeometry(),
    *,
    tail_tolerance: float = 1e-16,
    max_terms: int = 100_000,
) -> float:
    """
    Exact Poisson-averaged accumulated dangerous-state probability.

    The truncation error is bounded by the unprocessed Poisson tail because
    0 <= P_acc(k) <= 1.

    The stop condition uses an upper bound for the remaining Poisson tail rather
    than 1 - cumulative_mass. This avoids non-convergence at very small lambda,
    where floating-point cumulative mass can stop just below 1.0.
    """
    validate_geometry(geometry)

    if lambda_value < 0.0:
        raise ValueError("lambda_value must be non-negative")

    if lambda_value == 0.0:
        return 0.0

    poisson_k = math.exp(-lambda_value)
    result = poisson_k * p_acc_given_k(0, geometry)

    k = 0

    while k < max_terms:
        k += 1
        poisson_k *= lambda_value / k

        result += poisson_k * p_acc_given_k(k, geometry)

        # Bound the remaining tail after term k by a geometric majorant for the
        # subsequent Poisson terms. The next ratio is lambda/(k+1), and once it
        # is below one the remaining series is bounded by next_term/(1-ratio).
        next_ratio = lambda_value / (k + 1)

        if next_ratio < 1.0:
            next_term = poisson_k * next_ratio
            tail_bound = next_term / (1.0 - next_ratio)

            if tail_bound <= tail_tolerance:
                break
    else:
        raise RuntimeError(
            f"q_acc_exact did not converge for lambda={lambda_value} "
            f"within max_terms={max_terms}"
        )

    if result < 0.0 and result > -1e-15:
        return 0.0
    if result > 1.0 and result < 1.0 + 1e-15:
        return 1.0

    return result


def mission_probability_from_risk(risk_e: float) -> float:
    """Convert additive risk measure E to mission probability."""
    if risk_e < 0.0:
        raise ValueError("risk_e must be non-negative")
    return 1.0 - math.exp(-risk_e)


def risk_from_mission_probability(probability: float) -> float:
    """Convert mission probability to additive risk measure E."""
    if probability <= 0.0 or probability >= 1.0:
        raise ValueError("probability must be inside (0, 1)")
    return -math.log(1.0 - probability)


def accumulated_risk_for_schedule(
    nu_values: Iterable[float],
    tau_values: Iterable[float],
    dt_values: Iterable[float],
    geometry: MemoryGeometry = MemoryGeometry(),
    *,
    kernel: str = "exact",
) -> float:
    """
    Accumulated risk for a piecewise-constant scrub schedule.

    nu_values: expected single-bit error rate per hour for each interval
    tau_values: scrub period in hours for each interval
    dt_values: interval duration in hours

    Contribution:
        (dt_i / tau_i) * q_acc(nu_i * tau_i)
    """
    validate_geometry(geometry)

    risk = 0.0

    for index, (nu_value, tau_value, dt_value) in enumerate(
        zip(nu_values, tau_values, dt_values, strict=True)
    ):
        if nu_value < 0.0:
            raise ValueError(f"nu[{index}] must be non-negative")
        if tau_value <= 0.0:
            raise ValueError(f"tau[{index}] must be positive")
        if dt_value <= 0.0:
            raise ValueError(f"dt[{index}] must be positive")

        lambda_value = nu_value * tau_value

        if kernel == "exact":
            q_value = q_acc_exact(lambda_value, geometry)
        elif kernel == "quadratic":
            q_value = q_acc_quadratic(lambda_value, geometry)
        else:
            raise ValueError(f"unsupported kernel: {kernel}")

        risk += (dt_value / tau_value) * q_value

    return risk


def scrub_pass_count(
    tau_values: Iterable[float],
    dt_values: Iterable[float],
) -> float:
    """Continuous approximation of the number of full scrub passes."""
    total = 0.0

    for index, (tau_value, dt_value) in enumerate(
        zip(tau_values, dt_values, strict=True)
    ):
        if tau_value <= 0.0:
            raise ValueError(f"tau[{index}] must be positive")
        if dt_value <= 0.0:
            raise ValueError(f"dt[{index}] must be positive")

        total += dt_value / tau_value

    return total
