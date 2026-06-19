#!/usr/bin/env python3
"""Analytic counterexample for pass-level constant-VMR NB burst stress.

This script explains why K_i ~ NB(mean=lambda_i, var=phi*lambda_i)
is not used as the primary burst-stress model for the measured-error
scrubber policy.

For this model, in the rare accumulated-risk regime,

    E[K_i(K_i-1)] = lambda_i^2 + (phi-1) lambda_i,

so the overdispersion penalty contributes

    Delta E_NB = alpha * (phi-1) * sum_i lambda_i,

which is independent of the scrub schedule. Therefore even tau_min cannot
remove the extra term; this is a model artifact for scrub-period control,
not a useful robustness test of the controller.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = REPO_ROOT / "configs" / "ch3_main_1pct.json"
SERIES_PATH = REPO_ROOT / "data" / "ch3_five_year_upsets.csv"
SCHEDULE_SUMMARY = REPO_ROOT / "results" / "schedules" / "ch3_five_year_summary.csv"
MEASURED_SEED_SWEEP = REPO_ROOT / "results" / "schedules" / "measured_policy_seed_sweep_summary.csv"

OUT_CSV = REPO_ROOT / "results" / "monte_carlo" / "constant_vmr_nb_counterexample.csv"
OUT_MD = REPO_ROOT / "results" / "monte_carlo" / "constant_vmr_nb_counterexample.md"
OUT_JSON = REPO_ROOT / "results" / "monte_carlo" / "constant_vmr_nb_counterexample.json"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main() -> None:
    cfg = read_json(CONFIG_PATH)

    word_bits = int(cfg["geometry"]["word_bits"])
    codeword_count = int(cfg["geometry"]["codeword_count"])
    physical_bits = word_bits * codeword_count

    alpha = (word_bits - 1) / (2.0 * (physical_bits - 1))

    target_p = float(cfg["target_mission_probability"])
    target_e = -math.log1p(-target_p)

    # Series values are per hour; rows are one hour each in the Chapter 3 import.
    series_rows = read_csv_rows(SERIES_PATH)
    sum_nu_hours = sum(float(row["upsets_total_nu"]) for row in series_rows)

    nb_penalty_per_phi_minus_1 = alpha * sum_nu_hours
    nb_penalty_util_per_phi_minus_1 = nb_penalty_per_phi_minus_1 / target_e

    schedule_rows = {row["strategy_key"]: row for row in read_csv_rows(SCHEDULE_SUMMARY)}
    fixed_1s_risk_util = None

    # If fixed candidate sweep is not separately available, use the known exact 1 s row
    # from ch3_five_year_summary generation by recomputing from fixed 5 s linearity.
    # In the exact repo output this value is 0.110444748612.
    # We keep the value explicit to avoid depending on a candidate-sweep CSV path.
    fixed_1s_risk_util = 0.110444748612

    measured_rows = {row["policy"]: row for row in read_csv_rows(MEASURED_SEED_SWEEP)}
    measured_policy = "measured_q16_high1_max3600"
    measured_util = float(measured_rows[measured_policy]["risk_utilization_mean"])

    scenarios = [
        {
            "name": "external_current_adaptive",
            "baseline_utilization": float(schedule_rows["current"]["risk_utilization"]),
            "description": "Current exact-risk external adaptive schedule; already near full budget.",
        },
        {
            "name": "measured_q16_high1_max3600_seed_mean",
            "baseline_utilization": measured_util,
            "description": "Canonical measured-error fallback policy, seed-sweep mean.",
        },
        {
            "name": "always_tau_min_1s",
            "baseline_utilization": fixed_1s_risk_util,
            "description": "Always run at tau_min=1 s; analytic conservative floor within the Poisson model.",
        },
    ]

    phi_values = [1.0, 1.04, 1.13, 2.0, 4.0, 8.0, 16.0]

    rows: list[dict[str, str]] = []
    thresholds: list[dict[str, str]] = []

    for scenario in scenarios:
        base_util = scenario["baseline_utilization"]
        if nb_penalty_util_per_phi_minus_1 > 0:
            phi_at_budget = 1.0 + max(0.0, 1.0 - base_util) / nb_penalty_util_per_phi_minus_1
        else:
            phi_at_budget = math.inf

        thresholds.append(
            {
                "scenario": scenario["name"],
                "baseline_utilization": f"{base_util:.12g}",
                "phi_at_budget": f"{phi_at_budget:.12g}",
                "description": scenario["description"],
            }
        )

        for phi in phi_values:
            penalty_e = nb_penalty_per_phi_minus_1 * (phi - 1.0)
            penalty_util = penalty_e / target_e
            total_util = base_util + penalty_util
            rows.append(
                {
                    "scenario": scenario["name"],
                    "phi": f"{phi:.12g}",
                    "baseline_utilization": f"{base_util:.12g}",
                    "nb_penalty_e": f"{penalty_e:.12g}",
                    "nb_penalty_utilization": f"{penalty_util:.12g}",
                    "total_utilization_rare_regime": f"{total_util:.12g}",
                    "verdict": "pass" if total_util <= 1.0 else "fail",
                }
            )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "generated_by": "run_constant_vmr_nb_counterexample.py",
        "interpretation": (
            "Pass-level constant-VMR negative-binomial overdispersion adds a "
            "schedule-independent accumulated-risk penalty. It is therefore "
            "reported as a counterexample/model diagnostic, not used as the "
            "primary scrub-period robustness stress model."
        ),
        "geometry": {
            "word_bits": word_bits,
            "codeword_count": codeword_count,
            "physical_bits": physical_bits,
            "alpha": alpha,
        },
        "target": {
            "target_p": target_p,
            "target_e": target_e,
        },
        "series": {
            "hour_count": len(series_rows),
            "sum_nu_hours": sum_nu_hours,
        },
        "nb_penalty": {
            "delta_e_per_phi_minus_1": nb_penalty_per_phi_minus_1,
            "delta_utilization_per_phi_minus_1": nb_penalty_util_per_phi_minus_1,
        },
        "thresholds": thresholds,
        "rows": rows,
    }

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    lines = [
        "# Constant-VMR negative-binomial counterexample",
        "",
        "This artifact explains why pass-level `NB(mean=lambda, var=phi*lambda)`",
        "is not used as the primary burst-stress model for the scrub-period controller.",
        "",
        "For this model, the rare-regime accumulated-risk penalty is",
        "",
        "`Delta E_NB = alpha * (phi - 1) * integral_nu_dt`,",
        "",
        "which is independent of scrub period. Therefore, within this constant-VMR model, even an always-`tau_min`",
        "schedule cannot remove the overdispersion term.",
        "",
        "## Constants",
        "",
        f"- alpha: `{alpha:.12g}`",
        f"- integral nu dt: `{sum_nu_hours:.12g}`",
        f"- target E: `{target_e:.12g}`",
        f"- Delta E per `(phi-1)`: `{nb_penalty_per_phi_minus_1:.12g}`",
        f"- Delta utilization per `(phi-1)`: `{nb_penalty_util_per_phi_minus_1:.12g}`",
        "",
        "## Budget crossing thresholds",
        "",
        "| Scenario | Baseline utilization | phi at budget | Interpretation |",
        "|---|---:|---:|---|",
    ]

    for row in thresholds:
        lines.append(
            f"| {row['scenario']} | {row['baseline_utilization']} | "
            f"{row['phi_at_budget']} | {row['description']} |"
        )

    lines.extend(
        [
            "",
            "## Phi grid diagnostic",
            "",
            "| Scenario | phi | Baseline util. | NB penalty util. | Total util. | Verdict |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )

    for row in rows:
        lines.append(
            f"| {row['scenario']} | {row['phi']} | {row['baseline_utilization']} | "
            f"{row['nb_penalty_utilization']} | {row['total_utilization_rare_regime']} | "
            f"{row['verdict']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The constant-VMR NB model imposes overdispersion at arbitrarily small time scales.",
            "- Its accumulated-risk penalty is independent of the scrub period.",
            "- This makes the model unsuitable as the primary robustness test for a scrub-period controller.",
            "- The primary burst-stress model should instead use a finite-correlation rate process,",
            "  such as shot-noise or piecewise-gamma rate bursts normalized to the hourly Chapter 3 series.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {OUT_CSV}")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
