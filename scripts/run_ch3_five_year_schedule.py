#!/usr/bin/env python3
"""Compile Chapter 3 five-year scrub schedules from the reconstructed nu(t) series."""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from model.risk_exact import MemoryGeometry, risk_from_mission_probability
from model.schedule_compiler import (
    ScheduleResult,
    compile_adaptive_current_schedule,
    compile_fixed_allowed_schedule,
    find_largest_c_under_exact_risk,
    normalize_period_set,
    stats_for_tau_seconds,
)


CONFIG_PATH = REPO_ROOT / "configs" / "ch3_main_1pct.json"
SERIES_PATH = REPO_ROOT / "data" / "ch3_five_year_upsets.csv"
OUT_DIR = REPO_ROOT / "results" / "schedules"

SUMMARY_CSV = OUT_DIR / "ch3_five_year_summary.csv"
SUMMARY_MD = OUT_DIR / "ch3_five_year_summary.md"
HISTOGRAM_CSV = OUT_DIR / "ch3_five_year_period_histogram.csv"
FIXED_SWEEP_CSV = OUT_DIR / "ch3_five_year_fixed_candidate_sweep.csv"

SCHEDULE_PATHS = {
    "fixed": OUT_DIR / "ch3_five_year_schedule_fixed.csv",
    "current": OUT_DIR / "ch3_five_year_schedule_current.csv",
    "delayed_1h": OUT_DIR / "ch3_five_year_schedule_delayed_1h.csv",
}


def read_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_series() -> tuple[list[str], list[float], list[float]]:
    timestamps: list[str] = []
    nu_values: list[float] = []
    dt_hours: list[float] = []

    with SERIES_PATH.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            timestamps.append(row["timestamp_utc"])
            nu_values.append(float(row["upsets_total_nu"]))
            dt_hours.append(1.0)

    if not timestamps:
        raise RuntimeError("empty five-year series")

    return timestamps, nu_values, dt_hours


def delayed_estimate(values: list[float], delay_steps: int = 1) -> list[float]:
    if delay_steps < 0:
        raise ValueError("delay_steps must be non-negative")

    if not values:
        return []

    estimate: list[float] = []

    for index in range(len(values)):
        source_index = max(0, index - delay_steps)
        estimate.append(values[source_index])

    return estimate


def eta_shape(nu_values: list[float], estimate_values: list[float], dt_hours: list[float]) -> float:
    """Continuous-law shape penalty for using estimate_values instead of nu_values.

    eta = (∫ nu_hat dt)(∫ nu^2 / nu_hat dt) / (∫ nu dt)^2

    For nu_hat = nu, eta = 1.
    For a constant estimate, eta = 1 + CV^2.
    """

    eps = 1e-30
    numerator_left = sum(max(hat, eps) * dt for hat, dt in zip(estimate_values, dt_hours, strict=True))
    numerator_right = sum(
        (nu * nu / max(hat, eps)) * dt
        for nu, hat, dt in zip(nu_values, estimate_values, dt_hours, strict=True)
    )
    denominator = sum(nu * dt for nu, dt in zip(nu_values, dt_hours, strict=True)) ** 2

    return numerator_left * numerator_right / denominator


def cv2(values: list[float]) -> float:
    mu = mean(values)
    return sum((value - mu) ** 2 for value in values) / len(values) / (mu * mu)


def write_schedule(
    path: Path,
    result: ScheduleResult,
    timestamps: list[str],
    nu_values: list[float],
    estimate_values: list[float],
    dt_hours: list[float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "time_index",
        "timestamp_utc",
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

        for index, (timestamp, nu, estimate, dt, tau, period_index) in enumerate(
            zip(
                timestamps,
                nu_values,
                estimate_values,
                dt_hours,
                result.tau_seconds,
                result.period_indices,
                strict=True,
            )
        ):
            writer.writerow(
                {
                    "time_index": index,
                    "timestamp_utc": timestamp,
                    "nu": f"{nu:.12g}",
                    "nu_hat": f"{estimate:.12g}",
                    "dt_hours": f"{dt:.12g}",
                    "tau_seconds": f"{tau:.12g}",
                    "period_index": period_index,
                    "passes": f"{dt / (tau / 3600.0):.12g}",
                }
            )


def summary_row(
    strategy_key: str,
    result: ScheduleResult,
    target_e: float,
    target_p: float,
    fixed_pass_count: float,
    eta_value: float | None,
) -> dict[str, str]:
    stats = result.stats
    return {
        "strategy_key": strategy_key,
        "strategy": result.strategy,
        "target_p": f"{target_p:.12g}",
        "target_e": f"{target_e:.12g}",
        "risk_e": f"{stats.risk_e:.12g}",
        "p_mission": f"{stats.p_mission:.12g}",
        "risk_utilization": f"{stats.risk_e / target_e:.12g}",
        "pass_count": f"{stats.pass_count:.12g}",
        "gain_fixed_over_strategy": f"{fixed_pass_count / stats.pass_count:.12g}",
        "mean_tau_seconds": f"{stats.mean_tau_seconds:.12g}",
        "min_tau_seconds": f"{stats.min_tau_seconds:.12g}",
        "max_tau_seconds": f"{stats.max_tau_seconds:.12g}",
        "saturated_at_tau_min": str(stats.saturated_at_tau_min).lower(),
        "saturated_at_tau_max": str(stats.saturated_at_tau_max).lower(),
        "c_value": "" if result.c_value is None else f"{result.c_value:.12g}",
        "eta_shape": "" if eta_value is None else f"{eta_value:.12g}",
    }


def write_summary(rows: list[dict[str, str]], series_metrics: dict[str, float]) -> None:
    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "strategy_key",
        "strategy",
        "target_p",
        "target_e",
        "risk_e",
        "p_mission",
        "risk_utilization",
        "pass_count",
        "gain_fixed_over_strategy",
        "mean_tau_seconds",
        "min_tau_seconds",
        "max_tau_seconds",
        "saturated_at_tau_min",
        "saturated_at_tau_max",
        "c_value",
        "eta_shape",
    ]

    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Chapter 3 five-year schedule summary",
        "",
        "This report is generated from `data/ch3_five_year_upsets.csv` and the",
        "main Chapter 3 configuration.",
        "",
        "## Series metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| hours | {int(series_metrics['hours'])} |",
        f"| mean_nu_per_hour | {series_metrics['mean_nu']:.12g} |",
        f"| cv2 | {series_metrics['cv2']:.12g} |",
        f"| eta_const = 1 + CV^2 | {series_metrics['eta_const']:.12g} |",
        f"| max_nu_per_hour | {series_metrics['max_nu']:.12g} |",
        "",
        "## Strategies",
        "",
        "| Strategy | E risk | P mission | Pass count | Fixed/strategy gain | Tau range, s | Eta shape |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        eta = row["eta_shape"] if row["eta_shape"] else "-"
        lines.append(
            f"| {row['strategy_key']} | {row['risk_e']} | {row['p_mission']} | "
            f"{row['pass_count']} | {row['gain_fixed_over_strategy']} | "
            f"{row['min_tau_seconds']}..{row['max_tau_seconds']} | {eta} |"
        )

    lines.append("")
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def write_histogram(results: dict[str, ScheduleResult], periods: tuple[float, ...]) -> None:
    fieldnames = ["strategy_key", "period_index", "tau_seconds", "hours", "fraction"]

    with HISTOGRAM_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for strategy_key, result in results.items():
            counts = Counter(result.period_indices)
            total = len(result.period_indices)

            for index, period in enumerate(periods):
                count = counts.get(index, 0)
                writer.writerow(
                    {
                        "strategy_key": strategy_key,
                        "period_index": index,
                        "tau_seconds": f"{period:g}",
                        "hours": count,
                        "fraction": f"{count / total:.12g}",
                    }
                )

def write_fixed_candidate_sweep(
    periods: tuple[float, ...],
    nu_values: list[float],
    dt_hours: list[float],
    geometry: MemoryGeometry,
    target_e: float,
    target_p: float,
) -> None:
    fieldnames = [
        "period_index",
        "tau_seconds",
        "target_p",
        "target_e",
        "risk_e",
        "p_mission",
        "risk_utilization",
        "pass_count",
        "allowed",
    ]

    with FIXED_SWEEP_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for index, period in enumerate(periods):
            tau_seconds = [period for _ in nu_values]
            stats = stats_for_tau_seconds(
                nu_values=nu_values,
                tau_seconds=tau_seconds,
                dt_hours=dt_hours,
                geometry=geometry,
                period_set_seconds=periods,
            )

            writer.writerow(
                {
                    "period_index": index,
                    "tau_seconds": f"{period:g}",
                    "target_p": f"{target_p:.12g}",
                    "target_e": f"{target_e:.12g}",
                    "risk_e": f"{stats.risk_e:.12g}",
                    "p_mission": f"{stats.p_mission:.12g}",
                    "risk_utilization": f"{stats.risk_e / target_e:.12g}",
                    "pass_count": f"{stats.pass_count:.12g}",
                    "allowed": str(stats.risk_e <= target_e).lower(),
                }
            )


def main() -> int:
    config = read_config()
    timestamps, nu_values, dt_hours = read_series()

    target_p = float(config["target_mission_probability"])
    target_e = risk_from_mission_probability(target_p)

    geometry_config = config["geometry"]
    geometry = MemoryGeometry(
        word_bits=int(geometry_config["word_bits"]),
        codeword_count=int(geometry_config["codeword_count"]),
    )

    periods = normalize_period_set(float(value) for value in config["period_set_seconds"])

    delayed_values = delayed_estimate(nu_values, delay_steps=1)

    print("Compiling fixed schedule...")
    fixed = compile_fixed_allowed_schedule(
        nu_values=nu_values,
        dt_hours=dt_hours,
        target_e=target_e,
        period_set_seconds=periods,
        geometry=geometry,
    )

    print("Compiling current adaptive schedule...")
    current = compile_adaptive_current_schedule(
        nu_values=nu_values,
        dt_hours=dt_hours,
        target_e=target_e,
        period_set_seconds=periods,
        geometry=geometry,
    )

    print("Compiling delayed 1h adaptive schedule...")
    delayed = find_largest_c_under_exact_risk(
        nu_values=nu_values,
        estimate_values=delayed_values,
        dt_hours=dt_hours,
        target_e=target_e,
        period_set_seconds=periods,
        geometry=geometry,
        strategy="adaptive_delayed_1h_exact_floor_down",
    )

    results = {
        "fixed": fixed,
        "current": current,
        "delayed_1h": delayed,
    }

    estimates = {
        "fixed": [mean(nu_values) for _ in nu_values],
        "current": list(nu_values),
        "delayed_1h": delayed_values,
    }

    write_schedule(SCHEDULE_PATHS["fixed"], fixed, timestamps, nu_values, estimates["fixed"], dt_hours)
    write_schedule(SCHEDULE_PATHS["current"], current, timestamps, nu_values, estimates["current"], dt_hours)
    write_schedule(SCHEDULE_PATHS["delayed_1h"], delayed, timestamps, nu_values, estimates["delayed_1h"], dt_hours)

    fixed_pass_count = fixed.stats.pass_count

    eta_values = {
        "fixed": eta_shape(nu_values, estimates["fixed"], dt_hours),
        "current": eta_shape(nu_values, estimates["current"], dt_hours),
        "delayed_1h": eta_shape(nu_values, estimates["delayed_1h"], dt_hours),
    }

    summary_rows = [
        summary_row(key, result, target_e, target_p, fixed_pass_count, eta_values[key])
        for key, result in results.items()
    ]

    series_metrics = {
        "hours": float(len(nu_values)),
        "mean_nu": mean(nu_values),
        "cv2": cv2(nu_values),
        "eta_const": 1.0 + cv2(nu_values),
        "max_nu": max(nu_values),
    }

    write_summary(summary_rows, series_metrics)
    write_histogram(results, periods)
    write_fixed_candidate_sweep(periods, nu_values, dt_hours, geometry, target_e, target_p)

    print("Wrote", SUMMARY_CSV)
    print("Wrote", SUMMARY_MD)
    print("Wrote", HISTOGRAM_CSV)
    print("Wrote", FIXED_SWEEP_CSV)

    print()
    print("=== five-year schedule summary ===")
    print(SUMMARY_CSV.read_text(encoding="utf-8"))

    print()
    print("=== fixed candidate sweep ===")
    print(FIXED_SWEEP_CSV.read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
