#!/usr/bin/env python3
"""Finite-correlation rate-burst stress test for measured-error scrub policy.

This is the primary burst-stress model for the autonomous measured-error
scrubber. Unlike pass-level constant-VMR NB overdispersion, this model perturbs
the sub-hourly rate path while preserving each hourly mean from the Chapter 3
series.

Within each hour:
    lambda(t) = nu_hour * g(t),
where g(t) is piecewise-constant over burst_duration_seconds and normalized
inside the hour so that mean(g)=1 exactly.

For the measured policy:
    - realized K_i is sampled from Poisson(integral lambda(t) over pass i);
    - the policy observes K_i;
    - pathwise risk adds -log(1 - p_acc_given_k(K_i)).

For the always-tau_min baseline:
    - risk is evaluated in expectation over the conditional Poisson counts
      on 1-second passes using a stable closed-form Bernoulli/Poissonized
      approximation for q_acc(lambda).
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

from model.risk_exact import MemoryGeometry, p_acc_given_k  # noqa: E402


CONFIG_PATH = REPO_ROOT / "configs" / "ch4_rate_burst_stress.json"

_CURRENT_ACHIEVED_RATE_CV2_MEAN = 0.0
_CURRENT_ACHIEVED_RATE_CV2_MAX = 0.0


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


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


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
        return max(0, k - 1)

    # Pilot implementation: normal approximation with truncation.
    # This branch must never return a negative count.
    sample = int(round(rng.gauss(lambda_value, math.sqrt(lambda_value))))
    return max(0, sample)

def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def make_scenarios(cfg: dict) -> list[dict[str, float]]:
    explicit = cfg["rate_burst_model"].get("explicit_scenarios")

    if explicit:
        scenarios: list[dict[str, float]] = []
        seen_poisson = False

        for item in explicit:
            cv2 = float(item["rate_cv2"])
            duration = int(item.get("burst_duration_seconds", 0))

            if cv2 == 0.0:
                if seen_poisson:
                    continue
                seen_poisson = True
                duration = 0
                name = item.get("scenario", "poisson_sanity")
            else:
                if duration <= 0:
                    raise ValueError(f"nonzero rate_cv2 requires positive burst duration: {item}")
                if 3600 % duration != 0:
                    raise ValueError(f"burst_duration_seconds must divide 3600: {duration}")
                name = item.get("scenario", f"burst_{duration}s_cv2_{cv2:g}")

            scenarios.append(
                {
                    "scenario": name,
                    "burst_duration_seconds": duration,
                    "rate_cv2": cv2,
                }
            )

        return scenarios

    durations = [int(x) for x in cfg["rate_burst_model"]["burst_duration_seconds"]]
    cv2_values = [float(x) for x in cfg["rate_burst_model"]["rate_cv2"]]

    scenarios: list[dict[str, float]] = []

    # One Poisson sanity case. burst_duration is semantically irrelevant here.
    if 0.0 in cv2_values:
        scenarios.append(
            {
                "scenario": "poisson_sanity",
                "burst_duration_seconds": 0,
                "rate_cv2": 0.0,
            }
        )

    for duration in durations:
        if 3600 % duration != 0:
            raise ValueError(f"burst_duration_seconds must divide 3600: {duration}")

        for cv2 in cv2_values:
            if cv2 == 0.0:
                continue

            scenarios.append(
                {
                    "scenario": f"burst_{duration}s_cv2_{cv2:g}",
                    "burst_duration_seconds": duration,
                    "rate_cv2": cv2,
                }
            )

    return scenarios

def make_rate_multipliers(
    hour_count: int,
    burst_duration_seconds: int,
    rate_cv2: float,
    rng: random.Random,
) -> tuple[list[list[float]] | None, int]:
    """Return per-hour multipliers and bins_per_hour.

    For cv2=0, returns None and bins_per_hour=1. The integrator treats this
    as g(t)=1 everywhere.
    """
    if rate_cv2 <= 0.0 or burst_duration_seconds == 0:
        return None, 1

    bins_per_hour = 3600 // burst_duration_seconds

    if bins_per_hour <= 1:
        # Hourly normalization makes a one-bin hour multiplier exactly 1.
        return None, 1

    shape = 1.0 / rate_cv2
    scale = rate_cv2

    multipliers: list[list[float]] = []

    for _ in range(hour_count):
        values = [rng.gammavariate(shape, scale) for _ in range(bins_per_hour)]
        total = sum(values)

        if total <= 0.0:
            # Practically impossible, but keep a deterministic fallback.
            multipliers.append([1.0] * bins_per_hour)
            continue

        factor = bins_per_hour / total
        multipliers.append([value * factor for value in values])

    return multipliers, bins_per_hour


def achieved_cv2_stats(multipliers: list[list[float]] | None) -> tuple[float, float]:
    if multipliers is None:
        return 0.0, 0.0

    values: list[float] = []
    for hour_values in multipliers:
        if not hour_values:
            continue
        # Hourly normalization makes the bin mean exactly 1.
        cv2 = sum((value - 1.0) * (value - 1.0) for value in hour_values) / len(hour_values)
        values.append(cv2)

    if not values:
        return 0.0, 0.0

    return mean(values), max(values)


def multiplier_at(
    multipliers: list[list[float]] | None,
    bins_per_hour: int,
    burst_duration_seconds: int,
    hour_index: int,
    offset_seconds: float,
) -> float:
    if multipliers is None:
        return 1.0

    bin_index = int(offset_seconds // burst_duration_seconds)
    if bin_index >= bins_per_hour:
        bin_index = bins_per_hour - 1

    return multipliers[hour_index][bin_index]


def seconds_to_next_rate_boundary(
    multipliers: list[list[float]] | None,
    burst_duration_seconds: int,
    offset_seconds: float,
) -> float:
    if multipliers is None:
        return 3600.0 - offset_seconds

    next_boundary = (math.floor(offset_seconds / burst_duration_seconds) + 1) * burst_duration_seconds
    return min(next_boundary, 3600.0) - offset_seconds


def integrate_lambda_interval(
    nu_values: list[float],
    start_hour_index: int,
    start_offset_seconds: float,
    duration_seconds: float,
    multipliers: list[list[float]] | None,
    bins_per_hour: int,
    burst_duration_seconds: int,
) -> tuple[float, int, float]:
    hour_index = start_hour_index
    offset_seconds = start_offset_seconds
    remaining = duration_seconds
    lambda_interval = 0.0

    while remaining > 1e-12 and hour_index < len(nu_values):
        to_hour_end = 3600.0 - offset_seconds
        to_rate_boundary = seconds_to_next_rate_boundary(multipliers, burst_duration_seconds, offset_seconds)
        chunk = min(remaining, to_hour_end, to_rate_boundary)

        g = multiplier_at(multipliers, bins_per_hour, burst_duration_seconds, hour_index, offset_seconds)
        lambda_interval += nu_values[hour_index] * g * (chunk / 3600.0)

        remaining -= chunk
        offset_seconds += chunk

        if offset_seconds >= 3600.0 - 1e-12:
            hour_index += 1
            offset_seconds = 0.0

    return lambda_interval, hour_index, offset_seconds


def q_acc_closed_bernoulli(lambda_value: float, geometry: MemoryGeometry) -> float:
    """O(1) Bernoulli/Poissonized accumulated-risk approximation.

    This is used only for the aggregated always-tau_min expected baseline. The
    policy pathwise risk uses exact p_acc_given_k(K).
    """
    if lambda_value <= 0.0:
        return 0.0

    n = geometry.word_bits
    w = geometry.codeword_count
    nbits = geometry.physical_bits
    p = lambda_value / nbits

    if p <= 0.0:
        return 0.0

    if p >= 1.0:
        return 1.0

    log1m = math.log1p(-p)
    log_zero = n * log1m
    log_one = math.log(n * p) + (n - 1) * log1m

    # safe probability for one word = P(0 or 1 hit in the word)
    # These logs are close, and values are well-scaled.
    safe_word = math.exp(log_zero) + math.exp(log_one)

    if safe_word <= 0.0:
        return 1.0
    if safe_word >= 1.0:
        return 0.0

    log_safe_all = w * math.log(safe_word)
    return -math.expm1(log_safe_all)


def p_acc_cached(k: int, geometry: MemoryGeometry, cache: dict[int, float]) -> float:
    if k not in cache:
        cache[k] = p_acc_given_k(k, geometry)
    return cache[k]


def simulate_measured_policy(
    policy: Policy,
    periods: list[float],
    nu_values: list[float],
    geometry: MemoryGeometry,
    target_e: float,
    fixed_passes: float,
    seed: int,
    scenario: dict[str, float],
    multipliers: list[list[float]] | None,
    bins_per_hour: int,
) -> dict[str, str]:
    rng = random.Random(seed + 101)

    burst_duration = int(scenario["burst_duration_seconds"])
    if multipliers is None:
        burst_duration = 3600

    p_cache: dict[int, float] = {}

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
    max_k = 0

    while hour_index < len(nu_values):
        tau_seconds = periods[idx]

        lambda_interval, hour_index, offset_seconds = integrate_lambda_interval(
            nu_values=nu_values,
            start_hour_index=hour_index,
            start_offset_seconds=offset_seconds,
            duration_seconds=tau_seconds,
            multipliers=multipliers,
            bins_per_hour=bins_per_hour,
            burst_duration_seconds=burst_duration,
        )

        if lambda_interval <= 0.0 and hour_index >= len(nu_values):
            break

        observed = poisson_sample(lambda_interval, rng)
        if observed < 0:
            raise RuntimeError(
                f"negative observed count: observed={observed}, "
                f"lambda_interval={lambda_interval}, policy={policy.name}, "
                f"scenario={scenario['scenario']}, seed={seed}"
            )

        max_k = max(max_k, observed)

        p_acc = p_acc_cached(observed, geometry, p_cache)
        if p_acc >= 1.0:
            risk_e = float("inf")
        elif risk_e != float("inf"):
            risk_e += -math.log1p(-p_acc)

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

    p_mission = 1.0 if risk_e == float("inf") else 1.0 - math.exp(-risk_e)

    return {
        "kind": "policy",
        "policy": policy.name,
        "scenario": str(scenario["scenario"]),
        "burst_duration_seconds": str(int(scenario["burst_duration_seconds"])),
        "rate_cv2": f"{float(scenario['rate_cv2']):.12g}",
        "achieved_rate_cv2_mean": f"{_CURRENT_ACHIEVED_RATE_CV2_MEAN:.12g}",
        "achieved_rate_cv2_max": f"{_CURRENT_ACHIEVED_RATE_CV2_MAX:.12g}",
        "seed": str(seed),
        "risk_e": f"{risk_e:.12g}",
        "p_mission": f"{p_mission:.12g}",
        "risk_utilization": f"{risk_e / target_e:.12g}",
        "target_met": str(risk_e <= target_e).lower(),
        "pass_count": str(pass_count),
        "fixed_over_policy_gain": f"{fixed_passes / pass_count:.12g}",
        "mean_tau_seconds": f"{tau_sum / pass_count:.12g}",
        "min_tau_seconds": f"{tau_min:.12g}",
        "max_tau_seconds": f"{tau_max:.12g}",
        "observed_corrections": str(observed_corrections),
        "high_activity_events": str(high_activity_events),
        "relax_events": str(relax_events),
        "max_k_per_pass": str(max_k),
        "p_cache_entries": str(len(p_cache)),
    }


def evaluate_always_tau_min_baseline(
    periods: list[float],
    period_index: int,
    nu_values: list[float],
    geometry: MemoryGeometry,
    target_e: float,
    fixed_passes: float,
    seed: int,
    scenario: dict[str, float],
    multipliers: list[list[float]] | None,
    bins_per_hour: int,
) -> dict[str, str]:
    tau_seconds = periods[period_index]
    burst_duration = int(scenario["burst_duration_seconds"])
    if multipliers is None:
        burst_duration = 3600

    if abs(tau_seconds - 1.0) > 1e-12:
        raise ValueError("This aggregated baseline currently assumes tau_min=1 s.")

    risk_e = 0.0
    pass_count = 0

    for hour_index, nu in enumerate(nu_values):
        if multipliers is None:
            lambda_per_pass = nu / 3600.0
            q = q_acc_closed_bernoulli(lambda_per_pass, geometry)
            risk_e += 3600.0 * (-math.log1p(-q))
            pass_count += 3600
        else:
            for bin_index in range(bins_per_hour):
                g = multipliers[hour_index][bin_index]
                lambda_per_pass = nu * g / 3600.0
                q = q_acc_closed_bernoulli(lambda_per_pass, geometry)
                risk_e += burst_duration * (-math.log1p(-q))
                pass_count += burst_duration

    p_mission = 1.0 - math.exp(-risk_e)

    return {
        "kind": "baseline_expected",
        "policy": "always_tau_min_1s",
        "scenario": str(scenario["scenario"]),
        "burst_duration_seconds": str(int(scenario["burst_duration_seconds"])),
        "rate_cv2": f"{float(scenario['rate_cv2']):.12g}",
        "achieved_rate_cv2_mean": f"{_CURRENT_ACHIEVED_RATE_CV2_MEAN:.12g}",
        "achieved_rate_cv2_max": f"{_CURRENT_ACHIEVED_RATE_CV2_MAX:.12g}",
        "seed": str(seed),
        "risk_e": f"{risk_e:.12g}",
        "p_mission": f"{p_mission:.12g}",
        "risk_utilization": f"{risk_e / target_e:.12g}",
        "target_met": str(risk_e <= target_e).lower(),
        "pass_count": str(pass_count),
        "fixed_over_policy_gain": f"{fixed_passes / pass_count:.12g}",
        "mean_tau_seconds": f"{tau_seconds:.12g}",
        "min_tau_seconds": f"{tau_seconds:.12g}",
        "max_tau_seconds": f"{tau_seconds:.12g}",
        "observed_corrections": "",
        "high_activity_events": "",
        "relax_events": "",
        "max_k_per_pass": "",
        "p_cache_entries": "",
    }


def summarize_group(rows: list[dict[str, str]]) -> dict[str, str]:
    risk_utils = [float(row["risk_utilization"]) for row in rows]
    p_missions = [float(row["p_mission"]) for row in rows]
    pass_counts = [float(row["pass_count"]) for row in rows]

    achieved_means = [
        float(row.get("achieved_rate_cv2_mean", "0") or 0.0)
        for row in rows
    ]
    achieved_maxes = [
        float(row.get("achieved_rate_cv2_max", "0") or 0.0)
        for row in rows
    ]

    observed = [float(row["observed_corrections"]) for row in rows if row["observed_corrections"] != ""]
    high_events = [float(row["high_activity_events"]) for row in rows if row["high_activity_events"] != ""]
    relax_events = [float(row["relax_events"]) for row in rows if row["relax_events"] != ""]

    target_met_count = sum(1 for row in rows if row["target_met"] == "true")
    target_met_fraction = target_met_count / len(rows)

    p99 = percentile(risk_utils, 0.99)
    max_risk = max(risk_utils)

    return {
        "kind": rows[0]["kind"],
        "policy": rows[0]["policy"],
        "scenario": rows[0]["scenario"],
        "burst_duration_seconds": rows[0]["burst_duration_seconds"],
        "rate_cv2": rows[0]["rate_cv2"],
        "achieved_rate_cv2_mean": f"{mean(achieved_means):.12g}",
        "achieved_rate_cv2_p95": f"{percentile(achieved_means, 0.95):.12g}",
        "achieved_rate_cv2_max": f"{max(achieved_maxes):.12g}",
        "seed_count": str(len(rows)),
        "target_met_count": str(target_met_count),
        "target_met_fraction": f"{target_met_fraction:.12g}",
        "sampled_all_pass": str(max_risk <= 1.0).lower(),
        "sampled_p99_pass": str((target_met_fraction >= 0.99) and (p99 <= 1.0)).lower(),
        "risk_utilization_mean": f"{mean(risk_utils):.12g}",
        "risk_utilization_p95": f"{percentile(risk_utils, 0.95):.12g}",
        "risk_utilization_p99": f"{p99:.12g}",
        "risk_utilization_max": f"{max_risk:.12g}",
        "p_mission_mean": f"{mean(p_missions):.12g}",
        "p_mission_p95": f"{percentile(p_missions, 0.95):.12g}",
        "p_mission_p99": f"{percentile(p_missions, 0.99):.12g}",
        "pass_count_mean": f"{mean(pass_counts):.12g}",
        "pass_count_p95": f"{percentile(pass_counts, 0.95):.12g}",
        "pass_count_max": f"{max(pass_counts):.12g}",
        "fixed_over_policy_gain_mean": f"{mean(float(row['fixed_over_policy_gain']) for row in rows):.12g}",
        "observed_corrections_mean": "" if not observed else f"{mean(observed):.12g}",
        "observed_corrections_p99": "" if not observed else f"{percentile(observed, 0.99):.12g}",
        "high_activity_events_mean": "" if not high_events else f"{mean(high_events):.12g}",
        "relax_events_mean": "" if not relax_events else f"{mean(relax_events):.12g}",
    }


def write_outputs(cfg: dict, detail_rows: list[dict[str, str]], summary_rows: list[dict[str, str]], payload: dict) -> None:
    out_paths = cfg["out_paths"]

    detail_path = REPO_ROOT / out_paths["detail_csv"]
    summary_path = REPO_ROOT / out_paths["summary_csv"]
    report_path = REPO_ROOT / out_paths["report_md"]
    json_path = REPO_ROOT / out_paths["certificate_json"]

    detail_path.parent.mkdir(parents=True, exist_ok=True)

    detail_fields = list(detail_rows[0].keys())
    summary_fields = list(summary_rows[0].keys())

    with detail_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(detail_rows)

    with summary_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    lines = [
        "# Chapter 4 rate-burst stress certificate",
        "",
        "## Pre-registration",
        "",
    ]

    for item in cfg["pre_registered_prediction"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Model",
            "",
            f"- Type: `{cfg['rate_burst_model']['type']}`",
            f"- Count model: `{cfg['rate_burst_model']['count_model']}`",
            f"- Hourly mean preservation: {cfg['rate_burst_model']['hourly_mean_preservation']}",
            f"- Seed count: `{cfg['simulation']['seed_count']}`",
            "",
            "## Summary",
            "",
            "| Kind | Policy | Scenario | Burst duration, s | requested CV^2 | achieved CV^2 mean | achieved CV^2 max | Target met fraction | p99 util. | Max util. | Pass mean | Sampled p99 pass | All pass |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )

    for row in summary_rows:
        lines.append(
            f"| {row['kind']} | {row['policy']} | {row['scenario']} | "
            f"{row['burst_duration_seconds']} | {row['rate_cv2']} | "
            f"{row['achieved_rate_cv2_mean']} | {row['achieved_rate_cv2_max']} | "
            f"{row['target_met_fraction']} | {row['risk_utilization_p99']} | "
            f"{row['risk_utilization_max']} | {row['pass_count_mean']} | "
            f"{row['sampled_p99_pass']} | {row['sampled_all_pass']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation notes",
            "",
            "- The measured policy rows are pathwise Monte Carlo over the realized rate-burst and count process.",
            "- The always-tau_min rows are expected-risk baselines over the same sampled rate paths, not pass-by-pass count simulations.",
            "- `requested CV^2` is the gamma-generator dispersion before per-hour mean normalization.",
            "- `achieved CV^2 mean` and `achieved CV^2 max` summarize the normalized multiplier paths actually used in the simulation.",
            "- `rate_cv2=0` is the Poisson sanity case.",
            "- Failures at high requested/achieved CV^2 and short burst duration indicate the boundary of temporally resolvable accumulated-error control, not the instantaneous MBU/MCU mapping channel.",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {detail_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")
    print(f"Wrote {json_path}")


def main() -> None:
    cfg = read_json(CONFIG_PATH)
    base_cfg = read_json(REPO_ROOT / cfg["base_config"])

    geometry_cfg = base_cfg["geometry"]
    geometry = MemoryGeometry(
        word_bits=int(geometry_cfg["word_bits"]),
        codeword_count=int(geometry_cfg["codeword_count"]),
    )

    target_p = float(base_cfg["target_mission_probability"])
    target_e = -math.log1p(-target_p)

    periods = [float(x) for x in base_cfg["period_set_seconds"]]

    series_rows = read_csv_rows(REPO_ROOT / cfg["series_path"])
    nu_values = [float(row["upsets_total_nu"]) for row in series_rows]

    schedule_rows = {row["strategy_key"]: row for row in read_csv_rows(REPO_ROOT / cfg["schedule_summary_path"])}
    fixed_passes = float(schedule_rows["fixed"]["pass_count"])

    seed_count = int(cfg["simulation"]["seed_count"])
    master_seed = int(cfg["simulation"]["master_seed"])

    policies = [
        Policy(
            name=p["name"],
            initial_index=int(p["initial_index"]),
            min_index=int(p["min_index"]),
            max_index=int(p["max_index"]),
            high_threshold=int(p["high_threshold"]),
            quiet_threshold=int(p["quiet_threshold"]),
            speedup_step=int(p.get("speedup_step", 1)),
            relax_step=int(p.get("relax_step", 1)),
        )
        for p in cfg["policies"]
    ]

    scenarios = make_scenarios(cfg)

    detail_rows: list[dict[str, str]] = []

    for scenario_index, scenario in enumerate(scenarios):
        for seed_offset in range(seed_count):
            seed = master_seed + scenario_index * 100000 + seed_offset

            rng = random.Random(seed)
            multipliers, bins_per_hour = make_rate_multipliers(
                hour_count=len(nu_values),
                burst_duration_seconds=int(scenario["burst_duration_seconds"]),
                rate_cv2=float(scenario["rate_cv2"]),
                rng=rng,
            )
            achieved_cv2_mean, achieved_cv2_max = achieved_cv2_stats(multipliers)
            globals()['_CURRENT_ACHIEVED_RATE_CV2_MEAN'] = achieved_cv2_mean
            globals()['_CURRENT_ACHIEVED_RATE_CV2_MAX'] = achieved_cv2_max

            for policy in policies:
                detail_rows.append(
                    simulate_measured_policy(
                        policy=policy,
                        periods=periods,
                        nu_values=nu_values,
                        geometry=geometry,
                        target_e=target_e,
                        fixed_passes=fixed_passes,
                        seed=seed,
                        scenario=scenario,
                        multipliers=multipliers,
                        bins_per_hour=bins_per_hour,
                    )
                )

            for baseline in cfg["baselines"]:
                if baseline["name"] != "always_tau_min_1s":
                    raise ValueError(f"unsupported baseline: {baseline['name']}")

                detail_rows.append(
                    evaluate_always_tau_min_baseline(
                        periods=periods,
                        period_index=int(baseline["period_index"]),
                        nu_values=nu_values,
                        geometry=geometry,
                        target_e=target_e,
                        fixed_passes=fixed_passes,
                        seed=seed,
                        scenario=scenario,
                        multipliers=multipliers,
                        bins_per_hour=bins_per_hour,
                    )
                )

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in detail_rows:
        key = (row["kind"], row["policy"], row["scenario"])
        grouped.setdefault(key, []).append(row)

    summary_rows = [summarize_group(rows) for _, rows in sorted(grouped.items())]

    payload = {
        "generated_by": "run_measured_policy_rate_burst_stress.py",
        "config": cfg,
        "target": {
            "target_p": target_p,
            "target_e": target_e,
        },
        "geometry": {
            "word_bits": geometry.word_bits,
            "codeword_count": geometry.codeword_count,
            "physical_bits": geometry.physical_bits,
            "alpha": geometry.alpha,
        },
        "summary": summary_rows,
    }

    write_outputs(cfg, detail_rows, summary_rows, payload)


if __name__ == "__main__":
    main()
