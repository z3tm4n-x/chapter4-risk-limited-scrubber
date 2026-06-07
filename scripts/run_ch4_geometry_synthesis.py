#!/usr/bin/env python3
"""Run Chapter 4 synthesis at dissertation memory geometry.

This complements the default small-test-geometry synthesis report. It
parameterizes key scrub-controller tops with the dissertation codeword count
and address width while keeping the diagnostic DUE tracker bounded.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_synthesis import (  # noqa: E402
    REPO_ROOT,
    extract_module_stat_block,
    estimate_ff_count,
    estimate_lut_count,
    estimate_mux_count,
    parse_cell_counts,
    parse_int_metric,
    run_yosys,
)


RESULT_DIR = REPO_ROOT / "results" / "synthesis"
LOG_DIR = RESULT_DIR / "logs"

OUT_CSV = RESULT_DIR / "ch4_geometry_synthesis_summary.csv"
OUT_MD = RESULT_DIR / "ch4_geometry_synthesis_summary.md"
OUT_JSON = RESULT_DIR / "ch4_geometry_synthesis_summary.json"

ADDR_WIDTH = 21
DEPTH = 1_935_832
PROTECTED_BITS = DEPTH * 39
DUE_TRACKER_ENTRIES = 16

PERIOD_TICKS = {
    "PERIOD0_CYCLES": 1,
    "PERIOD1_CYCLES": 2,
    "PERIOD2_CYCLES": 5,
    "PERIOD3_CYCLES": 10,
    "PERIOD4_CYCLES": 30,
    "PERIOD5_CYCLES": 60,
    "PERIOD6_CYCLES": 120,
    "PERIOD7_CYCLES": 300,
    "PERIOD8_CYCLES": 600,
    "PERIOD9_CYCLES": 1200,
    "PERIOD10_CYCLES": 1800,
    "PERIOD11_CYCLES": 3600,
}


TARGETS = [
    {
        "run_key": "period_scheduler_ch3_period_table",
        "top": "period_scheduler",
        "sources": ["rtl/scrubber/period_scheduler.sv"],
        "chparams": {
            "PERIOD_INDEX_WIDTH": 4,
            **PERIOD_TICKS,
            "SAFE_PERIOD_INDEX": 0,
            "MAX_CONTROL_AGE_CYCLES": 7200,
        },
    },
    {
        "run_key": "scrub_pass_engine_ch4_geometry",
        "top": "scrub_pass_engine",
        "sources": [
            "rtl/ecc/secded_32_39_decoder.sv",
            "rtl/scrubber/scrub_pass_engine.sv",
        ],
        "chparams": {
            "ADDR_WIDTH": ADDR_WIDTH,
            "DEPTH": DEPTH,
        },
    },
    {
        "run_key": "diagnostic_supervisor_ch4_geometry",
        "top": "diagnostic_supervisor",
        "sources": ["rtl/scrubber/diagnostic_supervisor.sv"],
        "chparams": {
            "ADDR_WIDTH": ADDR_WIDTH,
            "DEPTH": DEPTH,
            "DUE_TRACKER_ENTRIES": DUE_TRACKER_ENTRIES,
        },
    },
    {
        "run_key": "adaptive_scrub_controller_ch4_geometry",
        "top": "adaptive_scrub_controller",
        "sources": [
            "rtl/ecc/secded_32_39_decoder.sv",
            "rtl/scrubber/period_scheduler.sv",
            "rtl/scrubber/scrub_pass_engine.sv",
            "rtl/scrubber/diagnostic_supervisor.sv",
            "rtl/scrubber/adaptive_scrub_controller.sv",
        ],
        "chparams": {
            "ADDR_WIDTH": ADDR_WIDTH,
            "DEPTH": DEPTH,
            "PERIOD_INDEX_WIDTH": 4,
            **PERIOD_TICKS,
            "SAFE_PERIOD_INDEX": 0,
            "MAX_CONTROL_AGE_CYCLES": 7200,
            "DIAG_DUE_TRACKER_ENTRIES": DUE_TRACKER_ENTRIES,
        },
    },
    {
        "run_key": "measured_error_scrub_controller_ch4_geometry",
        "top": "measured_error_scrub_controller",
        "sources": [
            "rtl/ecc/secded_32_39_decoder.sv",
            "rtl/scrubber/period_scheduler.sv",
            "rtl/scrubber/scrub_pass_engine.sv",
            "rtl/scrubber/diagnostic_supervisor.sv",
            "rtl/scrubber/adaptive_scrub_controller.sv",
            "rtl/scrubber/measured_error_period_estimator.sv",
            "rtl/scrubber/measured_error_scrub_controller.sv",
        ],
        "chparams": {
            "ADDR_WIDTH": ADDR_WIDTH,
            "DEPTH": DEPTH,
            "PERIOD_INDEX_WIDTH": 4,
            **PERIOD_TICKS,
            "SAFE_PERIOD_INDEX": 0,
            "MAX_CONTROL_AGE_CYCLES": 7200,
            "DIAG_DUE_TRACKER_ENTRIES": DUE_TRACKER_ENTRIES,
        },
    },
]


def chparam_script(top: str, chparams: dict[str, int]) -> str:
    return " ".join(f"chparam -set {name} {value} {top};" for name, value in chparams.items())


def synthesize_target(target: dict[str, object], flow: str) -> dict[str, str]:
    top = str(target["top"])
    run_key = str(target["run_key"])
    sources = target["sources"]
    chparams = target["chparams"]

    source_cmd = " ".join(str(src) for src in sources)
    chparam_cmd = chparam_script(top, chparams)  # type: ignore[arg-type]

    if flow == "generic_yosys":
        script = (
            f"read_verilog -sv {source_cmd}; "
            f"{chparam_cmd} "
            f"hierarchy -check -top {top}; "
            "proc; flatten; opt; fsm; opt; memory; opt; techmap; opt; "
            f"stat -top {top}"
        )
    elif flow == "xilinx_xc7":
        script = (
            f"read_verilog -sv {source_cmd}; "
            f"{chparam_cmd} "
            f"synth_xilinx -flatten -family xc7 -top {top}; "
            f"stat -top {top}"
        )
    else:
        raise ValueError(f"unknown flow: {flow}")

    proc = run_yosys(script)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{flow}_{run_key}.log"
    log_path.write_text(proc.stdout, encoding="utf-8")

    if proc.returncode != 0:
        print(proc.stdout)
        raise RuntimeError(f"Yosys failed for {flow}/{run_key}; see {log_path}")

    block = extract_module_stat_block(proc.stdout, top)
    cell_counts = parse_cell_counts(block)

    wires = parse_int_metric(block, "Number of wires")
    wire_bits = parse_int_metric(block, "Number of wire bits")
    cells = parse_int_metric(block, "Number of cells")

    if wires == 0 and wire_bits == 0 and cells == 0:
        raise RuntimeError(f"failed to parse statistics for {flow}/{run_key}; see {log_path}")

    return {
        "run_key": run_key,
        "flow": flow,
        "top": top,
        "addr_width": str(ADDR_WIDTH),
        "depth": str(DEPTH),
        "protected_bits": str(PROTECTED_BITS),
        "due_tracker_entries": str(DUE_TRACKER_ENTRIES),
        "period_ticks": " ".join(str(PERIOD_TICKS[f"PERIOD{i}_CYCLES"]) for i in range(12)),
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
        "chparams": ";".join(f"{k}={v}" for k, v in chparams.items()),  # type: ignore[union-attr]
    }


def write_csv(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "run_key",
        "flow",
        "top",
        "addr_width",
        "depth",
        "protected_bits",
        "due_tracker_entries",
        "period_ticks",
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
        "chparams",
    ]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str]]) -> None:
    lines = [
        "# Chapter 4 dissertation-geometry synthesis summary",
        "",
        "This report complements the default small-test-geometry synthesis summary.",
        "The selected RTL tops are parameterized with the dissertation memory geometry",
        f"`ADDR_WIDTH={ADDR_WIDTH}`, `DEPTH={DEPTH}`, and `{PROTECTED_BITS}` protected SEC-DED bits.",
        "",
        "Important limitation: this is still a Yosys synthesis estimate, not Vivado",
        "place-and-route timing closure and not an Fmax claim.",
        "",
        "The diagnostic persistent-DUE state is bounded by",
        f"`DUE_TRACKER_ENTRIES={DUE_TRACKER_ENTRIES}` and is not a full depth-wide bitmap.",
        "",
        "| Flow | Run | Top | Cells | FF estimate | LUT estimate | MUX estimate | Wire bits |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            "| {flow} | {run_key} | {top} | {cells} | {ff_estimate} | {lut_estimate} | "
            "{mux_estimate} | {wire_bits} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- These rows use the Chapter 4 memory address width and codeword count.",
            "- The protected memory array itself is external to these controllers; the",
            "  synthesis estimate covers the controller/address/ECC/diagnostic logic.",
            "- The bounded DUE tracker prevents diagnostic state from scaling as one",
            "  flip-flop per protected codeword.",
            "- Vivado implementation can later provide device-specific utilization,",
            "  routing, and timing closure evidence.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_json(rows: list[dict[str, str]]) -> None:
    OUT_JSON.write_text(
        json.dumps(
            {
                "generated_by": "run_ch4_geometry_synthesis.py",
                "addr_width": ADDR_WIDTH,
                "depth": DEPTH,
                "protected_bits": PROTECTED_BITS,
                "due_tracker_entries": DUE_TRACKER_ENTRIES,
                "period_ticks": [PERIOD_TICKS[f"PERIOD{i}_CYCLES"] for i in range(12)],
                "rows": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> int:
    rows: list[dict[str, str]] = []

    for flow in ("generic_yosys", "xilinx_xc7"):
        for target in TARGETS:
            print(f"Synthesizing {flow}/{target['run_key']} ...")
            row = synthesize_target(target, flow)
            rows.append(row)
            print(
                f"{flow:14s} {target['run_key']:46s} "
                f"cells={row['cells']} ff={row['ff_estimate']} "
                f"lut={row['lut_estimate']} mux={row['mux_estimate']}"
            )

    write_csv(rows)
    write_markdown(rows)
    write_json(rows)

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
