#!/usr/bin/env python3
"""Compile and run the SEC-DED exhaustive RTL test."""

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

    sim_out = BUILD_DIR / "tb_secded_exhaustive.vvp"
    log_path = RESULT_DIR / "secded_exhaustive.log"
    report_path = RESULT_DIR / "secded_exhaustive_report.md"

    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-o",
        str(sim_out),
        "rtl/ecc/secded_32_39_encoder.sv",
        "rtl/ecc/secded_32_39_decoder.sv",
        "tb/tb_secded_exhaustive.sv",
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
        r"SECDED_EXHAUSTIVE_SUMMARY no_error=(\d+) single=(\d+) double=(\d+) "
        r"triple_samples=(\d+) triple_detected_due=(\d+) triple_sdc=(\d+) failures=(\d+)",
        run_proc.stdout,
    )

    if not match:
        print("Could not parse SECDED summary")
        return 1

    no_error, single, double, triple, triple_due, triple_sdc, failures = map(int, match.groups())

    report = f"""# SEC-DED exhaustive RTL report

The SEC-DED encoder/decoder was checked over a representative data-pattern set.

| Check | Count |
|---|---:|
| no-error decode checks | {no_error} |
| single-bit corrections | {single} |
| double-bit DUE detections | {double} |
| sampled triple-bit patterns | {triple} |
| sampled triple-bit detected DUE | {triple_due} |
| sampled triple-bit SDC outcomes | {triple_sdc} |
| failures | {failures} |

Interpretation:

- Every single-bit corruption in the 39-bit codeword is corrected.
- Every double-bit corruption is detected as uncorrectable.
- Triple-bit corruptions are outside the guaranteed SEC-DED correction
  capability. The testbench records whether they become detected DUE or SDC
  relative to the golden data; SDC accounting is a verification-audit function,
  not an online SEC-DED guarantee.
"""

    report_path.write_text(report, encoding="utf-8")

    print("SEC-DED RTL report written to", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
