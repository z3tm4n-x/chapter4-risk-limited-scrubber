#!/usr/bin/env python3
"""Build an aggregate Chapter 3 model-to-RTL certificate."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SUMMARY_PATH = REPO_ROOT / "results" / "schedules" / "ch3_five_year_summary.csv"
FIXED_SWEEP_PATH = REPO_ROOT / "results" / "schedules" / "ch3_five_year_fixed_candidate_sweep.csv"
WINDOW_REPLAY_PATH = REPO_ROOT / "results" / "rtl_replay" / "ch3_window_replay_summary.csv"
IMPORT_SUMMARY_PATH = REPO_ROOT / "results" / "schedules" / "ch3_series_import_summary.csv"

OUT_CSV = REPO_ROOT / "results" / "chapter4_model_rtl_certificate.csv"
OUT_MD = REPO_ROOT / "results" / "chapter4_model_rtl_certificate.md"
OUT_JSON = REPO_ROOT / "results" / "chapter4_model_rtl_certificate.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_metric_csv(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    return {row["metric"]: row["value"] for row in rows}


def git_commit() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def build_csv_rows(summary_rows: list[dict[str, str]], replay_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for row in summary_rows:
        rows.append(
            {
                "artifact_type": "five_year_model_schedule",
                "strategy": row["strategy_key"],
                "window_name": "full_2021_2025",
                "target_p": row["target_p"],
                "risk_e": row["risk_e"],
                "p_mission": row["p_mission"],
                "risk_utilization": row["risk_utilization"],
                "model_pass_count": row["pass_count"],
                "rtl_observed_pass_starts": "",
                "rtl_completed_passes": "",
                "pass_start_delta": "",
                "completed_delta": "",
                "selected_mismatches": "",
                "safe_mode_cycles": "",
                "failures": "",
                "status": "model_risk_pass" if float(row["p_mission"]) <= float(row["target_p"]) else "model_risk_fail",
            }
        )

    for row in replay_rows:
        pass_delta = int(row["pass_start_delta_vs_expected"])
        completed_delta = int(row["completed_delta_vs_expected"])
        mismatches = int(row["selected_mismatches"])
        safe_cycles = int(row["safe_mode_cycles"])
        failures = int(row["failures"])
        ok = pass_delta == 0 and completed_delta == 0 and mismatches == 0 and safe_cycles == 0 and failures == 0

        rows.append(
            {
                "artifact_type": "rtl_window_replay",
                "strategy": row["strategy"],
                "window_name": row["window_name"],
                "target_p": "",
                "risk_e": "",
                "p_mission": "",
                "risk_utilization": "",
                "model_pass_count": row["expected_passes"],
                "rtl_observed_pass_starts": row["observed_pass_starts"],
                "rtl_completed_passes": row["completed_passes"],
                "pass_start_delta": row["pass_start_delta_vs_expected"],
                "completed_delta": row["completed_delta_vs_expected"],
                "selected_mismatches": row["selected_mismatches"],
                "safe_mode_cycles": row["safe_mode_cycles"],
                "failures": row["failures"],
                "status": "rtl_replay_pass" if ok else "rtl_replay_fail",
            }
        )

    return rows


def write_outputs() -> None:
    import_metrics = read_metric_csv(IMPORT_SUMMARY_PATH)
    summary_rows = read_csv(SUMMARY_PATH)
    fixed_sweep_rows = read_csv(FIXED_SWEEP_PATH)
    replay_rows = read_csv(WINDOW_REPLAY_PATH)

    csv_rows = build_csv_rows(summary_rows, replay_rows)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "artifact_type",
        "strategy",
        "window_name",
        "target_p",
        "risk_e",
        "p_mission",
        "risk_utilization",
        "model_pass_count",
        "rtl_observed_pass_starts",
        "rtl_completed_passes",
        "pass_start_delta",
        "completed_delta",
        "selected_mismatches",
        "safe_mode_cycles",
        "failures",
        "status",
    ]

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    model_pass = all(row["status"] == "model_risk_pass" for row in csv_rows if row["artifact_type"] == "five_year_model_schedule")
    rtl_pass = all(row["status"] == "rtl_replay_pass" for row in csv_rows if row["artifact_type"] == "rtl_window_replay")

    best_fixed = next(row for row in summary_rows if row["strategy_key"] == "fixed")
    current = next(row for row in summary_rows if row["strategy_key"] == "current")
    delayed = next(row for row in summary_rows if row["strategy_key"] == "delayed_1h")
    forecast = next(row for row in summary_rows if row["strategy_key"] == "forecast")

    ten_second_row = next(row for row in fixed_sweep_rows if row["tau_seconds"] == "10")
    five_second_row = next(row for row in fixed_sweep_rows if row["tau_seconds"] == "5")

    certificate = {
        "generated_by": "build_ch3_model_rtl_certificate.py",
        "series": {
            "hours": import_metrics["hour_count"],
            "start": import_metrics["start_timestamp_utc"],
            "end": import_metrics["end_timestamp_utc"],
            "mean_total_nu": import_metrics["total_nu_mean"],
            "cv2_total": import_metrics["total_nu_cv2"],
            "eta_const": import_metrics["total_nu_eta_const"],
            "max_total_nu": import_metrics["total_nu_max"],
        },
        "model_schedule_pass": model_pass,
        "rtl_window_replay_pass": rtl_pass,
        "best_fixed": best_fixed,
        "current": current,
        "delayed_1h": delayed,
        "forecast": forecast,
        "fixed_5s": five_second_row,
        "fixed_10s": ten_second_row,
        "window_replay_cases": len(replay_rows),
    }

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(certificate, file, indent=2, ensure_ascii=False)

    lines = [
        "# Chapter 4 model-to-RTL certificate",
        "",
        "This certificate aggregates the Chapter 3 five-year model schedules and",
        "the Chapter 4 RTL window replay results.",
        "",
        "## Series",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| hours | {import_metrics['hour_count']} |",
        f"| start | {import_metrics['start_timestamp_utc']} |",
        f"| end | {import_metrics['end_timestamp_utc']} |",
        f"| mean total nu, 1/hour | {import_metrics['total_nu_mean']} |",
        f"| CV^2 | {import_metrics['total_nu_cv2']} |",
        f"| eta_const = 1 + CV^2 | {import_metrics['total_nu_eta_const']} |",
        f"| max total nu, 1/hour | {import_metrics['total_nu_max']} |",
        "",
        "## Five-year exact-risk schedules",
        "",
        "| Strategy | P mission | E risk | Risk utilization | Pass count | Fixed/strategy gain | Tau range, s | Eta shape |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in summary_rows:
        eta = row["eta_shape"] if row["eta_shape"] else "-"
        lines.append(
            f"| {row['strategy_key']} | {row['p_mission']} | {row['risk_e']} | "
            f"{row['risk_utilization']} | {row['pass_count']} | "
            f"{row['gain_fixed_over_strategy']} | {row['min_tau_seconds']}..{row['max_tau_seconds']} | {eta} |"
        )

    lines.extend(
        [
            "",
            "## Fixed-candidate boundary",
            "",
            f"The best allowed fixed period is 5 s with risk utilization {five_second_row['risk_utilization']}.",
            f"The next fixed candidate, 10 s, is not allowed: risk utilization {ten_second_row['risk_utilization']}.",
            "Therefore fixed/adaptive gain is larger than the continuous 1+CV^2 bound because the fixed baseline is discretized.",
            "",
            "## RTL window replay",
            "",
            "| Strategy | Window | Model passes | RTL pass starts | Completed | Delta | Mismatches | Safe cycles | Failures |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for row in replay_rows:
        lines.append(
            f"| {row['strategy']} | {row['window_name']} | {row['expected_passes']} | "
            f"{row['observed_pass_starts']} | {row['completed_passes']} | "
            f"{row['pass_start_delta_vs_expected']} | {row['selected_mismatches']} | "
            f"{row['safe_mode_cycles']} | {row['failures']} |"
        )

    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- Five-year model schedules satisfy the mission-risk target: `{str(model_pass).lower()}`.",
            f"- RTL window replay matches model pass counts with zero mismatches: `{str(rtl_pass).lower()}`.",
            "- The RTL controller receives only period indices; it does not receive nu(t), risk values, or the radiation model.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print("model_schedule_pass:", model_pass)
    print("rtl_window_replay_pass:", rtl_pass)


def main() -> int:
    write_outputs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
