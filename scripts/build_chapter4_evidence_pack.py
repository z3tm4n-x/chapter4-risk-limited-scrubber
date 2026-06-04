#!/usr/bin/env python3
"""
Build the Chapter 4 evidence pack.

This script aggregates the generated model, RTL, audit, and synthesis artifacts
into one dissertation-facing Markdown report.
"""

from __future__ import annotations

import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS = REPO_ROOT / "results"
OUTPUT = RESULTS / "chapter4_evidence_pack.md"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(title: str) -> list[str]:
    return ["", f"## {title}", ""]


def main() -> int:
    feasibility_rows = read_csv_rows(RESULTS / "feasibility" / "feasibility_summary.csv")
    schedule_rows = read_csv_rows(RESULTS / "schedules" / "schedule_summary.csv")
    synthesis_rows = read_csv_rows(RESULTS / "synthesis" / "rtl_synthesis_summary.csv")

    fixed = next(row for row in schedule_rows if row["strategy"].startswith("fixed"))
    adaptive = next(row for row in schedule_rows if row["strategy"].startswith("adaptive"))

    adaptive_xc7 = next(
        row
        for row in synthesis_rows
        if row["flow"] == "xilinx_xc7" and row["top"] == "adaptive_scrub_controller"
    )

    lines: list[str] = [
        "# Chapter 4 evidence pack",
        "",
        "This report aggregates the reproducible artifacts for the Chapter 4",
        "hardware implementation of the risk-limited adaptive SEC-DED scrubber.",
        "",
        "The controller is treated as the hardware endpoint of the Chapter 3",
        "schedule compiler. It consumes an external `period_index` and does not",
        "compute the radiation-risk model inside RTL.",
        "",
    ]

    lines += section("Claim matrix")

    lines += [
        "| Claim | Evidence artifact |",
        "|---|---|",
        "| Chapter 2 feasibility handoff distinguishes instant-risk, bandwidth-limited, and selectable regions | `results/feasibility/feasibility_summary.md` |",
        "| Chapter 3 schedule compiler emits an implementable exact-risk period-index schedule | `results/schedules/schedule_summary.md` |",
        "| SEC-DED datapath corrects all single-bit errors and detects all double-bit errors in the tested 39-bit codeword space | `results/rtl_replay/secded_exhaustive_report.md` |",
        "| Period scheduler applies external period indices and enters conservative mode when updates are stale | `results/rtl_replay/period_scheduler_report.md` |",
        "| Scrub pass engine performs a complete memory pass, correction writeback, and DUE reporting | `results/rtl_replay/scrub_pass_engine_report.md` |",
        "| Integrated controller combines scheduler and scrub engine without computing the risk model in RTL | `results/rtl_replay/adaptive_controller_report.md` |",
        "| Dangerous-state accounting distinguishes online DUE diagnostics from verification-only SDC audit | `results/rtl_replay/dangerous_state_audit_report.md` |",
        "| Flattened synthesis gives hardware resource estimates for the controller | `results/synthesis/rtl_synthesis_summary.md` |",
        "",
    ]

    lines += section("Feasibility handoff from Chapter 2")

    lines += [
        "| Case | Status | g_D | E_inst | E_residual | E_acc(tau_min) | Slack |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    for row in feasibility_rows:
        lines.append(
            "| {case_name} | {status} | {g_D} | {E_inst} | {E_residual} | "
            "{E_acc_at_tau_min} | {risk_slack_after_tau_min} |".format(**row)
        )

    lines += [
        "",
        "Interpretation: Chapter 4 only proceeds to hardware period scheduling for",
        "cases classified as `scrub_period_selectable`. The other two regions require",
        "architectural changes or a lower achievable minimum period before the",
        "scheduler can satisfy the risk budget.",
        "",
    ]

    lines += section("Implementable schedule result from Chapter 3")

    lines += [
        "| Strategy | Exact E_acc | P_mission | Pass count | Risk utilization | Tau range, s |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for row in schedule_rows:
        lines.append(
            "| {strategy} | {risk_e} | {p_mission} | {pass_count} | "
            "{risk_utilization} | {min_tau_seconds}..{max_tau_seconds} |".format(**row)
        )

    lines += [
        "",
        f"The adaptive exact-risk floor-down schedule reduces full-pass count from "
        f"`{fixed['pass_count']}` to `{adaptive['pass_count']}`, giving a fixed/adaptive "
        f"gain of `{adaptive['gain_fixed_over_strategy']}`.",
        "",
    ]

    lines += section("RTL verification reports")

    for report_name, title in [
        ("secded_exhaustive_report.md", "SEC-DED exhaustive verification"),
        ("period_scheduler_report.md", "Period scheduler verification"),
        ("scrub_pass_engine_report.md", "Scrub pass engine verification"),
        ("adaptive_controller_report.md", "Integrated adaptive controller verification"),
        ("dangerous_state_audit_report.md", "Dangerous-state audit verification"),
    ]:
        report_path = RESULTS / "rtl_replay" / report_name
        report_text = read_text(report_path)

        lines += [
            f"### {title}",
            "",
            f"Source artifact: `results/rtl_replay/{report_name}`.",
            "",
        ]

        # Include report content after its first heading to avoid nested duplicate H1.
        report_lines = report_text.splitlines()
        if report_lines and report_lines[0].startswith("# "):
            report_lines = report_lines[1:]

        lines += report_lines
        lines += [""]

    lines += section("Synthesis/resource estimate")

    lines += [
        "| Flow | Top | Cells | FF estimate | LUT estimate | MUX estimate | Wire bits |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    for row in synthesis_rows:
        lines.append(
            "| {flow} | {top} | {cells} | {ff_estimate} | {lut_estimate} | "
            "{mux_estimate} | {wire_bits} |".format(**row)
        )

    lines += [
        "",
        "For the integrated `adaptive_scrub_controller`, the flattened XC7 estimate is:",
        "",
        f"- cells: `{adaptive_xc7['cells']}`;",
        f"- FF estimate: `{adaptive_xc7['ff_estimate']}`;",
        f"- LUT estimate: `{adaptive_xc7['lut_estimate']}`;",
        f"- MUX estimate: `{adaptive_xc7['mux_estimate']}`.",
        "",
        "This is a synthesis/resource estimate only. It does not establish Fmax",
        "because no target-specific placement and routing has been performed.",
        "",
    ]

    lines += section("Explicit limits")

    lines += [
        "- The RTL controller does not compute `nu(t)`, `g_D`, `E_inst`, or `E_residual`.",
        "- The RTL controller consumes an externally generated `period_index` stream.",
        "- SEC-DED online logic does not guarantee detection of every 3+ bit corruption.",
        "- `final_sdc_words` is a verification-audit metric based on a golden reference.",
        "- The MBU feasibility cases are illustrative unless technology-specific `p_m` and `h_m^(D)` values are supplied.",
        "- Yosys estimates are not timing closure and do not claim maximum frequency.",
        "",
    ]

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print("Chapter 4 evidence pack written to", OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
