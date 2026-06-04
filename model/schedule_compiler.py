#!/usr/bin/env python3
"""
Implementable scrub-period schedule compiler.

This module implements the Chapter 3 hardware-aware step:

    tau_calc_i = C / nu_hat_i
    tau_impl_i = floor_down_to_period_set(tau_calc_i, T)

The resulting schedule is verified with the exact accumulated-risk kernel from
model.risk_exact, not with the quadratic approximation.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable

from model.risk_exact import (
    MemoryGeometry,
    accumulated_risk_for_schedule,
    mission_probability_from_risk,
    scrub_pass_count,
)


EPS_NU = 1e-30


DEFAULT_PERIOD_SET_SECONDS = (
    1.0,
    2.0,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
    300.0,
    600.0,
    1200.0,
    1800.0,
    3600.0,
)


@dataclass(frozen=True)
class ScheduleStats:
    """Risk and resource statistics for an implementable scrub schedule."""

    risk_e: float
    p_mission: float
    pass_count: float
    mean_tau_seconds: float
    min_tau_seconds: float
    max_tau_seconds: float
    saturated_at_tau_min: bool
    saturated_at_tau_max: bool


@dataclass(frozen=True)
class ScheduleResult:
    """Compiled scrub schedule and its exact-risk certificate."""

    strategy: str
    c_value: float | None
    tau_seconds: list[float]
    period_indices: list[int]
    stats: ScheduleStats


def normalize_period_set(period_set_seconds: Iterable[float]) -> tuple[float, ...]:
    """Return a sorted unique positive period set in seconds."""
    values = sorted(set(float(value) for value in period_set_seconds))

    if not values:
        raise ValueError("period set must not be empty")

    for value in values:
        if value <= 0.0:
            raise ValueError(f"period must be positive: {value}")

    return tuple(values)


def period_index_for_seconds(
    tau_seconds: float,
    period_set_seconds: tuple[float, ...],
) -> int:
    """Return exact index of a period value in the normalized period set."""
    for index, period in enumerate(period_set_seconds):
        if tau_seconds == period:
            return index

    raise ValueError(f"tau_seconds={tau_seconds} is not in the period set")


def floor_down_to_period_set(
    tau_calc_seconds: float,
    period_set_seconds: Iterable[float],
) -> float:
    """
    Conservative hardware rounding from Chapter 3.

    If tau_calc is below the minimum allowed period, return tau_min.
    If tau_calc is above the maximum allowed period, return tau_max.
    Otherwise return the largest period in T that is <= tau_calc.
    """
    periods = normalize_period_set(period_set_seconds)

    if tau_calc_seconds <= periods[0]:
        return periods[0]

    if tau_calc_seconds >= periods[-1]:
        return periods[-1]

    selected = periods[0]

    for period in periods:
        if period <= tau_calc_seconds:
            selected = period
        else:
            break

    return selected


def validate_series(
    nu_values: list[float],
    estimate_values: list[float],
    dt_hours: list[float],
) -> None:
    if not nu_values:
        raise ValueError("nu_values must not be empty")

    if len(nu_values) != len(estimate_values):
        raise ValueError("nu_values and estimate_values length mismatch")

    if len(nu_values) != len(dt_hours):
        raise ValueError("nu_values and dt_hours length mismatch")

    for index, value in enumerate(nu_values):
        if value < 0.0:
            raise ValueError(f"nu[{index}] must be non-negative")

    for index, value in enumerate(estimate_values):
        if value < 0.0:
            raise ValueError(f"estimate[{index}] must be non-negative")

    for index, value in enumerate(dt_hours):
        if value <= 0.0:
            raise ValueError(f"dt_hours[{index}] must be positive")


def tau_schedule_from_c_over_estimate(
    estimate_values: list[float],
    c_value: float,
    period_set_seconds: Iterable[float],
) -> tuple[list[float], list[int]]:
    """
    Build implementable tau schedule in seconds from tau = C / nu_hat.

    C is expressed in error-count units because nu_hat is in 1/hour and tau is
    first computed in hours.
    """
    if c_value < 0.0:
        raise ValueError("c_value must be non-negative")

    periods = normalize_period_set(period_set_seconds)

    tau_seconds: list[float] = []
    period_indices: list[int] = []

    for estimate_value in estimate_values:
        safe_estimate = max(estimate_value, EPS_NU)
        tau_calc_hours = c_value / safe_estimate
        tau_calc_seconds = tau_calc_hours * 3600.0

        tau_impl_seconds = floor_down_to_period_set(
            tau_calc_seconds=tau_calc_seconds,
            period_set_seconds=periods,
        )

        tau_seconds.append(tau_impl_seconds)
        period_indices.append(period_index_for_seconds(tau_impl_seconds, periods))

    return tau_seconds, period_indices


def stats_for_tau_seconds(
    nu_values: list[float],
    tau_seconds: list[float],
    dt_hours: list[float],
    geometry: MemoryGeometry,
    period_set_seconds: Iterable[float] | None = None,
) -> ScheduleStats:
    """Compute exact accumulated risk and pass count for a tau schedule."""
    tau_hours = [value / 3600.0 for value in tau_seconds]

    if period_set_seconds is None:
        tau_min_seconds = min(tau_seconds)
        tau_max_seconds = max(tau_seconds)
    else:
        periods = normalize_period_set(period_set_seconds)
        tau_min_seconds = periods[0]
        tau_max_seconds = periods[-1]

    risk_e = accumulated_risk_for_schedule(
        nu_values=nu_values,
        tau_values=tau_hours,
        dt_values=dt_hours,
        geometry=geometry,
        kernel="exact",
    )

    passes = scrub_pass_count(
        tau_values=tau_hours,
        dt_values=dt_hours,
    )

    return ScheduleStats(
        risk_e=risk_e,
        p_mission=mission_probability_from_risk(risk_e),
        pass_count=passes,
        mean_tau_seconds=mean(tau_seconds),
        min_tau_seconds=min(tau_seconds),
        max_tau_seconds=max(tau_seconds),
        saturated_at_tau_min=min(tau_seconds) == tau_min_seconds,
        saturated_at_tau_max=max(tau_seconds) == tau_max_seconds,
    )


def compile_schedule_for_c(
    nu_values: list[float],
    estimate_values: list[float],
    dt_hours: list[float],
    c_value: float,
    target_e: float,
    period_set_seconds: Iterable[float] = DEFAULT_PERIOD_SET_SECONDS,
    geometry: MemoryGeometry = MemoryGeometry(),
    strategy: str = "adaptive",
) -> ScheduleResult:
    """Compile and verify an implementable schedule for a fixed C value."""
    del target_e  # Kept in the signature to make call sites explicit.

    validate_series(nu_values, estimate_values, dt_hours)
    periods = normalize_period_set(period_set_seconds)

    tau_seconds, period_indices = tau_schedule_from_c_over_estimate(
        estimate_values=estimate_values,
        c_value=c_value,
        period_set_seconds=periods,
    )

    stats = stats_for_tau_seconds(
        nu_values=nu_values,
        tau_seconds=tau_seconds,
        dt_hours=dt_hours,
        geometry=geometry,
        period_set_seconds=periods,
    )

    return ScheduleResult(
        strategy=strategy,
        c_value=c_value,
        tau_seconds=tau_seconds,
        period_indices=period_indices,
        stats=stats,
    )


def find_largest_c_under_exact_risk(
    nu_values: list[float],
    estimate_values: list[float],
    dt_hours: list[float],
    target_e: float,
    period_set_seconds: Iterable[float] = DEFAULT_PERIOD_SET_SECONDS,
    geometry: MemoryGeometry = MemoryGeometry(),
    strategy: str = "adaptive",
) -> ScheduleResult:
    """
    Find the largest useful C such that exact accumulated risk is <= target_e.

    Because tau is clamped to the finite period set, C is unbounded once all
    intervals have reached tau_max. In that case this function returns the
    smallest C that already selects tau_max everywhere.
    """
    if target_e <= 0.0:
        raise ValueError("target_e must be positive")

    validate_series(nu_values, estimate_values, dt_hours)
    periods = normalize_period_set(period_set_seconds)

    min_tau_seconds = [periods[0] for _ in nu_values]
    min_stats = stats_for_tau_seconds(
        nu_values=nu_values,
        tau_seconds=min_tau_seconds,
        dt_hours=dt_hours,
        geometry=geometry,
        period_set_seconds=periods,
    )

    if min_stats.risk_e > target_e:
        raise ValueError(
            "infeasible schedule: even tau_min exceeds the target risk "
            f"({min_stats.risk_e} > {target_e})"
        )

    max_tau_hours = periods[-1] / 3600.0
    c_all_max = max(max(value, EPS_NU) * max_tau_hours for value in estimate_values)

    all_max_result = compile_schedule_for_c(
        nu_values=nu_values,
        estimate_values=estimate_values,
        dt_hours=dt_hours,
        c_value=c_all_max,
        target_e=target_e,
        period_set_seconds=periods,
        geometry=geometry,
        strategy=strategy,
    )

    if all_max_result.stats.risk_e <= target_e:
        return all_max_result

    low = 0.0
    high = c_all_max

    best = compile_schedule_for_c(
        nu_values=nu_values,
        estimate_values=estimate_values,
        dt_hours=dt_hours,
        c_value=low,
        target_e=target_e,
        period_set_seconds=periods,
        geometry=geometry,
        strategy=strategy,
    )

    for _ in range(90):
        mid = 0.5 * (low + high)

        candidate = compile_schedule_for_c(
            nu_values=nu_values,
            estimate_values=estimate_values,
            dt_hours=dt_hours,
            c_value=mid,
            target_e=target_e,
            period_set_seconds=periods,
            geometry=geometry,
            strategy=strategy,
        )

        if candidate.stats.risk_e <= target_e:
            low = mid
            best = candidate
        else:
            high = mid

    return best


def compile_adaptive_current_schedule(
    nu_values: list[float],
    dt_hours: list[float],
    target_e: float,
    period_set_seconds: Iterable[float] = DEFAULT_PERIOD_SET_SECONDS,
    geometry: MemoryGeometry = MemoryGeometry(),
) -> ScheduleResult:
    """Compile a schedule using the ideal current estimate nu_hat=nu."""
    return find_largest_c_under_exact_risk(
        nu_values=nu_values,
        estimate_values=list(nu_values),
        dt_hours=dt_hours,
        target_e=target_e,
        period_set_seconds=period_set_seconds,
        geometry=geometry,
        strategy="adaptive_current_exact_floor_down",
    )


def compile_fixed_allowed_schedule(
    nu_values: list[float],
    dt_hours: list[float],
    target_e: float,
    period_set_seconds: Iterable[float] = DEFAULT_PERIOD_SET_SECONDS,
    geometry: MemoryGeometry = MemoryGeometry(),
) -> ScheduleResult:
    """Select the largest fixed allowed period whose exact risk is <= target_e."""
    validate_series(nu_values, list(nu_values), dt_hours)
    periods = normalize_period_set(period_set_seconds)

    best: ScheduleResult | None = None

    for period in periods:
        tau_seconds = [period for _ in nu_values]
        stats = stats_for_tau_seconds(
            nu_values=nu_values,
            tau_seconds=tau_seconds,
            dt_hours=dt_hours,
            geometry=geometry,
            period_set_seconds=periods,
        )

        if stats.risk_e <= target_e:
            best = ScheduleResult(
                strategy=f"fixed_allowed_{period:g}s",
                c_value=None,
                tau_seconds=tau_seconds,
                period_indices=[period_index_for_seconds(period, periods) for _ in nu_values],
                stats=stats,
            )

    if best is None:
        raise ValueError("infeasible fixed schedule: tau_min exceeds target risk")

    return best


def schedule_rows(
    result: ScheduleResult,
    nu_values: list[float],
    estimate_values: list[float],
    dt_hours: list[float],
) -> list[dict[str, str]]:
    """Return machine-readable rows for a compiled schedule."""
    validate_series(nu_values, estimate_values, dt_hours)

    rows: list[dict[str, str]] = []

    for index, (nu, estimate, dt, tau, period_index) in enumerate(
        zip(
            nu_values,
            estimate_values,
            dt_hours,
            result.tau_seconds,
            result.period_indices,
            strict=True,
        )
    ):
        rows.append(
            {
                "time_index": str(index),
                "nu": f"{nu:.12g}",
                "nu_hat": f"{estimate:.12g}",
                "dt_hours": f"{dt:.12g}",
                "tau_seconds": f"{tau:.12g}",
                "period_index": str(period_index),
                "passes": f"{dt / (tau / 3600.0):.12g}",
            }
        )

    return rows


def write_schedule_csv(
    path: Path,
    result: ScheduleResult,
    nu_values: list[float],
    estimate_values: list[float],
    dt_hours: list[float],
) -> None:
    """Write compiled schedule rows to CSV."""
    rows = schedule_rows(result, nu_values, estimate_values, dt_hours)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "time_index",
        "nu",
        "nu_hat",
        "dt_hours",
        "tau_seconds",
        "period_index",
        "passes",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
