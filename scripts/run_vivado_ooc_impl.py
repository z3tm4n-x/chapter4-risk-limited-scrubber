#!/usr/bin/env python3
"""Run Vivado out-of-context implementation sweep for Chapter 4 RTL.

The script runs synth/opt/place/route for selected RTL tops on one AMD/Xilinx
FPGA part. It is a commercial-FPGA demonstrator, not a radiation-qualified
target implementation.

Outputs:
  results/vivado_ooc/vivado_ooc_detail.csv
  results/vivado_ooc/vivado_ooc_summary.csv
  results/vivado_ooc/vivado_ooc_report.md
  results/vivado_ooc/vivado_ooc_summary.json
  results/vivado_ooc/runs/<top>_<freq>/*.rpt
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "results" / "vivado_ooc"
RUN_DIR = OUT_DIR / "runs"

TCL_SCRIPT = REPO_ROOT / "scripts" / "vivado_ooc_impl.tcl"

DEFAULT_TOPS = [
    "period_scheduler",
    "scrub_pass_engine",
    "adaptive_scrub_controller",
    "measured_error_scrub_controller",
]

DEFAULT_PERIODS_NS = [10.0, 7.5, 5.0, 4.0, 3.333]

ADDR_WIDTH = 21
DEPTH = 1_935_832
CODEWORD_BITS = 39
PROTECTED_BITS = DEPTH * CODEWORD_BITS
PIPELINE_OVERHEAD_CYCLES = 4
PASS_CYCLES = DEPTH + PIPELINE_OVERHEAD_CYCLES
TAU_MIN_SECONDS = 1.0
DUE_TRACKER_ENTRIES = 16
MAX_CONTROL_AGE_CYCLES = 7200


def run_cmd(cmd: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(proc.stdout, encoding="utf-8")
    return proc.returncode


def parse_ooc_result(log_text: str) -> dict[str, str]:
    result_re = re.compile(
        r"OOC_RESULT\s+top=(?P<top>\S+)\s+part=(?P<part>\S+)\s+"
        r"period_ns=(?P<period_ns>\S+)\s+wns_ns=(?P<wns_ns>\S+)"
    )
    match = result_re.search(log_text)
    if not match:
        return {}
    return match.groupdict()


def parse_utilization(path: Path) -> dict[str, str]:
    data = {
        "lut": "",
        "ff": "",
        "bram": "",
        "dsp": "",
    }

    if not path.exists():
        return data

    text = path.read_text(encoding="utf-8", errors="ignore")

    patterns = {
        "lut": r"\|\s*Slice LUTs\s*\|\s*([0-9]+)\s*\|",
        "ff": r"\|\s*Slice Registers\s*\|\s*([0-9]+)\s*\|",
        "bram": r"\|\s*Block RAM Tile\s*\|\s*([0-9]+)\s*\|",
        "dsp": r"\|\s*DSPs\s*\|\s*([0-9]+)\s*\|",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            data[key] = match.group(1)

    return data


def parse_power(path: Path) -> str:
    if not path.exists():
        return ""

    text = path.read_text(encoding="utf-8", errors="ignore")

    patterns = [
        r"Total On-Chip Power \(W\)\s*\|\s*([0-9.]+)",
        r"\|\s*Total On-Chip Power \(W\)\s*\|\s*([0-9.]+)\s*\|",
        r"Total On-Chip Power:\s*([0-9.]+)\s*W",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return ""


def float_or_nan(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return math.nan


def timing_met(wns_ns: str, return_code: int) -> bool:
    wns = float_or_nan(wns_ns)
    return return_code == 0 and not math.isnan(wns) and wns >= 0.0


def mhz_from_period(period_ns: float) -> float:
    return 1000.0 / period_ns


def tau_metrics(best_mhz: float, mem_words_per_sec: float) -> dict[str, str]:
    if best_mhz <= 0:
        return {
            "effective_words_per_sec": "",
            "pass_time_seconds": "",
            "tau_min_margin": "",
        }

    core_words_per_sec = best_mhz * 1e6
    effective = min(core_words_per_sec, mem_words_per_sec)
    pass_time = PASS_CYCLES / effective
    margin = TAU_MIN_SECONDS / pass_time

    return {
        "effective_words_per_sec": f"{effective:.12g}",
        "pass_time_seconds": f"{pass_time:.12g}",
        "tau_min_margin": f"{margin:.12g}",
    }


def run_one(
    vivado: str,
    part: str,
    top: str,
    period_ns: float,
) -> dict[str, str]:
    freq_mhz = mhz_from_period(period_ns)
    run_key = f"{top}_{freq_mhz:.3f}MHz".replace(".", "p")
    out_dir = RUN_DIR / run_key
    log_path = out_dir / f"{top}.log"

    cmd = [
        vivado,
        "-mode",
        "batch",
        "-nojournal",
        "-nolog",
        "-notrace",
        "-source",
        str(TCL_SCRIPT),
        "-tclargs",
        top,
        part,
        f"{period_ns:.6f}",
        str(out_dir),
        str(ADDR_WIDTH),
        str(DEPTH),
        str(DUE_TRACKER_ENTRIES),
        str(MAX_CONTROL_AGE_CYCLES),
    ]

    print(f"Vivado OOC: top={top} part={part} period={period_ns:.6f} ns ({freq_mhz:.3f} MHz)")
    rc = run_cmd(cmd, log_path)
    log_text = log_path.read_text(encoding="utf-8", errors="ignore")

    ooc = parse_ooc_result(log_text)

    util_path = out_dir / f"util_{top}.rpt"
    timing_path = out_dir / f"timing_{top}.rpt"
    power_path = out_dir / f"power_{top}.rpt"

    util = parse_utilization(util_path)
    power_w = parse_power(power_path)

    wns_ns = ooc.get("wns_ns", "")
    met = timing_met(wns_ns, rc)

    row = {
        "run_key": run_key,
        "top": top,
        "part": part,
        "period_ns": f"{period_ns:.6f}",
        "target_mhz": f"{freq_mhz:.6f}",
        "return_code": str(rc),
        "timing_met": str(met).lower(),
        "wns_ns": wns_ns,
        "lut": util["lut"],
        "ff": util["ff"],
        "bram": util["bram"],
        "dsp": util["dsp"],
        "power_w": power_w,
        "log_path": str(log_path.relative_to(REPO_ROOT)),
        "util_path": str(util_path.relative_to(REPO_ROOT)) if util_path.exists() else "",
        "timing_path": str(timing_path.relative_to(REPO_ROOT)) if timing_path.exists() else "",
        "power_path": str(power_path.relative_to(REPO_ROOT)) if power_path.exists() else "",
    }

    print(
        "  -> rc={return_code} met={timing_met} wns={wns_ns} "
        "lut={lut} ff={ff} bram={bram} dsp={dsp}".format(**row)
    )

    return row


def summarize(rows: list[dict[str, str]], tops: list[str], mem_words_per_sec: float) -> list[dict[str, str]]:
    summary: list[dict[str, str]] = []

    for top in tops:
        top_rows = [row for row in rows if row["top"] == top]
        passing = [row for row in top_rows if row["timing_met"] == "true"]

        if passing:
            best = max(passing, key=lambda row: float(row["target_mhz"]))
            best_mhz = float(best["target_mhz"])
            next_failing_candidates = [
                row for row in top_rows
                if row["timing_met"] != "true" and float(row["target_mhz"]) > best_mhz
            ]
            next_failing = min(next_failing_candidates, key=lambda row: float(row["target_mhz"])) if next_failing_candidates else None

            tau = tau_metrics(best_mhz, mem_words_per_sec)

            row = {
                "top": top,
                "part": best["part"],
                "highest_passing_mhz": f"{best_mhz:.6f}",
                "highest_passing_period_ns": best["period_ns"],
                "wns_at_highest_passing_ns": best["wns_ns"],
                "lut_at_highest_passing": best["lut"],
                "ff_at_highest_passing": best["ff"],
                "bram_at_highest_passing": best["bram"],
                "dsp_at_highest_passing": best["dsp"],
                "power_w_at_highest_passing": best["power_w"],
                "next_failing_mhz": next_failing["target_mhz"] if next_failing else "",
                "next_failing_wns_ns": next_failing["wns_ns"] if next_failing else "",
                **tau,
            }
        else:
            row = {
                "top": top,
                "part": top_rows[0]["part"] if top_rows else "",
                "highest_passing_mhz": "",
                "highest_passing_period_ns": "",
                "wns_at_highest_passing_ns": "",
                "lut_at_highest_passing": "",
                "ff_at_highest_passing": "",
                "bram_at_highest_passing": "",
                "dsp_at_highest_passing": "",
                "power_w_at_highest_passing": "",
                "next_failing_mhz": "",
                "next_failing_wns_ns": "",
                "effective_words_per_sec": "",
                "pass_time_seconds": "",
                "tau_min_margin": "",
            }

        summary.append(row)

    return summary


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    path: Path,
    detail_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    part: str,
    mem_words_per_sec: float,
) -> None:
    lines = [
        "# Vivado out-of-context implementation report",
        "",
        "This report implements selected Chapter 4 RTL tops on a commercial",
        "AMD/Xilinx FPGA in out-of-context mode.",
        "",
        "It is a device-specific implementation/timing demonstrator. It is not a",
        "claim of radiation-qualified deployment and does not replace a final",
        "platform-specific FPGA or ASIC implementation flow.",
        "",
        "## Configuration",
        "",
        f"- FPGA part: `{part}`",
        f"- Address width: `{ADDR_WIDTH}`",
        f"- Codeword count: `{DEPTH}`",
        f"- Protected SEC-DED bits: `{PROTECTED_BITS}`",
        f"- Bounded DUE tracker entries: `{DUE_TRACKER_ENTRIES}`",
        f"- Memory service-rate assumption: `{mem_words_per_sec:.12g}` words/s",
        f"- Tau-min target: `{TAU_MIN_SECONDS}` s",
        "",
        "The pass-time estimate uses:",
        "",
        "`pass_time = pass_cycles / min(Fmax_core, memory_service_rate)`",
        "",
        f"with `pass_cycles = {PASS_CYCLES}`.",
        "",
        "## Highest passing frequency per top",
        "",
        "| Top | Highest passing MHz | WNS, ns | LUT | FF | BRAM | DSP | Power, W | pass time, s | tau-min margin |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in summary_rows:
        lines.append(
            "| {top} | {highest_passing_mhz} | {wns_at_highest_passing_ns} | "
            "{lut_at_highest_passing} | {ff_at_highest_passing} | "
            "{bram_at_highest_passing} | {dsp_at_highest_passing} | "
            "{power_w_at_highest_passing} | {pass_time_seconds} | "
            "{tau_min_margin} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Sweep detail",
            "",
            "| Top | Target MHz | Period, ns | Timing met | WNS, ns | LUT | FF | BRAM | DSP |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for row in detail_rows:
        lines.append(
            "| {top} | {target_mhz} | {period_ns} | {timing_met} | {wns_ns} | "
            "{lut} | {ff} | {bram} | {dsp} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Out-of-context mode is used because the scrub-control core connects to",
            "  an external memory subsystem and does not require package pin assignment",
            "  for this core-level timing check.",
            "- Timing closure here demonstrates the commercial-FPGA implementation",
            "  feasibility of the core at the reported clock constraints.",
            "- The protected memory array itself is external to these controller tops.",
            "- Radiation-qualified deployment would require migration to the selected",
            "  qualified platform and its tool flow.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", default="xc7a200tfbg484-2")
    parser.add_argument("--vivado", default=str(Path.home() / "bin" / "vivado-wsl"))
    parser.add_argument("--tops", nargs="+", default=DEFAULT_TOPS)
    parser.add_argument("--periods-ns", nargs="+", type=float, default=DEFAULT_PERIODS_NS)
    parser.add_argument("--mem-words-per-sec", type=float, default=100_000_000.0)
    args = parser.parse_args()

    if not TCL_SCRIPT.exists():
        raise SystemExit(f"Missing Tcl script: {TCL_SCRIPT}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    detail_rows: list[dict[str, str]] = []

    for top in args.tops:
        for period_ns in args.periods_ns:
            detail_rows.append(run_one(args.vivado, args.part, top, period_ns))

    summary_rows = summarize(detail_rows, args.tops, args.mem_words_per_sec)

    detail_csv = OUT_DIR / "vivado_ooc_detail.csv"
    summary_csv = OUT_DIR / "vivado_ooc_summary.csv"
    report_md = OUT_DIR / "vivado_ooc_report.md"
    summary_json = OUT_DIR / "vivado_ooc_summary.json"

    write_csv(detail_csv, detail_rows)
    write_csv(summary_csv, summary_rows)
    write_report(report_md, detail_rows, summary_rows, args.part, args.mem_words_per_sec)

    summary_json.write_text(
        json.dumps(
            {
                "generated_by": "run_vivado_ooc_impl.py",
                "part": args.part,
                "addr_width": ADDR_WIDTH,
                "depth": DEPTH,
                "protected_bits": PROTECTED_BITS,
                "pass_cycles": PASS_CYCLES,
                "tau_min_seconds": TAU_MIN_SECONDS,
                "mem_words_per_sec": args.mem_words_per_sec,
                "periods_ns": args.periods_ns,
                "detail": detail_rows,
                "summary": summary_rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("Wrote", detail_csv)
    print("Wrote", summary_csv)
    print("Wrote", report_md)
    print("Wrote", summary_json)

    print()
    print("=== Vivado OOC summary ===")
    with summary_csv.open("r", encoding="utf-8") as file:
        print(file.read())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
