#!/usr/bin/env python3
"""Seed-robustness sweep for measured-error policies.

This script repeats selected measured-policy simulations over multiple Poisson
sampling seeds. It is intentionally policy-level, not RTL-level.

Goal:
  - distinguish aggressive settings that sometimes/always violate risk;
  - identify conservative onboard measured-error settings that robustly meet
    the exact accumulated-risk target on the five-year series.
"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from model.risk_exact import (
    MemoryGeometry,
    mission_probability_from_risk,
    q_acc_exact,
    risk_from_mission_probability,
)


CONFIG_PATH = REPO_ROOT / "configs" / "ch3_main_1pct.json"
SERIES_PATH = REPO_ROOT / "data" / "ch3_five_year_upsets.csv"
SCHEDULE_SUMMARY = REPO_ROOT / "results" / "schedules" / "ch3_five_year_summary.csv"

OUT_DETAIL_CSV = REPO_ROOT / "results" / "schedules" / "measured_policy_seed_sweep_detail.csv"
OUT_SUMMARY_CSV = REPO_ROOT / "results" / "schedules" / "measured_policy_seed_sweep_summary.csv"
OUT_MD = REPO_ROOT / "results" / "schedules" / "measured_policy_seed_sweep_report.md"
OUT_JSON = REPO_ROOT / "results" / "schedules" / "measured_policy_seed_sweep_certificate.json"

BASE_SEED = 20260650
SEED_COUNT = 30


@dataclass(frozen=True)
class Policy:
    name: str
    initial_index: int
    min_index: int
    max_index: int
    high_threshold: int
    quiet_threshold: int
    speedup_step: int = 1
    relax_step: int = 1


POLICIES = [
    Policy("measured_q8_high1_max120", initial_index=6, min_index=0, max_index=6, high_threshold=1, quiet_threshold=8),
    Policy("measured_q16_high1_max120", initial_index=6, min_index=0, max_index=6, high_threshold=1, quiet_threshold=16),
    Policy("measured_q16_high1_max3600", initial_index=6, min_index=0, max_index=11, high_threshold=1, quiet_threshold=16),
    Policy("measured_q32_high1_max120", initial_index=6, min_index=0, max_index=6, high_threshold=1, quiet_threshold=32),
]


def read_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_series() -> list[float]:
    values: list[float] = []

    with SERIES_PATH.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            values.append(float(row["upsets_total_nu"]))

    if not values:
        raise RuntimeError("empty series")

    return values


def read_schedule_summary() -> dict[str, dict[str, str]]:
    with SCHEDULE_SUMMARY.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    return {row["strategy_key"]: row for row in rows}


def poisson_sample(lambda_value: float, rng: random.Random) -> int:
    if lambda_value <= 0.0:
        return 0

    if lambda_value < 30.0:
        threshold = math.exp(-lambda_value)
        product = 1.0
        k = 0

        while product > threshold:
            k += 1
            product *= rng.random()

        return k - 1

    sample = int(round(rng.gauss(lambda_value, math.sqrt(lambda_value))))
    return max(0, sample)


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def q_exact_cached(lambda_value: float, geometry: MemoryGeometry, cache: dict[float, float]) -> float:
    key = round(lambda_value, 12)

    if key not in cache:
        cache[key] = q_acc_exact(lambda_value, geometry)

    return cache[key]


def simulate_policy(
    policy: Policy,
    nu_values: list[float],
    periods: list[float],
    geometry: MemoryGeometry,
    target_e: float,
    seed: int,
) -> dict[str, str]:
    rng = random.Random(seed)
    q_cache: dict[float, float] = {}

    idx = clamp(policy.initial_index, policy.min_index, policy.max_index)
    quiet_count = 0

    hour_index = 0
    offset_seconds = 0.0

    risk_e = 0.0
    pass_count = 0
    observed_corrections = 0
    high_activity_events = 0
    relax_events = 0
    tau_sum = 0.0
    tau_min = float("inf")
    tau_max = 0.0

    while hour_index < len(nu_values):
        tau_seconds = periods[idx]
        remaining = tau_seconds
        lambda_interval = 0.0

        while remaining > 1e-12 and hour_index < len(nu_values):
            available = 3600.0 - offset_seconds
            chunk = min(remaining, available)

            lambda_interval += nu_values[hour_index] * (chunk / 3600.0)

            remaining -= chunk
            offset_seconds += chunk

            if offset_seconds >= 3600.0 - 1e-12:
                hour_index += 1
                offset_seconds = 0.0

        if lambda_interval <= 0.0 and hour_index >= len(nu_values):
            break

        risk_e += q_exact_cached(lambda_interval, geometry, q_cache)
        observed = poisson_sample(lambda_interval, rng)

        pass_count += 1
        tau_sum += tau_seconds
        tau_min = min(tau_min, tau_seconds)
        tau_max = max(tau_max, tau_seconds)
        observed_corrections += observed

        if observed >= policy.high_threshold:
            idx = clamp(idx - policy.speedup_step, policy.min_index, policy.max_index)
            quiet_count = 0
            high_activity_events += 1
        elif observed == 0:
            quiet_count += 1

            if quiet_count >= policy.quiet_threshold:
                idx = clamp(idx + policy.relax_step, policy.min_index, policy.max_index)
                quiet_count = 0
                relax_events += 1
        else:
            quiet_count = 0

    p_mission = mission_probability_from_risk(risk_e)

    return {
        "policy": policy.name,
        "seed": str(seed),
        "target_e": f"{target_e:.12g}",
        "risk_e": f"{risk_e:.12g}",
        "p_mission": f"{p_mission:.12g}",
        "risk_utilization": f"{risk_e / target_e:.12g}",
        "target_met": str(risk_e <= target_e).lower(),
        "pass_count": str(pass_count),
        "mean_tau_seconds": f"{tau_sum / pass_count:.12g}",
        "min_tau_seconds": f"{tau_min:.12g}",
        "max_tau_seconds": f"{tau_max:.12g}",
        "observed_corrections": str(observed_corrections),
        "high_activity_events": str(high_activity_events),
        "relax_events": str(relax_events),
        "q_cache_entries": str(len(q_cache)),
    }


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("empty values")

    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)

    if lo == hi:
        return ordered[lo]

    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def summarize_policy(policy: str, rows: list[dict[str, str]], fixed_passes: float, current_passes: float) -> dict[str, str]:
    risk_utils = [float(row["risk_utilization"]) for row in rows]
    pass_counts = [float(row["pass_count"]) for row in rows]
    p_missions = [float(row["p_mission"]) for row in rows]

    target_met_count = sum(1 for row in rows if row["target_met"] == "true")

    pass_mean = mean(pass_counts)

    return {
        "policy": policy,
        "seed_count": str(len(rows)),
        "target_met_count": str(target_met_count),
        "target_met_fraction": f"{target_met_count / len(rows):.12g}",
        "risk_utilization_min": f"{min(risk_utils):.12g}",
        "risk_utilization_mean": f"{mean(risk_utils):.12g}",
        "risk_utilization_p95": f"{percentile(risk_utils, 0.95):.12g}",
        "risk_utilization_max": f"{max(risk_utils):.12g}",
        "p_mission_mean": f"{mean(p_missions):.12g}",
        "p_mission_max": f"{max(p_missions):.12g}",
        "pass_count_min": f"{min(pass_counts):.12g}",
        "pass_count_mean": f"{pass_mean:.12g}",
        "pass_count_max": f"{max(pass_counts):.12g}",
        "fixed_over_policy_gain_mean": f"{fixed_passes / pass_mean:.12g}",
        "current_over_policy_pass_ratio_mean": f"{current_passes / pass_mean:.12g}",
    }


def write_outputs(
    detail_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    schedule_rows: dict[str, dict[str, str]],
) -> None:
    OUT_DETAIL_CSV.parent.mkdir(parents=True, exist_ok=True)

    detail_fields = [
        "policy",
        "seed",
        "target_e",
        "risk_e",
        "p_mission",
        "risk_utilization",
        "target_met",
        "pass_count",
        "mean_tau_seconds",
        "min_tau_seconds",
        "max_tau_seconds",
        "observed_corrections",
        "high_activity_events",
        "relax_events",
        "q_cache_entries",
    ]

    summary_fields = [
        "policy",
        "seed_count",
        "target_met_count",
        "target_met_fraction",
        "risk_utilization_min",
        "risk_utilization_mean",
        "risk_utilization_p95",
        "risk_utilization_max",
        "p_mission_mean",
        "p_mission_max",
        "pass_count_min",
        "pass_count_mean",
        "pass_count_max",
        "fixed_over_policy_gain_mean",
        "current_over_policy_pass_ratio_mean",
    ]

    with OUT_DETAIL_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(detail_rows)

    with OUT_SUMMARY_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    lines = [
        "# Measured-error policy seed sweep",
        "",
        "This report repeats selected measured-error policy simulations over",
        f"`{SEED_COUNT}` Poisson seeds per policy.",
        "",
        "## Baselines",
        "",
        "| Strategy | Pass count | P mission | Risk utilization |",
        "|---|---:|---:|---:|",
        f"| fixed | {schedule_rows['fixed']['pass_count']} | {schedule_rows['fixed']['p_mission']} | {schedule_rows['fixed']['risk_utilization']} |",
        f"| current adaptive | {schedule_rows['current']['pass_count']} | {schedule_rows['current']['p_mission']} | {schedule_rows['current']['risk_utilization']} |",
        f"| delayed 1h adaptive | {schedule_rows['delayed_1h']['pass_count']} | {schedule_rows['delayed_1h']['p_mission']} | {schedule_rows['delayed_1h']['risk_utilization']} |",
        "",
        "## Seed sweep summary",
        "",
        "| Policy | Target met fraction | Risk util. mean | Risk util. p95 | Risk util. max | Pass mean | Fixed/policy gain mean | Current/policy pass ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in summary_rows:
        lines.append(
            f"| {row['policy']} | {row['target_met_fraction']} | "
            f"{row['risk_utilization_mean']} | {row['risk_utilization_p95']} | "
            f"{row['risk_utilization_max']} | {row['pass_count_mean']} | "
            f"{row['fixed_over_policy_gain_mean']} | {row['current_over_policy_pass_ratio_mean']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Policies with `target_met_fraction=1` satisfy the exact-risk target across all sampled seeds.",
            "- Aggressive policies can be useful as demonstrations of adaptation but are not certified replacements if they exceed the target.",
            "- The external Chapter 3 current/delayed schedules remain the primary risk-certified strategies.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "base_seed": BASE_SEED,
                "seed_count": SEED_COUNT,
                "summary_rows": summary_rows,
                "detail_rows": detail_rows,
                "baselines": schedule_rows,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Wrote", OUT_DETAIL_CSV)
    print("Wrote", OUT_SUMMARY_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print()
    print(OUT_SUMMARY_CSV.read_text(encoding="utf-8"))


def main() -> int:
    config = read_config()
    nu_values = read_series()
    schedule_rows = read_schedule_summary()

    geometry = MemoryGeometry(
        word_bits=int(config["geometry"]["word_bits"]),
        codeword_count=int(config["geometry"]["codeword_count"]),
    )

    periods = [float(value) for value in config["period_set_seconds"]]
    target_e = risk_from_mission_probability(float(config["target_mission_probability"]))

    detail_rows: list[dict[str, str]] = []

    for policy_index, policy in enumerate(POLICIES):
        for seed_offset in range(SEED_COUNT):
            seed = BASE_SEED + policy_index * 1000 + seed_offset
            detail_rows.append(
                simulate_policy(policy, nu_values, periods, geometry, target_e, seed)
            )

    fixed_passes = float(schedule_rows["fixed"]["pass_count"])
    current_passes = float(schedule_rows["current"]["pass_count"])

    summary_rows = []

    for policy in POLICIES:
        rows = [row for row in detail_rows if row["policy"] == policy.name]
        summary_rows.append(summarize_policy(policy.name, rows, fixed_passes, current_passes))

    write_outputs(detail_rows, summary_rows, schedule_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
