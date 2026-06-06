#!/usr/bin/env python3
"""Residual-budget / rho_D sweep for the Chapter 3 five-year series.

rho_D is treated as the fraction of the total admissible risk budget consumed
by the instant, non-scrub-controllable component.  The remaining accumulated
budget is

    E_residual = (1 - rho_D) * E_target.

The sweep demonstrates the Chapter 2 handoff:
  - if E_residual <= 0, period selection is meaningless;
  - if E_acc(tau_min) > E_residual, even maximum scrub rate is insufficient;
  - otherwise the Chapter 3 schedule compiler can select a period schedule.
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
    compile_adaptive_current_schedule,
    normalize_period_set,
    stats_for_tau_seconds,
)


CONFIG_PATH = REPO_ROOT / "configs" / "ch3_main_1pct.json"
SERIES_PATH = REPO_ROOT / "data" / "ch3_five_year_upsets.csv"

OUT_CSV = REPO_ROOT / "results" / "feasibility" / "rho_d_sweep_summary.csv"
OUT_MD = REPO_ROOT / "results" / "feasibility" / "rho_d_sweep_summary.md"
OUT_JSON = REPO_ROOT / "results" / "feasibility" / "rho_d_sweep_certificate.json"


RHO_VALUES = [
    0.0,
    0.25,
    0.50,
    0.75,
    0.85,
    0.88,
    0.8890,
    0.8895,
    0.88955,
    0.89,
    0.90,
    0.95,
    0.99,
    1.0,
]


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
        raise RuntimeError("empty series")

    return nu_values, dt_hours


def status_for_case(residual_e: float, min_risk_e: float) -> str:
    if residual_e <= 0.0:
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

    rows: list[dict[str, str]] = []

    for rho in RHO_VALUES:
        instant_e = rho * target_e
        residual_e = (1.0 - rho) * target_e
        status = status_for_case(residual_e, min_stats.risk_e)

        result = compile_if_selectable(status, nu_values, dt_hours, residual_e, periods, geometry)

        if result is None:
            schedule_risk_e = ""
            schedule_p_mission = ""
            schedule_pass_count = ""
            schedule_mean_tau = ""
            schedule_min_tau = ""
            schedule_max_tau = ""
            saturated_min = ""
            saturated_max = ""
            c_value = ""
            residual_utilization = ""
            pass_gain_vs_tau_min = ""
        else:
            schedule_risk_e = f"{result.stats.risk_e:.12g}"
            schedule_p_mission = f"{result.stats.p_mission:.12g}"
            schedule_pass_count = f"{result.stats.pass_count:.12g}"
            schedule_mean_tau = f"{result.stats.mean_tau_seconds:.12g}"
            schedule_min_tau = f"{result.stats.min_tau_seconds:.12g}"
            schedule_max_tau = f"{result.stats.max_tau_seconds:.12g}"
            saturated_min = str(result.stats.saturated_at_tau_min).lower()
            saturated_max = str(result.stats.saturated_at_tau_max).lower()
            c_value = "" if result.c_value is None else f"{result.c_value:.12g}"
            residual_utilization = f"{result.stats.risk_e / residual_e:.12g}" if residual_e > 0 else ""
            pass_gain_vs_tau_min = f"{min_stats.pass_count / result.stats.pass_count:.12g}"

        slack_after_tau_min = residual_e - min_stats.risk_e
        instant_utilization = instant_e / target_e
        tau_min_residual_utilization = min_stats.risk_e / residual_e if residual_e > 0.0 else math.inf

        rows.append(
            {
                "rho_D": f"{rho:.12g}",
                "status": status,
                "target_p": f"{target_p:.12g}",
                "target_e": f"{target_e:.12g}",
                "instant_e": f"{instant_e:.12g}",
                "residual_e": f"{residual_e:.12g}",
                "tau_min_seconds": f"{tau_min:.12g}",
                "e_acc_at_tau_min": f"{min_stats.risk_e:.12g}",
                "p_acc_at_tau_min": f"{min_stats.p_mission:.12g}",
                "risk_slack_after_tau_min": f"{slack_after_tau_min:.12g}",
                "instant_utilization": f"{instant_utilization:.12g}",
                "tau_min_residual_utilization": f"{tau_min_residual_utilization:.12g}",
                "schedule_risk_e": schedule_risk_e,
                "schedule_p_mission": schedule_p_mission,
                "schedule_pass_count": schedule_pass_count,
                "pass_gain_vs_tau_min": pass_gain_vs_tau_min,
                "schedule_mean_tau_seconds": schedule_mean_tau,
                "schedule_min_tau_seconds": schedule_min_tau,
                "schedule_max_tau_seconds": schedule_max_tau,
                "saturated_at_tau_min": saturated_min,
                "saturated_at_tau_max": saturated_max,
                "c_value": c_value,
            }
        )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "rho_D",
        "status",
        "target_p",
        "target_e",
        "instant_e",
        "residual_e",
        "tau_min_seconds",
        "e_acc_at_tau_min",
        "p_acc_at_tau_min",
        "risk_slack_after_tau_min",
        "instant_utilization",
        "tau_min_residual_utilization",
        "schedule_risk_e",
        "schedule_p_mission",
        "schedule_pass_count",
        "pass_gain_vs_tau_min",
        "schedule_mean_tau_seconds",
        "schedule_min_tau_seconds",
        "schedule_max_tau_seconds",
        "saturated_at_tau_min",
        "saturated_at_tau_max",
        "c_value",
    ]

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# rho_D residual-budget sweep",
        "",
        "This sweep demonstrates the Chapter 2 feasibility handoff for the",
        "Chapter 3 five-year series.",
        "",
        "| Quantity | Value |",
        "|---|---:|",
        f"| target probability | {target_p:.12g} |",
        f"| target risk E | {target_e:.12g} |",
        f"| tau_min, s | {tau_min:.12g} |",
        f"| E_acc(tau_min) | {min_stats.risk_e:.12g} |",
        f"| P_acc(tau_min) | {min_stats.p_mission:.12g} |",
        f"| rho_crit = 1 - E_acc(tau_min)/E_target | {rho_crit:.12g} |",
        "",
        "## Sweep",
        "",
        "| rho_D | Status | E_residual | Slack after tau_min | tau_min/residual utilization | Schedule passes | Tau range, s | Saturated tau_min |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        tau_range = "-"
        if row["schedule_min_tau_seconds"]:
            tau_range = f"{row['schedule_min_tau_seconds']}..{row['schedule_max_tau_seconds']}"

        passes = row["schedule_pass_count"] or "-"
        saturated = row["saturated_at_tau_min"] or "-"

        lines.append(
            f"| {row['rho_D']} | {row['status']} | {row['residual_e']} | "
            f"{row['risk_slack_after_tau_min']} | {row['tau_min_residual_utilization']} | "
            f"{passes} | {tau_range} | {saturated} |"
        )

    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- Below rho_crit, a scrub schedule can be selected from the residual accumulated-risk budget.",
            "- Near rho_crit, the schedule is forced toward tau_min saturation.",
            "- Above rho_crit, even continuous operation at tau_min cannot satisfy the residual budget; the system must escalate.",
            "- This computation is model-side evidence for the out-of-envelope flag implemented by the diagnostic supervisor.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "target_p": target_p,
                "target_e": target_e,
                "tau_min_seconds": tau_min,
                "e_acc_at_tau_min": min_stats.risk_e,
                "p_acc_at_tau_min": min_stats.p_mission,
                "rho_crit": rho_crit,
                "rows": rows,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print("rho_crit:", f"{rho_crit:.12g}")
    print()
    print(OUT_CSV.read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
