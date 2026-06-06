#!/usr/bin/env python3
"""Semantic evaluation of measured-error period policies on the five-year row.

This is not RTL. It is a fast policy-level replay that answers whether an
onboard counter-based estimator can meet the Chapter 3 risk target on the
five-year nu(t) series.

The policy observes only Poisson-sampled corrected counts per completed pass:
  - count >= high_threshold -> speed up period index
  - quiet_threshold consecutive zero-count passes -> relax period index
  - risk is evaluated independently using q_acc_exact(lambda) on the true nu(t)

No radiation model is fed to the measured estimator.
"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path


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

OUT_CSV = REPO_ROOT / "results" / "schedules" / "measured_policy_model_summary.csv"
OUT_MD = REPO_ROOT / "results" / "schedules" / "measured_policy_model_report.md"
OUT_JSON = REPO_ROOT / "results" / "schedules" / "measured_policy_model_certificate.json"

SEED = 20260605


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
    Policy("measured_q4_high1_max120", initial_index=6, min_index=0, max_index=6, high_threshold=1, quiet_threshold=4),
    Policy("measured_q8_high1_max120", initial_index=6, min_index=0, max_index=6, high_threshold=1, quiet_threshold=8),
    Policy("measured_q16_high1_max120", initial_index=6, min_index=0, max_index=6, high_threshold=1, quiet_threshold=16),
    Policy("measured_q32_high1_max120", initial_index=6, min_index=0, max_index=6, high_threshold=1, quiet_threshold=32),
    Policy("measured_q64_high1_max120", initial_index=6, min_index=0, max_index=6, high_threshold=1, quiet_threshold=64),
    Policy("measured_q16_high1_max3600", initial_index=6, min_index=0, max_index=11, high_threshold=1, quiet_threshold=16),
    Policy("measured_q32_high1_max3600", initial_index=6, min_index=0, max_index=11, high_threshold=1, quiet_threshold=32),
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

    # Knuth is exact and fast enough for the small-lambda region where most
    # measured-policy decisions occur.
    if lambda_value < 30.0:
        threshold = math.exp(-lambda_value)
        product = 1.0
        k = 0

        while product > threshold:
            k += 1
            product *= rng.random()

        return k - 1

    # For rare high-lambda storm intervals, a normal approximation is sufficient
    # for policy reaction. Risk is still evaluated by q_acc_exact, not by this
    # approximation.
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
    rng_seed: int,
) -> dict[str, str]:
    rng = random.Random(rng_seed)
    q_cache: dict[float, float] = {}

    idx = clamp(policy.initial_index, policy.min_index, policy.max_index)
    quiet_count = 0

    hour_index = 0
    offset_seconds = 0.0

    risk_e = 0.0
    pass_count = 0
    total_scrub_seconds = 0.0
    total_observed_corrections = 0
    high_activity_events = 0
    relax_events = 0
    min_seen_index = idx
    max_seen_index = idx
    tau_sum = 0.0
    tau_min = float("inf")
    tau_max = 0.0

    period_hist = {index: 0 for index in range(len(periods))}

    while hour_index < len(nu_values):
        tau_seconds = periods[idx]

        # Accumulate lambda over a pass interval, which may cross hour boundaries.
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
        total_scrub_seconds += tau_seconds
        total_observed_corrections += observed
        tau_sum += tau_seconds
        tau_min = min(tau_min, tau_seconds)
        tau_max = max(tau_max, tau_seconds)
        period_hist[idx] += 1
        min_seen_index = min(min_seen_index, idx)
        max_seen_index = max(max_seen_index, idx)

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

    dominant_index = max(period_hist.items(), key=lambda item: item[1])[0]
    target_met = risk_e <= target_e

    return {
        "policy": policy.name,
        "target_e": f"{target_e:.12g}",
        "risk_e": f"{risk_e:.12g}",
        "p_mission": f"{p_mission:.12g}",
        "risk_utilization": f"{risk_e / target_e:.12g}",
        "target_met": str(target_met).lower(),
        "pass_count": str(pass_count),
        "mean_tau_seconds": f"{tau_sum / pass_count:.12g}",
        "min_tau_seconds": f"{tau_min:.12g}",
        "max_tau_seconds": f"{tau_max:.12g}",
        "min_period_index": str(min_seen_index),
        "max_period_index": str(max_seen_index),
        "dominant_period_index": str(dominant_index),
        "dominant_tau_seconds": f"{periods[dominant_index]:.12g}",
        "observed_corrections": str(total_observed_corrections),
        "high_activity_events": str(high_activity_events),
        "relax_events": str(relax_events),
        "q_cache_entries": str(len(q_cache)),
        "seed": str(rng_seed),
    }


def write_outputs(rows: list[dict[str, str]], schedule_rows: dict[str, dict[str, str]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "policy",
        "target_e",
        "risk_e",
        "p_mission",
        "risk_utilization",
        "target_met",
        "pass_count",
        "fixed_over_policy_gain",
        "current_over_policy_pass_ratio",
        "mean_tau_seconds",
        "min_tau_seconds",
        "max_tau_seconds",
        "min_period_index",
        "max_period_index",
        "dominant_period_index",
        "dominant_tau_seconds",
        "observed_corrections",
        "high_activity_events",
        "relax_events",
        "q_cache_entries",
        "seed",
    ]

    fixed_passes = float(schedule_rows["fixed"]["pass_count"])
    current_passes = float(schedule_rows["current"]["pass_count"])

    enriched_rows: list[dict[str, str]] = []

    for row in rows:
        pass_count = float(row["pass_count"])
        enriched = dict(row)
        enriched["fixed_over_policy_gain"] = f"{fixed_passes / pass_count:.12g}"
        enriched["current_over_policy_pass_ratio"] = f"{current_passes / pass_count:.12g}"
        enriched_rows.append(enriched)

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)

    lines = [
        "# Measured-error policy model evaluation",
        "",
        "This report evaluates autonomous counter-based scrub-period policies on",
        "the five-year Chapter 3 total upset-rate series.",
        "",
        "The policy receives only sampled corrected-event counts per completed pass.",
        "Risk is evaluated separately with `q_acc_exact(lambda)` on the true series.",
        "",
        "## Baselines",
        "",
        "| Strategy | Pass count | P mission | Risk utilization |",
        "|---|---:|---:|---:|",
        f"| fixed | {schedule_rows['fixed']['pass_count']} | {schedule_rows['fixed']['p_mission']} | {schedule_rows['fixed']['risk_utilization']} |",
        f"| current adaptive | {schedule_rows['current']['pass_count']} | {schedule_rows['current']['p_mission']} | {schedule_rows['current']['risk_utilization']} |",
        f"| delayed 1h adaptive | {schedule_rows['delayed_1h']['pass_count']} | {schedule_rows['delayed_1h']['p_mission']} | {schedule_rows['delayed_1h']['risk_utilization']} |",
        "",
        "## Measured policies",
        "",
        "| Policy | Target met | P mission | Risk utilization | Pass count | Fixed/policy gain | Current/policy pass ratio | Tau range, s | High events | Relax events |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in enriched_rows:
        lines.append(
            f"| {row['policy']} | {row['target_met']} | {row['p_mission']} | "
            f"{row['risk_utilization']} | {row['pass_count']} | "
            f"{row['fixed_over_policy_gain']} | {row['current_over_policy_pass_ratio']} | "
            f"{row['min_tau_seconds']}..{row['max_tau_seconds']} | "
            f"{row['high_activity_events']} | {row['relax_events']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is a stochastic policy-level replay with a fixed seed.",
            "- Passing `target_met=true` means the resulting measured schedule satisfies the exact accumulated-risk target for this replay.",
            "- Failing policies are still useful as onboard fallback demonstrations, but not as certified replacements for the Chapter 3 schedule compiler.",
            "- The current/delayed external schedules remain the risk-certified path because they are compiled against the full nu(t) estimate.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "seed": SEED,
                "rows": enriched_rows,
                "baselines": schedule_rows,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print()
    print(OUT_CSV.read_text(encoding="utf-8"))


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

    rows = [
        simulate_policy(policy, nu_values, periods, geometry, target_e, SEED + index)
        for index, policy in enumerate(POLICIES)
    ]

    write_outputs(rows, schedule_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
