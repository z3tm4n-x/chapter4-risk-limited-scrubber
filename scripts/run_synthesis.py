#!/usr/bin/env python3
"""
Run Yosys synthesis/resource estimation for Chapter 4 RTL blocks.

This is a reproducible engineering-cost artifact. It is not timing closure and
does not claim Fmax. Target-specific Fmax requires place-and-route.
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "synthesis"
LOG_DIR = RESULT_DIR / "logs"


TARGETS = {
    "secded_32_39_encoder": [
        "rtl/ecc/secded_32_39_encoder.sv",
    ],
    "secded_32_39_decoder": [
        "rtl/ecc/secded_32_39_decoder.sv",
    ],
    "period_scheduler": [
        "rtl/scrubber/period_scheduler.sv",
    ],
    "scrub_pass_engine": [
        "rtl/ecc/secded_32_39_decoder.sv",
        "rtl/scrubber/scrub_pass_engine.sv",
    ],
    "adaptive_scrub_controller": [
        "rtl/ecc/secded_32_39_decoder.sv",
        "rtl/scrubber/period_scheduler.sv",
        "rtl/scrubber/scrub_pass_engine.sv",
        "rtl/scrubber/diagnostic_supervisor.sv",
        "rtl/scrubber/adaptive_scrub_controller.sv",
    ],
}


def run_yosys(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["yosys", "-p", script],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def extract_module_stat_block(log_text: str, top: str) -> str:
    pattern = rf"=== {re.escape(top)} ===\n(?P<body>.*?)(?:\n=== |\nEnd of script|\Z)"
    matches = list(re.finditer(pattern, log_text, flags=re.DOTALL))

    if not matches:
        return log_text

    return matches[-1].group("body")


def parse_int_metric(block: str, name: str) -> int:
    match = re.search(rf"{re.escape(name)}:\s+([0-9]+)", block)
    if not match:
        return 0
    return int(match.group(1))


def parse_cell_counts(block: str) -> dict[str, int]:
    counts: dict[str, int] = {}

    capture = False

    for line in block.splitlines():
        if "Number of cells:" in line:
            capture = True
            continue

        if capture:
            stripped = line.strip()
            if not stripped:
                continue

            match = re.match(r"([A-Za-z0-9_.$]+)\s+([0-9]+)$", stripped)
            if match:
                counts[match.group(1)] = int(match.group(2))

    return counts


def estimate_ff_count(cell_counts: dict[str, int]) -> int:
    total = 0

    for cell_name, count in cell_counts.items():
        upper = cell_name.upper()
        if upper.startswith("FD") or "DFF" in upper:
            total += count

    return total


def estimate_lut_count(cell_counts: dict[str, int]) -> int:
    total = 0

    for cell_name, count in cell_counts.items():
        upper = cell_name.upper()
        if upper.startswith("LUT") or "LUT" in upper:
            total += count

    return total


def estimate_mux_count(cell_counts: dict[str, int]) -> int:
    total = 0

    for cell_name, count in cell_counts.items():
        upper = cell_name.upper()
        if "MUX" in upper:
            total += count

    return total


def synthesize_target(top: str, sources: list[str], flow: str) -> dict[str, str]:
    source_cmd = " ".join(sources)

    if flow == "generic_yosys":
        script = (
            f"read_verilog -sv {source_cmd}; "
            f"hierarchy -check -top {top}; "
            "proc; flatten; opt; fsm; opt; memory; opt; techmap; opt; "
            f"stat -top {top}"
        )
    elif flow == "xilinx_xc7":
        script = (
            f"read_verilog -sv {source_cmd}; "
            f"synth_xilinx -flatten -family xc7 -top {top}; "
            f"stat -top {top}"
        )
    else:
        raise ValueError(f"unknown synthesis flow: {flow}")

    proc = run_yosys(script)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{flow}_{top}.log"
    log_path.write_text(proc.stdout, encoding="utf-8")

    if proc.returncode != 0:
        print(proc.stdout)
        raise RuntimeError(f"Yosys failed for {flow}/{top}")

    block = extract_module_stat_block(proc.stdout, top)
    cell_counts = parse_cell_counts(block)

    wires = parse_int_metric(block, "Number of wires")
    wire_bits = parse_int_metric(block, "Number of wire bits")
    cells = parse_int_metric(block, "Number of cells")

    if wires == 0 and wire_bits == 0 and cells == 0:
        raise RuntimeError(
            f"failed to parse non-zero Yosys statistics for {flow}/{top}. "
            f"Check {log_path}"
        )

    return {
        "flow": flow,
        "top": top,
        "wires": str(wires),
        "wire_bits": str(wire_bits),
        "public_wires": str(parse_int_metric(block, "Number of public wires")),
        "public_wire_bits": str(parse_int_metric(block, "Number of public wire bits")),
        "memories": str(parse_int_metric(block, "Number of memories")),
        "memory_bits": str(parse_int_metric(block, "Number of memory bits")),
        "processes": str(parse_int_metric(block, "Number of processes")),
        "cells": str(cells),
        "ff_estimate": str(estimate_ff_count(cell_counts)),
        "lut_estimate": str(estimate_lut_count(cell_counts)),
        "mux_estimate": str(estimate_mux_count(cell_counts)),
        "log_path": str(log_path.relative_to(REPO_ROOT)),
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "flow",
        "top",
        "wires",
        "wire_bits",
        "public_wires",
        "public_wire_bits",
        "memories",
        "memory_bits",
        "processes",
        "cells",
        "ff_estimate",
        "lut_estimate",
        "mux_estimate",
        "log_path",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# RTL synthesis/resource summary",
        "",
        "This report gives reproducible flattened Yosys resource estimates for the Chapter 4 RTL.",
        "",
        "Important limitation: these are synthesis estimates only. They are not",
        "place-and-route timing closure and do not establish Fmax.",
        "",
        "| Flow | Top | Cells | FF estimate | LUT estimate | MUX estimate | Wire bits |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            "| {flow} | {top} | {cells} | {ff_estimate} | {lut_estimate} | "
            "{mux_estimate} | {wire_bits} |".format(**row)
        )

    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- `secded_32_39_encoder` and `secded_32_39_decoder` represent the ECC datapath.",
            "- `period_scheduler` is the hardware endpoint of the Chapter 3 period-index schedule.",
            "- `scrub_pass_engine` performs the full sequential memory pass and correction writeback.",
            "- `adaptive_scrub_controller` is the integrated flattened controller proposed for Chapter 4.",
            "- The Xilinx XC7 flow reports LUT/FF-style estimates but still does not replace",
            "  implementation, placement, routing, and timing analysis.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []

    for flow in ("generic_yosys", "xilinx_xc7"):
        for top, sources in TARGETS.items():
            print(f"Synthesizing {flow}/{top} ...")
            rows.append(synthesize_target(top, sources, flow))

    write_csv(RESULT_DIR / "rtl_synthesis_summary.csv", rows)
    write_markdown(RESULT_DIR / "rtl_synthesis_summary.md", rows)

    print("Synthesis summary written to", RESULT_DIR / "rtl_synthesis_summary.csv")

    for row in rows:
        print(
            f"{row['flow']:14s} {row['top']:28s} "
            f"cells={row['cells']} ff={row['ff_estimate']} "
            f"lut={row['lut_estimate']} mux={row['mux_estimate']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
