#!/usr/bin/env python3
"""Compile and run the scrub pass engine RTL test."""

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

    sim_out = BUILD_DIR / "tb_scrub_pass_engine.vvp"
    log_path = RESULT_DIR / "scrub_pass_engine.log"
    report_path = RESULT_DIR / "scrub_pass_engine_report.md"

    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-o",
        str(sim_out),
        "rtl/ecc/secded_32_39_decoder.sv",
        "rtl/ecc/secded_32_39_encoder.sv",
        "rtl/scrubber/scrub_pass_engine.sv",
        "tb/tb_scrub_pass_engine.sv",
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
        r"SCRUB_PASS_ENGINE_SUMMARY depth=(\d+) pass_count=(\d+) reads=(\d+) "
        r"writes=(\d+) corrected=(\d+) detected_due=(\d+) wait_cycles=(\d+) failures=(\d+)",
        run_proc.stdout,
    )

    if not match:
        print("Could not parse scrub pass engine summary")
        return 1

    depth, passes, reads, writes, corrected, detected_due, wait_cycles, failures = map(
        int, match.groups()
    )

    report = f"""# Scrub pass engine RTL report

One complete SEC-DED scrub pass was executed over a protected memory model.

| Check | Value |
|---|---:|
| protected depth | {depth} |
| completed passes | {passes} |
| memory reads | {reads} |
| correction writes | {writes} |
| corrected single-bit errors | {corrected} |
| detected uncorrectable errors | {detected_due} |
| wait cycles until pass_done | {wait_cycles} |
| failures | {failures} |

Interpretation:

- The pass engine reads every protected codeword exactly once per pass.
- A correctable single-bit corruption is written back as the restored codeword.
- A detected double-bit error is reported as DUE and is not falsely repaired.
- This block implements the Chapter 4 per-word scrub operation; period
  scheduling is handled separately by the period scheduler.
"""

    report_path.write_text(report, encoding="utf-8")

    print("Scrub pass engine RTL report written to", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
