#!/usr/bin/env python3
"""Train/test transfer check for the adaptive C coefficient.

This script asks whether C calibrated on one part of the five-year series
remains safe on a disjoint part without reoptimization.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from model.risk_exact import MemoryGeometry, risk_from_mission_probability, mission_probability_from_risk
from model.schedule_compiler import (
    compile_schedule_for_c,
    find_largest_c_under_exact_risk,
    normalize_period_set,
    stats_for_tau_seconds,
)


CONFIG_PATH = REPO_ROOT / "configs" / "ch3_c_transfer_check.json"
OUT_CSV = REPO_ROOT / "results" / "schedules" / "ch3_c_transfer_check_summary.csv"
OUT_MD = REPO_ROOT / "results" / "schedules" / "ch3_c_transfer_check_certificate.md"
OUT_JSON = REPO_ROOT / "results" / "schedules" / "ch3_c_transfer_check_certificate.json"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_series(path: Path) -> tuple[list[str], list[float], list[float]]:
    timestamps: list[str] = []
    nu_values: list[float] = []
    dt_hours: list[float] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            timestamps.append(row["timestamp_utc"])
            nu_values.append(float(row["upsets_total_nu"]))
            dt_hours.append(1.0)

    if not timestamps:
        raise RuntimeError("empty series")

    return timestamps, nu_values, dt_hours


def year_from_timestamp(timestamp: str) -> int:
    return int(timestamp[:4])


def slice_window(
    *,
    timestamps: list[str],
    nu_values: list[float],
    dt_hours: list[float],
    start_year: int,
    end_year: int,
) -> tuple[list[str], list[float], list[float]]:
    rows = [
        (ts, nu, dt)
        for ts, nu, dt in zip(timestamps, nu_values, dt_hours, strict=True)
        if start_year <= year_from_timestamp(ts) <= end_year
    ]

    if not rows:
        raise RuntimeError(f"empty window {start_year}..{end_year}")

    ts_out, nu_out, dt_out = zip(*rows, strict=True)
    return list(ts_out), list(nu_out), list(dt_out)


def delayed_estimate(values: list[float], delay_steps: int = 1) -> list[float]:
    return [values[max(0, index - delay_steps)] for index in range(len(values))]


def forecast_growth_estimate(
    values: list[float],
    *,
    q_threshold: float = 1.35,
    beta: float = 0.7,
    rmax: float = 2.5,
) -> list[float]:
    if not values:
        return []

    eps = 1e-30
    estimate: list[float] = []

    for index in range(len(values)):
        delayed_index = max(0, index - 1)
        delayed_value = max(values[delayed_index], eps)

        if index < 2:
            multiplier = 1.0
        else:
            previous_value = max(values[index - 2], eps)
            growth_ratio = delayed_value / previous_value
            multiplier = min(rmax, growth_ratio ** beta) if growth_ratio > q_threshold else 1.0

        estimate.append(delayed_value * multiplier)

    return estimate


def estimate_for_strategy(strategy: str, nu_values: list[float]) -> list[float]:
    if strategy == "current":
        return list(nu_values)
    if strategy == "delayed_1h":
        return delayed_estimate(nu_values, 1)
    if strategy == "forecast":
        return forecast_growth_estimate(nu_values)
    raise ValueError(f"unknown strategy: {strategy}")


def fixed_5s_pass_count(dt_hours: list[float]) -> float:
    return sum(dt / (5.0 / 3600.0) for dt in dt_hours)


def row_for_transfer(
    *,
    direction_key: str,
    strategy: str,
    train_key: str,
    test_key: str,
    train_nu: list[float],
    train_dt: list[float],
    test_nu: list[float],
    test_dt: list[float],
    target_e_full: float,
    total_hours: float,
    periods: tuple[float, ...],
    geometry: MemoryGeometry,
) -> dict[str, str]:
    train_hours = sum(train_dt)
    test_hours = sum(test_dt)

    train_limit = target_e_full * train_hours / total_hours
    test_limit = target_e_full * test_hours / total_hours

    train_est = estimate_for_strategy(strategy, train_nu)
    test_est = estimate_for_strategy(strategy, test_nu)

    train_result = find_largest_c_under_exact_risk(
        nu_values=train_nu,
        estimate_values=train_est,
        dt_hours=train_dt,
        target_e=train_limit,
        period_set_seconds=periods,
        geometry=geometry,
        strategy=f"{strategy}_trained_on_{train_key}",
    )

    test_applied = compile_schedule_for_c(
        nu_values=test_nu,
        estimate_values=test_est,
        dt_hours=test_dt,
        c_value=float(train_result.c_value),
        target_e=test_limit,
        period_set_seconds=periods,
        geometry=geometry,
        strategy=f"{strategy}_train_{train_key}_apply_{test_key}",
    )

    test_required = find_largest_c_under_exact_risk(
        nu_values=test_nu,
        estimate_values=test_est,
        dt_hours=test_dt,
        target_e=test_limit,
        period_set_seconds=periods,
        geometry=geometry,
        strategy=f"{strategy}_required_on_{test_key}",
    )

    p_test = mission_probability_from_risk(test_applied.stats.risk_e)
    verdict = "pass" if test_applied.stats.risk_e <= test_limit else "fail"

    c_train = float(train_result.c_value)
    c_required = float(test_required.c_value)

    if c_required > 0:
        c_train_over_required = c_train / c_required
        c_required_over_train = c_required / c_train if c_train > 0 else math.inf
    else:
        c_train_over_required = math.inf
        c_required_over_train = 0.0

    return {
        "direction": direction_key,
        "strategy": strategy,
        "train_window": train_key,
        "test_window": test_key,
        "train_hours": f"{train_hours:.12g}",
        "test_hours": f"{test_hours:.12g}",
        "target_e_full": f"{target_e_full:.12g}",
        "train_limit_e": f"{train_limit:.12g}",
        "test_limit_e": f"{test_limit:.12g}",
        "c_train": f"{c_train:.12g}",
        "c_required_on_test": f"{c_required:.12g}",
        "c_train_over_c_required_on_test": f"{c_train_over_required:.12g}",
        "c_required_on_test_over_c_train": f"{c_required_over_train:.12g}",
        "train_risk_e": f"{train_result.stats.risk_e:.12g}",
        "train_risk_utilization": f"{train_result.stats.risk_e / train_limit:.12g}",
        "test_risk_e": f"{test_applied.stats.risk_e:.12g}",
        "test_risk_utilization": f"{test_applied.stats.risk_e / test_limit:.12g}",
        "test_p_mission": f"{p_test:.12g}",
        "test_pass_count": f"{test_applied.stats.pass_count:.12g}",
        "test_gain_vs_fixed_5s": f"{fixed_5s_pass_count(test_dt) / test_applied.stats.pass_count:.12g}",
        "test_min_tau_seconds": f"{test_applied.stats.min_tau_seconds:.12g}",
        "test_max_tau_seconds": f"{test_applied.stats.max_tau_seconds:.12g}",
        "verdict": verdict,
    }


def write_csv(rows: list[dict[str, str]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_md(cfg: dict, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Chapter 3 C-transfer train/test certificate",
        "",
        "## Purpose",
        "",
        "This certificate checks whether the adaptive-schedule coefficient `C`,",
        "calibrated on one disjoint part of the five-year series, remains safe on",
        "another part without reoptimization.",
        "",
        "The check is not a proof of a future mission. It is a transferability",
        "test on held-out portions of the reconstructed Chapter 3 series.",
        "",
        "## Rules",
        "",
        f"- Budget rule: {cfg['budget_rule']}",
        f"- Edge rule: {cfg['edge_rule']}",
        "",
        "## Results",
        "",
        "| Direction | Strategy | Train | Test | Test risk util. | Test passes | Gain vs 5 s | C_train/C_required_test | Verdict |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            f"| {row['direction']} | {row['strategy']} | {row['train_window']} | {row['test_window']} | "
            f"{row['test_risk_utilization']} | {row['test_pass_count']} | "
            f"{row['test_gain_vs_fixed_5s']} | {row['c_train_over_c_required_on_test']} | {row['verdict']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The transfer check shows that the early 2021--2023 window is more",
            "  restrictive for adaptive-C calibration under the proportional-budget",
            "  criterion, although the later 2024--2025 window contains the largest",
            "  individual event peaks.",
            "- This is consistent with the fact that the early window has a higher mean",
            "  upset rate, while the late window has much higher variability. The late",
            "  window is difficult for fixed-period operation, but its high variability",
            "  is precisely where adaptive scheduling gains leverage.",
            "- A value `C_train/C_required_test < 1` means that the train-calibrated",
            "  coefficient is more conservative than required on the test window.",
            "- A value `C_train/C_required_test > 1` means that the train-calibrated",
            "  coefficient is too permissive on the test window and must be reduced by",
            "  that factor or replaced by a qualification-scenario calibration.",
            "- Therefore `C` must be selected over a qualification envelope of",
            "  representative scenarios using the most restrictive exact-risk-calibrated",
            "  value, rather than by visual inspection of the largest event peak.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_json(cfg: dict, rows: list[dict[str, str]]) -> None:
    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "generated_by": "run_ch3_c_transfer_check.py",
                "config": cfg,
                "rows": rows,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )


def main() -> int:
    cfg = read_json(CONFIG_PATH)
    base_cfg = read_json(REPO_ROOT / cfg["base_config"])

    timestamps, nu_values, dt_hours = read_series(REPO_ROOT / cfg["series_path"])

    target_p = float(cfg["target_mission_probability"])
    target_e_full = risk_from_mission_probability(target_p)
    total_hours = sum(dt_hours)

    geometry_cfg = base_cfg["geometry"]
    geometry = MemoryGeometry(
        word_bits=int(geometry_cfg["word_bits"]),
        codeword_count=int(geometry_cfg["codeword_count"]),
    )

    periods = normalize_period_set(float(value) for value in base_cfg["period_set_seconds"])

    windows: dict[str, tuple[list[str], list[float], list[float]]] = {}
    for key, spec in cfg["windows"].items():
        windows[key] = slice_window(
            timestamps=timestamps,
            nu_values=nu_values,
            dt_hours=dt_hours,
            start_year=int(spec["start_year"]),
            end_year=int(spec["end_year"]),
        )

    rows: list[dict[str, str]] = []

    for direction in cfg["directions"]:
        direction_key = direction["key"]
        train_key = direction["train"]
        test_key = direction["test"]

        _, train_nu, train_dt = windows[train_key]
        _, test_nu, test_dt = windows[test_key]

        for strategy in cfg["strategies"]:
            print(f"Running {direction_key} / {strategy}...")
            rows.append(
                row_for_transfer(
                    direction_key=direction_key,
                    strategy=strategy,
                    train_key=train_key,
                    test_key=test_key,
                    train_nu=train_nu,
                    train_dt=train_dt,
                    test_nu=test_nu,
                    test_dt=test_dt,
                    target_e_full=target_e_full,
                    total_hours=total_hours,
                    periods=periods,
                    geometry=geometry,
                )
            )

    write_csv(rows)
    write_md(cfg, rows)
    write_json(cfg, rows)

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print()
    print(OUT_MD.read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
