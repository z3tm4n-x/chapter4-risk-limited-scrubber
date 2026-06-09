#!/usr/bin/env python3
"""Instantiate a Chapter-2 interleaving g(D) feasibility case.

This script turns rho_D from a free sweep parameter into a value computed from:
  - a geometric multiplicity distribution p_m = (1 - s) s^(m-1),
  - the Chapter-2 limiting dangerous-mapping model g_D = s^D,
  - the five-year Chapter-3 upset series,
  - and the residual accumulated-risk scheduler from Chapter 3.

The model is a Chapter-2-consistent design-case instantiation. It is not a
universal upper bound for arbitrary physical SRAM placement; a concrete memory
macro should refine h_m(D) from its topology or test data.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from model.risk_exact import MemoryGeometry, risk_from_mission_probability
from model.schedule_compiler import (
    compile_adaptive_current_schedule,
    normalize_period_set,
    stats_for_tau_seconds,
)


CONFIG_PATH = REPO_ROOT / "configs" / "ch3_main_1pct.json"
SERIES_PATH = REPO_ROOT / "data" / "ch3_five_year_upsets.csv"

OUT_DIR = REPO_ROOT / "results" / "feasibility"
FIG_DIR = REPO_ROOT / "results" / "figures"

OUT_CSV = OUT_DIR / "interleaving_gd_case_summary.csv"
OUT_MD = OUT_DIR / "interleaving_gd_case_report.md"
OUT_JSON = OUT_DIR / "interleaving_gd_case.json"
OUT_FIG = FIG_DIR / "interleaving_gd_case.png"

MEAN_MULTIPLICITIES = [1.5, 2.0, 3.0]
D_VALUES = [1, 2, 4, 8, 12, 16, 20, 24, 25, 28, 32, 36, 40, 41, 44, 48, 64]


def read_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_series() -> tuple[list[float], list[float]]:
    nu_values: list[float] = []
    dt_hours: list[float] = []

    with SERIES_PATH.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            nu_values.append(float(row["upsets_total_nu"]))
            dt_hours.append(float(row.get("dt_hours", "1.0")) if row.get("dt_hours") else 1.0)

    if not nu_values:
        raise RuntimeError("empty Chapter 3 series")

    return nu_values, dt_hours


def fmt(value: float | int | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if math.isinf(value):
        return "inf"
    if math.isnan(value):
        return "nan"
    return f"{value:.12g}"


def status_for_case(rho_d: float, residual_e: float, min_risk_e: float) -> str:
    if rho_d >= 1.0 or residual_e <= 0.0:
        return "architecture_change_required"
    if min_risk_e > residual_e:
        return "bandwidth_or_tau_min_insufficient"
    return "scrub_period_selectable"


def compile_if_selectable(
    status: str,
    nu_values: list[float],
    dt_hours: list[float],
    residual_e: float,
    periods: tuple[float, ...],
    geometry: MemoryGeometry,
):
    if status != "scrub_period_selectable":
        return None

    return compile_adaptive_current_schedule(
        nu_values=nu_values,
        dt_hours=dt_hours,
        target_e=residual_e,
        period_set_seconds=periods,
        geometry=geometry,
    )


def make_plot(rows: list[dict[str, str]], rho_crit: float) -> str:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        return f"skipped: matplotlib unavailable: {exc}"

    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.0, 4.5))

    for mean_m in MEAN_MULTIPLICITIES:
        xs: list[float] = []
        ys: list[float] = []

        for row in rows:
            if abs(float(row["mean_multiplicity"]) - mean_m) < 1e-12:
                xs.append(float(row["interleaving_depth_D"]))
                ys.append(float(row["rho_D"]))

        ax.plot(xs, ys, marker="o", label=f"mean m={mean_m:g}")

    ax.axhline(1.0, linestyle="--", linewidth=1.0, label="rho_D = 1")
    ax.axhline(rho_crit, linestyle=":", linewidth=1.5, label=f"rho_crit={rho_crit:.5f}")

    ax.set_yscale("log")
    ax.set_xlabel("Interleaving depth D")
    ax.set_ylabel("rho_D")
    ax.set_title("Interleaving dangerous-mapping budget share")
    ax.grid(True, which="both", linewidth=0.5)
    ax.legend()

    fig.tight_layout()
    fig.savefig(OUT_FIG, dpi=180)
    plt.close(fig)

    return str(OUT_FIG.relative_to(REPO_ROOT))


def main() -> int:
    config = read_config()
    nu_values, dt_hours = read_series()

    target_p = float(config["target_mission_probability"])
    target_e = risk_from_mission_probability(target_p)

    geometry = MemoryGeometry(
        word_bits=int(config["geometry"]["word_bits"]),
        codeword_count=int(config["geometry"]["codeword_count"]),
    )

    periods = normalize_period_set(float(value) for value in config["period_set_seconds"])
    tau_min = periods[0]

    tau_min_schedule = [tau_min for _ in nu_values]
    min_stats = stats_for_tau_seconds(
        nu_values=nu_values,
        tau_seconds=tau_min_schedule,
        dt_hours=dt_hours,
        geometry=geometry,
        period_set_seconds=periods,
    )

    rho_crit = 1.0 - min_stats.risk_e / target_e
    total_nu_integral = sum(nu * dt for nu, dt in zip(nu_values, dt_hours))

    rows: list[dict[str, str]] = []

    for mean_m in MEAN_MULTIPLICITIES:
        if mean_m <= 1.0:
            raise RuntimeError("mean multiplicity must exceed one")

        s = (mean_m - 1.0) / mean_m
        expected_event_count = total_nu_integral / mean_m

        for depth_d in D_VALUES:
            g_d = s ** depth_d
            instant_e = g_d * expected_event_count
            rho_d = instant_e / target_e
            residual_e = (1.0 - rho_d) * target_e
            status = status_for_case(rho_d, residual_e, min_stats.risk_e)

            result = compile_if_selectable(
                status,
                nu_values,
                dt_hours,
                residual_e,
                periods,
                geometry,
            )

            if result is None:
                schedule_risk_e = ""
                schedule_p_mission = ""
                schedule_pass_count = ""
                schedule_mean_tau_seconds = ""
                schedule_min_tau_seconds = ""
                schedule_max_tau_seconds = ""
                saturated_at_tau_min = ""
                saturated_at_tau_max = ""
                c_value = ""
                residual_utilization = ""
                fixed_over_schedule_gain = ""
            else:
                schedule_risk_e = fmt(result.stats.risk_e)
                schedule_p_mission = fmt(result.stats.p_mission)
                schedule_pass_count = fmt(result.stats.pass_count)
                schedule_mean_tau_seconds = fmt(result.stats.mean_tau_seconds)
                schedule_min_tau_seconds = fmt(result.stats.min_tau_seconds)
                schedule_max_tau_seconds = fmt(result.stats.max_tau_seconds)
                saturated_at_tau_min = str(result.stats.saturated_at_tau_min).lower()
                saturated_at_tau_max = str(result.stats.saturated_at_tau_max).lower()
                c_value = "" if result.c_value is None else fmt(result.c_value)
                residual_utilization = fmt(result.stats.risk_e / residual_e) if residual_e > 0 else ""
                fixed_over_schedule_gain = fmt(31553280 / result.stats.pass_count)

            rows.append(
                {
                    "mean_multiplicity": fmt(mean_m),
                    "geometric_s": fmt(s),
                    "interleaving_depth_D": str(depth_d),
                    "g_D": fmt(g_d),
                    "total_nu_integral": fmt(total_nu_integral),
                    "expected_event_count": fmt(expected_event_count),
                    "target_e": fmt(target_e),
                    "instant_e": fmt(instant_e),
                    "rho_D": fmt(rho_d),
                    "rho_crit": fmt(rho_crit),
                    "residual_e": fmt(residual_e),
                    "e_acc_at_tau_min": fmt(min_stats.risk_e),
                    "status": status,
                    "schedule_risk_e": schedule_risk_e,
                    "schedule_p_mission": schedule_p_mission,
                    "schedule_pass_count": schedule_pass_count,
                    "fixed_over_schedule_gain": fixed_over_schedule_gain,
                    "residual_utilization": residual_utilization,
                    "schedule_mean_tau_seconds": schedule_mean_tau_seconds,
                    "schedule_min_tau_seconds": schedule_min_tau_seconds,
                    "schedule_max_tau_seconds": schedule_max_tau_seconds,
                    "saturated_at_tau_min": saturated_at_tau_min,
                    "saturated_at_tau_max": saturated_at_tau_max,
                    "c_value": c_value,
                }
            )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())
    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    d_min_rows: list[dict[str, str]] = []
    for mean_m in MEAN_MULTIPLICITIES:
        candidates = [
            row for row in rows
            if abs(float(row["mean_multiplicity"]) - mean_m) < 1e-12
            and row["status"] == "scrub_period_selectable"
        ]
        if candidates:
            first = min(candidates, key=lambda row: int(row["interleaving_depth_D"]))
            d_min_rows.append(
                {
                    "mean_multiplicity": fmt(mean_m),
                    "minimum_selectable_D": first["interleaving_depth_D"],
                    "rho_D_at_minimum": first["rho_D"],
                    "pass_count_at_minimum": first["schedule_pass_count"],
                }
            )
        else:
            d_min_rows.append(
                {
                    "mean_multiplicity": fmt(mean_m),
                    "minimum_selectable_D": "",
                    "rho_D_at_minimum": "",
                    "pass_count_at_minimum": "",
                }
            )

    figure_status = make_plot(rows, rho_crit)

    lines = [
        "# Interleaving g(D) feasibility case",
        "",
        "This report instantiates the Chapter-2 interleaving handoff for the",
        "Chapter-3 five-year upset-rate series.",
        "",
        "The dangerous instantaneous budget share is computed rather than swept:",
        "",
        "`p_m = (1 - s) s^(m-1)`, `s = (mean_m - 1) / mean_m`, `g_D = s^D`,",
        "and `rho_D = g_D N_events / E_target`.",
        "",
        "This is a Chapter-2-consistent limiting design model. It is not a",
        "universal upper bound for arbitrary physical placement; a concrete memory",
        "macro should refine `h_m(D)` from topology or test data.",
        "",
        "## Parameters",
        "",
        "| Quantity | Value |",
        "|---|---:|",
        f"| target probability | {target_p:.12g} |",
        f"| target risk E | {target_e:.12g} |",
        f"| codeword count | {geometry.codeword_count} |",
        f"| word/codeword bits | {geometry.word_bits} |",
        f"| total nu integral | {total_nu_integral:.12g} |",
        f"| tau_min, s | {tau_min:.12g} |",
        f"| E_acc(tau_min) | {min_stats.risk_e:.12g} |",
        f"| rho_crit = 1 - E_acc(tau_min)/E_target | {rho_crit:.12g} |",
        f"| figure | {figure_status} |",
        "",
        "## Minimum selectable interleaving depth",
        "",
        "| Mean multiplicity | Minimum selectable D | rho_D at minimum | Pass count at minimum |",
        "|---:|---:|---:|---:|",
    ]

    for row in d_min_rows:
        lines.append(
            "| {mean_multiplicity} | {minimum_selectable_D} | {rho_D_at_minimum} | "
            "{pass_count_at_minimum} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Main case: mean multiplicity = 2",
            "",
            "| D | g_D | rho_D | Status | Schedule passes | Mean tau, s | Tau range, s |",
            "|---:|---:|---:|---|---:|---:|---:|",
        ]
    )

    for row in rows:
        if abs(float(row["mean_multiplicity"]) - 2.0) > 1e-12:
            continue

        tau_range = "-"
        if row["schedule_min_tau_seconds"]:
            tau_range = f"{row['schedule_min_tau_seconds']}..{row['schedule_max_tau_seconds']}"

        lines.append(
            f"| {row['interleaving_depth_D']} | {row['g_D']} | {row['rho_D']} | "
            f"{row['status']} | {row['schedule_pass_count'] or '-'} | "
            f"{row['schedule_mean_tau_seconds'] or '-'} | {tau_range} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `rho_D >= 1` means the instantaneous component alone consumes or exceeds",
            "  the full mission-risk budget; architectural mitigation is required.",
            "- `rho_D > rho_crit` means a residual accumulated-risk budget remains, but",
            "  even continuous operation at `tau_min` is insufficient.",
            "- `rho_D < rho_crit` means a scrub-period schedule can be selected for the",
            "  residual accumulated-risk budget.",
            "- Thus the minimum interleaving depth is set by the stricter realizability",
            "  gate `rho_D < rho_crit`, not merely by `rho_D < 1`.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "generated_by": "run_interleaving_gd_case.py",
                "assumptions": {
                    "multiplicity_distribution": "geometric",
                    "p_m": "(1 - s) * s^(m-1)",
                    "s": "(mean_m - 1) / mean_m",
                    "dangerous_mapping_model": "g_D = s^D",
                    "event_count": "sum(nu_i * dt_i) / mean_m",
                    "scope": "Chapter-2-consistent design-case instantiation, not a universal placement bound",
                },
                "target_p": target_p,
                "target_e": target_e,
                "total_nu_integral": total_nu_integral,
                "tau_min_seconds": tau_min,
                "e_acc_at_tau_min": min_stats.risk_e,
                "rho_crit": rho_crit,
                "d_min_rows": d_min_rows,
                "figure": figure_status,
                "rows": rows,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print("Figure:", figure_status)
    print()
    print(OUT_MD.read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
