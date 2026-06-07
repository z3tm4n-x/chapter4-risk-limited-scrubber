#!/usr/bin/env python3
"""Build the aggregate Chapter 4 evidence pack.

This file intentionally aggregates reproducible artifacts only. It is not the
chapter text. The chapter can later be written from these results.
"""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_MD = REPO_ROOT / "results" / "chapter4_evidence_pack.md"
OUT_JSON = REPO_ROOT / "results" / "chapter4_evidence_pack.json"


ARTIFACTS = [
    {
        "key": "series_import",
        "title": "Chapter 3 five-year series import",
        "path": "results/schedules/ch3_series_import_summary.csv",
        "claim": "The five-year upset series is imported and transformed into the total upset-rate series used by Chapter 3.",
    },
    {
        "key": "five_year_schedule",
        "title": "Chapter 3 five-year exact-risk schedules",
        "path": "results/schedules/ch3_five_year_summary.md",
        "claim": "The fixed/current/delayed schedules are compiled on the dissertation geometry and target probability.",
    },
    {
        "key": "model_rtl_replay",
        "title": "Model-to-RTL schedule replay certificate",
        "path": "results/chapter4_model_rtl_certificate.md",
        "claim": "The RTL controller executes model-generated period indices with zero pass-count mismatch on representative windows.",
    },
    {
        "key": "fault_replay",
        "title": "Radiation-window fault replay",
        "path": "results/rtl_replay/ch3_fault_replay_summary.md",
        "claim": "The selected radiation windows are replayed with fault streams and separated DUE/persistent/SDC-audit metrics.",
    },
    {
        "key": "interleaving_mbu",
        "title": "Interleaving MBU experiment",
        "path": "results/rtl_replay/interleaving_mbu_summary.md",
        "claim": "The same physical MBU is dangerous without interleaving and correctable when split across codewords.",
    },
    {
        "key": "diagnostic_supervisor",
        "title": "Diagnostic supervisor RTL",
        "path": "results/rtl_replay/diagnostic_supervisor_report.md",
        "claim": "The diagnostic block raises alert, persistent-DUE, out-of-envelope, and force-conservative flags from SEC-DED symptoms.",
    },
    {
        "key": "due_tracker_contract",
        "title": "Limited DUE tracker contract",
        "path": "results/rtl_replay/due_tracker_contract.md",
        "claim": "Persistent-DUE diagnostics use bounded associative state rather than a full depth-wide bitmap.",
    },
    {
        "key": "integrated_diagnostic",
        "title": "Integrated diagnostic controller RTL",
        "path": "results/rtl_replay/integrated_diagnostic_controller_report.md",
        "claim": "The top-level external-period controller exposes diagnostic flags from real scrub events.",
    },
    {
        "key": "tau_min_certificate",
        "title": "Tau-min hardware feasibility certificate",
        "path": "results/feasibility/tau_min_certificate.md",
        "claim": "The Chapter 3 minimum scrub period is connected to an explicit hardware service-rate model and shown feasible for the dissertation memory geometry.",
    },
    {
        "key": "timebase_contract",
        "title": "RTL timebase contract",
        "path": "results/rtl_replay/timebase_contract.md",
        "claim": "The RTL scheduler counts coarse timebase ticks rather than long raw implementation-clock intervals.",
    },
    {
        "key": "rho_d_sweep",
        "title": "rho_D residual-budget sweep",
        "path": "results/feasibility/rho_d_sweep_summary.md",
        "claim": "The residual-budget boundary is reproduced numerically; above rho_crit, tau_min is insufficient.",
    },
    {
        "key": "monte_carlo",
        "title": "Accumulated-risk Monte Carlo validation",
        "path": "results/monte_carlo/accumulation_monte_carlo_report.md",
        "claim": "The exact accumulated-risk kernel is validated by direct random placement at accelerated lambda values.",
    },
    {
        "key": "measured_estimator",
        "title": "Measured-error period estimator RTL",
        "path": "results/rtl_replay/measured_error_estimator_report.md",
        "claim": "The onboard estimator relaxes on quiet passes, speeds up on corrections, and forces safe period on DUE.",
    },
    {
        "key": "measured_controller",
        "title": "Integrated measured-error controller RTL",
        "path": "results/rtl_replay/measured_error_controller_report.md",
        "claim": "The measured-error estimator is integrated into a complete autonomous scrub controller.",
    },
    {
        "key": "measured_policy_model",
        "title": "Measured-error policy model evaluation",
        "path": "results/schedules/measured_policy_model_report.md",
        "claim": "Counter-based measured-error policies are evaluated on the five-year series; conservative settings meet the target but use more passes than external exact-risk schedules.",
    },
    {
        "key": "measured_policy_seed_sweep",
        "title": "Measured-error policy seed robustness sweep",
        "path": "results/schedules/measured_policy_seed_sweep_report.md",
        "claim": "Measured-error policy robustness is checked over multiple Poisson seeds; conservative q16 policies meet the target in all sampled seeds.",
    },
    {
        "key": "synthesis",
        "title": "RTL synthesis/resource summary",
        "path": "results/synthesis/rtl_synthesis_summary.md",
        "claim": "Flattened Yosys/XC7 synthesis estimates quantify the hardware cost of the blocks.",
    },
    {
        "key": "ch4_geometry_synthesis",
        "title": "Chapter 4 dissertation-geometry synthesis",
        "path": "results/synthesis/ch4_geometry_synthesis_summary.md",
        "claim": "Key RTL tops are synthesized with the dissertation memory address width and codeword count.",
    },
    {
        "key": "overhead_gain",
        "title": "Overhead/gain certificate",
        "path": "results/chapter4_overhead_gain_certificate.md",
        "claim": "Schedule benefit and RTL resource cost are combined in one certificate.",
    },
]


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


def read_text_if_exists(relative_path: str) -> str:
    path = REPO_ROOT / relative_path

    if not path.exists():
        return f"**MISSING ARTIFACT:** `{relative_path}`\n"

    return path.read_text(encoding="utf-8")


def read_csv_rows(relative_path: str) -> list[dict[str, str]]:
    path = REPO_ROOT / relative_path

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def compact_key_numbers() -> list[str]:
    lines: list[str] = []

    schedule = read_csv_rows("results/schedules/ch3_five_year_summary.csv")
    overhead = read_csv_rows("results/chapter4_overhead_gain_certificate.csv")
    rho_rows = read_csv_rows("results/feasibility/rho_d_sweep_summary.csv")
    tau_rows = read_csv_rows("results/feasibility/tau_min_certificate.csv")
    mc_rows = read_csv_rows("results/monte_carlo/accumulation_monte_carlo_summary.csv")

    if schedule:
        fixed = next(row for row in schedule if row["strategy_key"] == "fixed")
        current = next(row for row in schedule if row["strategy_key"] == "current")
        delayed = next(row for row in schedule if row["strategy_key"] == "delayed_1h")

        lines.extend(
            [
                f"- Fixed pass count: `{fixed['pass_count']}`.",
                f"- Current adaptive pass count: `{current['pass_count']}`; fixed/current gain: `{current['gain_fixed_over_strategy']}`.",
                f"- Delayed 1h adaptive pass count: `{delayed['pass_count']}`; fixed/delayed gain: `{delayed['gain_fixed_over_strategy']}`.",
                f"- Current adaptive mission probability: `{current['p_mission']}`.",
                f"- Delayed 1h mission probability: `{delayed['p_mission']}`.",
            ]
        )

    if overhead:
        external = next(row for row in overhead if row["item"] == "external_current_adaptive_schedule")
        measured = next(row for row in overhead if row["item"] == "measured_error_onboard_fallback")

        lines.extend(
            [
                f"- External adaptive controller XC7 estimate: `{external['lut']}` LUT, `{external['ff']}` FF.",
                f"- Measured-error controller XC7 estimate: `{measured['lut']}` LUT, `{measured['ff']}` FF.",
                f"- Measured-error increment over external endpoint: `+{measured['delta_lut_vs_external']}` LUT, `+{measured['delta_ff_vs_external']}` FF.",
            ]
        )

    if rho_rows:
        # Pick the last selectable and first insufficient rows around the boundary.
        selectable = [row for row in rho_rows if row["status"] == "scrub_period_selectable"]
        insufficient = [row for row in rho_rows if row["status"] == "bandwidth_or_tau_min_insufficient"]

        if selectable:
            lines.append(f"- Last sampled selectable rho_D: `{selectable[-1]['rho_D']}`.")
        if insufficient:
            lines.append(f"- First sampled tau_min-insufficient rho_D: `{insufficient[0]['rho_D']}`.")

    if tau_rows:
        tau = {row["metric"]: row["value"] for row in tau_rows}
        lines.append(
            f"- Tau-min pass time: `{tau['pass_time_seconds']}` s; "
            f"margin `{tau['tau_min_margin']}`; feasible `{tau['tau_min_feasible']}`."
        )

    if mc_rows:
        all_pass = all(row["pass_z_4sigma"] == "true" for row in mc_rows)
        lines.append(f"- Monte Carlo accumulated-risk validation 4-sigma pass: `{str(all_pass).lower()}`.")

    measured_policy = read_csv_rows("results/schedules/measured_policy_model_summary.csv")
    if measured_policy:
        passing = [row for row in measured_policy if row["target_met"] == "true"]
        if passing:
            best = min(passing, key=lambda row: float(row["pass_count"]))
            lines.append(
                f"- Best sampled target-meeting measured policy: `{best['policy']}`; "
                f"pass count `{best['pass_count']}`, fixed/policy gain `{best['fixed_over_policy_gain']}`."
            )

        failing = [row for row in measured_policy if row["target_met"] == "false"]
        if failing:
            best_failing = min(failing, key=lambda row: float(row["pass_count"]))
            lines.append(
                f"- Fastest sampled measured policy fails target: `{best_failing['policy']}`; "
                f"risk utilization `{best_failing['risk_utilization']}`."
            )

    seed_sweep = read_csv_rows("results/schedules/measured_policy_seed_sweep_summary.csv")
    if seed_sweep:
        robust = [
            row for row in seed_sweep
            if row["target_met_fraction"] == "1"
        ]

        if robust:
            best = min(robust, key=lambda row: float(row["pass_count_mean"]))
            lines.append(
                f"- Best robust measured policy over seed sweep: `{best['policy']}`; "
                f"mean pass count `{best['pass_count_mean']}`, "
                f"max risk utilization `{best['risk_utilization_max']}`."
            )

        failing = [
            row for row in seed_sweep
            if row["target_met_fraction"] != "1"
        ]

        if failing:
            fastest_failing = min(failing, key=lambda row: float(row["pass_count_mean"]))
            lines.append(
                f"- Fastest seed-swept measured policy fails robustness: `{fastest_failing['policy']}`; "
                f"target-met fraction `{fastest_failing['target_met_fraction']}`."
            )

    return lines


def main() -> int:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "generated_by": "build_chapter4_evidence_pack.py",
        "artifacts": ARTIFACTS,
    }

    lines = [
        "# Chapter 4 evidence pack",
        "",
        "This aggregate file collects reproducible model, RTL, fault-replay,",
        "diagnostic, measured-mode, feasibility, Monte Carlo, and synthesis",
        "artifacts for the Chapter 4 implementation.",
        "",
        "It is an evidence pack, not dissertation prose.",
        "",
        "## Build metadata",
        "",
        f"- Generated by: `{metadata['generated_by']}`",
        "",
        "## Claim matrix",
        "",
        "| Claim | Evidence artifact |",
        "|---|---|",
    ]

    for artifact in ARTIFACTS:
        lines.append(f"| {artifact['claim']} | `{artifact['path']}` |")

    lines.extend(
        [
            "",
            "## Compact key numbers",
            "",
            *compact_key_numbers(),
            "",
            "## Aggregated artifact contents",
            "",
        ]
    )

    for artifact in ARTIFACTS:
        lines.extend(
            [
                f"## {artifact['title']}",
                "",
                f"Source artifact: `{artifact['path']}`.",
                "",
                read_text_if_exists(artifact["path"]).strip(),
                "",
            ]
        )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2, ensure_ascii=False)

    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print()
    print("=== Compact key numbers ===")
    for line in compact_key_numbers():
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
