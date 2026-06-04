#!/usr/bin/env python3
"""Compile and run the integrated adaptive scrub controller RTL test."""

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

    sim_out = BUILD_DIR / "tb_adaptive_scrub_controller.vvp"
    log_path = RESULT_DIR / "adaptive_controller.log"
    report_path = RESULT_DIR / "adaptive_controller_report.md"

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
        "rtl/scrubber/adaptive_scrub_controller.sv",
        "tb/tb_adaptive_scrub_controller.sv",
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

    match = re.search(
        r"ADAPTIVE_CONTROLLER_SUMMARY passes=(\d+) reads=(\d+) writes=(\d+) "
        r"corrected=(\d+) detected_due=(\d+) safe_entries=(\d+) "
        r"last_pass_cycles=(\d+) failures=(\d+)",
        run_proc.stdout,
    )

    if not match:
        print("Could not parse adaptive controller summary")
        return 1

    passes, reads, writes, corrected, detected_due, safe_entries, last_pass_cycles, failures = map(
        int, match.groups()
    )

    report = f"""# Adaptive scrub controller RTL report

The integrated controller combines the Chapter 3 period scheduler with the
full-pass SEC-DED scrub engine.

| Check | Value |
|---|---:|
| completed passes | {passes} |
| memory reads | {reads} |
| correction writes | {writes} |
| corrected single-bit errors | {corrected} |
| detected uncorrectable errors | {detected_due} |
| safe-mode entries | {safe_entries} |
| last pass duration | {last_pass_cycles} cycles |
| failures | {failures} |

Interpretation:

- The controller consumes an external period index and does not compute the
  radiation-risk model in RTL.
- Full sequential passes are launched by the scheduler.
- Single-bit SEC-DED corruptions are corrected and written back.
- Detected double-bit corruptions are reported as DUE and are not falsely
  repaired.
- Stale external period updates force the conservative safe period.
"""

    report_path.write_text(report, encoding="utf-8")

    print("Adaptive controller RTL report written to", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
