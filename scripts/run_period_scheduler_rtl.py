#!/usr/bin/env python3
"""Compile and run the period scheduler RTL test."""

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

    sim_out = BUILD_DIR / "tb_period_scheduler.vvp"
    log_path = RESULT_DIR / "period_scheduler.log"
    report_path = RESULT_DIR / "period_scheduler_report.md"

    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-o",
        str(sim_out),
        "rtl/scrubber/period_scheduler.sv",
        "tb/tb_period_scheduler.sv",
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
        r"PERIOD_SCHEDULER_SUMMARY measured_interval=(\d+) "
        r"last_pass_cycles=(\d+) safe_entries=(\d+) failures=(\d+)",
        run_proc.stdout,
    )

    if not match:
        print("Could not parse period scheduler summary")
        return 1

    measured_interval, last_pass_cycles, safe_entries, failures = map(int, match.groups())

    report = f"""# Period scheduler RTL report

The scheduler was checked as the hardware endpoint of the Chapter 3
implementable schedule.

| Check | Value |
|---|---:|
| measured pass_start interval | {measured_interval} cycles |
| last pass duration | {last_pass_cycles} cycles |
| safe-mode entries | {safe_entries} |
| failures | {failures} |

Interpretation:

- The selected period index controls the interval between full-pass starts.
- The scheduler compensates for the pass duration when computing the idle wait.
- If control updates become stale, the safe conservative period index is applied.
- A fresh period update exits safe mode.
"""

    report_path.write_text(report, encoding="utf-8")

    print("Period scheduler RTL report written to", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
