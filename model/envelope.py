#!/usr/bin/env python3
"""
Protection-envelope and feasibility checks.

This module implements the Chapter 2 handoff to Chapter 3:

    p_m, h_m^(D) -> g_D -> E_inst -> E_residual
    E_acc(tau_min) <= E_residual ?

The scrub-period scheduler is only applicable if the instant dangerous-state
component does not consume the mission risk budget and the accumulated component
is still feasible at the minimum hardware scrub period.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from model.risk_exact import (
    MemoryGeometry,
    accumulated_risk_for_schedule,
    mission_probability_from_risk,
)


ARCHITECTURE_CHANGE_REQUIRED = "architecture_change_required"
BANDWIDTH_OR_TAU_MIN_INSUFFICIENT = "bandwidth_or_tau_min_insufficient"
SCRUB_PERIOD_SELECTABLE = "scrub_period_selectable"


@dataclass(frozen=True)
class FeasibilityResult:
    """Result of the Chapter 2 protection-envelope feasibility check."""

    case_name: str
    description: str
    status: str
    target_e: float
    event_count: float
    g_d: float
    e_inst: float
    e_residual: float
    e_acc_at_tau_min: float
    tau_min_seconds: float
    risk_slack_after_tau_min: float

    @property
    def target_probability(self) -> float:
        return mission_probability_from_risk(self.target_e)

    @property
    def instant_utilization(self) -> float:
        if self.target_e == 0.0:
            return float("inf")
        return self.e_inst / self.target_e

    @property
    def residual_utilization_at_tau_min(self) -> float:
        if self.e_residual <= 0.0:
            return float("inf")
        return self.e_acc_at_tau_min / self.e_residual


def validate_probability_distribution(pm: Mapping[int, float]) -> None:
    """Validate physical multiplicity distribution p_m."""
    if not pm:
        raise ValueError("pm distribution must not be empty")

    total = 0.0

    for multiplicity, probability in pm.items():
        if multiplicity < 1:
            raise ValueError(f"multiplicity must be >= 1: {multiplicity}")
        if probability < 0.0:
            raise ValueError(f"p_m must be non-negative for m={multiplicity}")
        total += probability

    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"pm probabilities must sum to 1.0, got {total}")


def validate_mapping_probabilities(hmd: Mapping[int, float]) -> None:
    """Validate logical dangerous-mapping probabilities h_m^(D)."""
    for multiplicity, probability in hmd.items():
        if multiplicity < 1:
            raise ValueError(f"multiplicity must be >= 1: {multiplicity}")
        if probability < 0.0 or probability > 1.0:
            raise ValueError(f"h_m must be inside [0, 1] for m={multiplicity}")


def compute_g_d(
    pm: Mapping[int, float],
    hmd: Mapping[int, float],
) -> float:
    """
    Compute g_D = sum_{m>=2} p_m * h_m^(D).

    Missing h_m values are treated as zero only for m=1. For m>=2, they must be
    provided explicitly to avoid accidental undercounting.
    """
    validate_probability_distribution(pm)
    validate_mapping_probabilities(hmd)

    g_d = 0.0

    for multiplicity, probability in pm.items():
        if multiplicity == 1:
            continue

        if multiplicity not in hmd:
            raise ValueError(f"missing h_m^(D) for m={multiplicity}")

        g_d += probability * hmd[multiplicity]

    return g_d


def instant_risk_e(
    event_count: float,
    g_d: float,
) -> float:
    """Expected instant dangerous-state risk measure E_inst = N_events * g_D."""
    if event_count < 0.0:
        raise ValueError("event_count must be non-negative")
    if g_d < 0.0 or g_d > 1.0:
        raise ValueError("g_d must be inside [0, 1]")

    return event_count * g_d


def residual_budget_e(
    target_e: float,
    e_inst: float,
) -> float:
    """Residual accumulated-risk budget E_residual = E_target - E_inst."""
    if target_e <= 0.0:
        raise ValueError("target_e must be positive")
    if e_inst < 0.0:
        raise ValueError("e_inst must be non-negative")

    return target_e - e_inst


def accumulated_risk_at_tau_min(
    nu_values: list[float],
    dt_hours: list[float],
    tau_min_seconds: float,
    geometry: MemoryGeometry,
) -> float:
    """Exact accumulated risk when every interval uses the minimum scrub period."""
    if tau_min_seconds <= 0.0:
        raise ValueError("tau_min_seconds must be positive")

    tau_hours = [tau_min_seconds / 3600.0 for _ in nu_values]

    return accumulated_risk_for_schedule(
        nu_values=nu_values,
        tau_values=tau_hours,
        dt_values=dt_hours,
        geometry=geometry,
        kernel="exact",
    )


def classify_feasibility(
    target_e: float,
    e_inst: float,
    e_acc_at_tau_min: float,
) -> str:
    """
    Classify the design point into the Chapter 2 protection-envelope regions.
    """
    e_residual = residual_budget_e(target_e, e_inst)

    if e_residual <= 0.0:
        return ARCHITECTURE_CHANGE_REQUIRED

    if e_acc_at_tau_min > e_residual:
        return BANDWIDTH_OR_TAU_MIN_INSUFFICIENT

    return SCRUB_PERIOD_SELECTABLE


def evaluate_feasibility_case(
    *,
    case_name: str,
    description: str,
    target_e: float,
    event_count: float,
    pm: Mapping[int, float],
    hmd: Mapping[int, float],
    nu_values: list[float],
    dt_hours: list[float],
    tau_min_seconds: float,
    geometry: MemoryGeometry,
) -> FeasibilityResult:
    """Evaluate a complete Chapter 2 -> Chapter 3 feasibility case."""
    if len(nu_values) != len(dt_hours):
        raise ValueError("nu_values and dt_hours length mismatch")

    g_d = compute_g_d(pm, hmd)
    e_inst = instant_risk_e(event_count, g_d)
    e_residual = residual_budget_e(target_e, e_inst)

    e_acc_min = accumulated_risk_at_tau_min(
        nu_values=nu_values,
        dt_hours=dt_hours,
        tau_min_seconds=tau_min_seconds,
        geometry=geometry,
    )

    status = classify_feasibility(
        target_e=target_e,
        e_inst=e_inst,
        e_acc_at_tau_min=e_acc_min,
    )

    return FeasibilityResult(
        case_name=case_name,
        description=description,
        status=status,
        target_e=target_e,
        event_count=event_count,
        g_d=g_d,
        e_inst=e_inst,
        e_residual=e_residual,
        e_acc_at_tau_min=e_acc_min,
        tau_min_seconds=tau_min_seconds,
        risk_slack_after_tau_min=e_residual - e_acc_min,
    )
