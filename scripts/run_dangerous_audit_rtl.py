#!/usr/bin/env python3
"""Compile and run the dangerous-state audit RTL test."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "rtl_replay"
BUILD_DIR = REPO_ROOT / "generated" / "rtl"


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    sim_out = BUILD_DIR / "tb_dangerous_state_audit.vvp"
    log_path = RESULT_DIR / "dangerous_state_audit.log"
    report_path = RESULT_DIR / "dangerous_state_audit_report.md"

    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-o",
        str(sim_out),
        "rtl/ecc/secded_32_39_encoder.sv",
        "rtl/ecc/secded_32_39_decoder.sv",
        "rtl/scrubber/period_scheduler.sv",
        "rtl/scrubber/scrub_pass_engine.sv",
        "rtl/scrubber/diagnostic_supervisor.sv",
        "rtl/scrubber/adaptive_scrub_controller.sv",
        "tb/tb_dangerous_state_audit.sv",
    ]

    compile_proc = run_cmd(compile_cmd)

    if compile_proc.returncode != 0:
        log_path.write_text(compile_proc.stdout, encoding="utf-8")
        print(compile_proc.stdout)
        return compile_proc.returncode

    run_proc = run_cmd(["vvp", str(sim_out)])
    log_path.write_text(compile_proc.stdout + run_proc.stdout, encoding="utf-8")
    print(run_proc.stdout)

    if run_proc.returncode != 0:
        return run_proc.returncode

    pattern = (
        r"DANGEROUS_AUDIT_SUMMARY passes=(\d+) reads=(\d+) writes=(\d+) "
        r"corrected_events=(\d+) detected_due_events=(\d+) "
        r"final_uncorrectable_words=(\d+) final_sdc_words=(\d+) "
        r"final_dangerous_words=(\d+) failures=(\d+)"
    )

    match = re.search(pattern, run_proc.stdout)

    if not match:
        print("Could not parse dangerous audit summary")
        return 1

    (
        passes,
        reads,
        writes,
        corrected_events,
        detected_due_events,
        final_uncorrectable,
        final_sdc,
        final_dangerous,
        failures,
    ) = map(int, match.groups())

    report = f"""# Dangerous-state audit RTL report

The integrated controller was run against a memory containing a correctable
single-bit corruption, a detected double-bit DUE, and a triple-bit corruption
outside the SEC-DED correction guarantee.

| Metric | Value |
|---|---:|
| completed passes | {passes} |
| memory reads | {reads} |
| correction writes | {writes} |
| online corrected events | {corrected_events} |
| online detected DUE events | {detected_due_events} |
| final uncorrectable words | {final_uncorrectable} |
| final SDC words | {final_sdc} |
| final dangerous words | {final_dangerous} |
| failures | {failures} |

Interpretation:

- Single-bit accumulated errors are corrected by the scrub pass.
- Detected double-bit states are reported as DUE but are not repaired.
- A triple-bit state can be outside the SEC-DED guarantee and become SDC.
- `final_sdc_words` is obtained by a verification-only golden-reference audit,
  not by an online SEC-DED hardware flag.
- This is the Chapter 4 distinction between online diagnostics and the broader
  dangerous-state class used in Chapter 2.
"""

    report_path.write_text(report, encoding="utf-8")

    print("Dangerous-state audit RTL report written to", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
