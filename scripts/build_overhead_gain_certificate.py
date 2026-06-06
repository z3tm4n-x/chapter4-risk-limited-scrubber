#!/usr/bin/env python3
"""Build Chapter 4 overhead/gain certificate.

This artifact combines:
  - Chapter 3 five-year fixed/current/delayed schedule results;
  - RTL synthesis estimates for the external-period endpoint;
  - RTL synthesis estimates for diagnostic and measured-error fallback logic.

The point is to put benefit and hardware cost in one table.
"""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SCHEDULE_SUMMARY = REPO_ROOT / "results" / "schedules" / "ch3_five_year_summary.csv"
SYNTHESIS_SUMMARY = REPO_ROOT / "results" / "synthesis" / "rtl_synthesis_summary.csv"
MODEL_RTL_CERT = REPO_ROOT / "results" / "chapter4_model_rtl_certificate.json"

OUT_CSV = REPO_ROOT / "results" / "chapter4_overhead_gain_certificate.csv"
OUT_MD = REPO_ROOT / "results" / "chapter4_overhead_gain_certificate.md"
OUT_JSON = REPO_ROOT / "results" / "chapter4_overhead_gain_certificate.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


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


def row_by_key(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    for row in rows:
        if row[key] == value:
            return row
    raise KeyError(f"missing row where {key}={value}")


def synthesis_row(rows: list[dict[str, str]], flow: str, top: str) -> dict[str, str]:
    for row in rows:
        if row["flow"] == flow and row["top"] == top:
            return row
    raise KeyError(f"missing synthesis row {flow}/{top}")


def int_field(row: dict[str, str], field: str) -> int:
    return int(row[field])


def float_field(row: dict[str, str], field: str) -> float:
    return float(row[field])


def pct_delta(delta: int, base: int) -> str:
    if base == 0:
        return ""
    return f"{100.0 * delta / base:.6g}"


def main() -> int:
    schedule_rows = read_csv(SCHEDULE_SUMMARY)
    synthesis_rows = read_csv(SYNTHESIS_SUMMARY)

    fixed = row_by_key(schedule_rows, "strategy_key", "fixed")
    current = row_by_key(schedule_rows, "strategy_key", "current")
    delayed = row_by_key(schedule_rows, "strategy_key", "delayed_1h")

    xc7_adaptive = synthesis_row(synthesis_rows, "xilinx_xc7", "adaptive_scrub_controller")
    xc7_measured = synthesis_row(synthesis_rows, "xilinx_xc7", "measured_error_scrub_controller")
    xc7_estimator = synthesis_row(synthesis_rows, "xilinx_xc7", "measured_error_period_estimator")
    xc7_diag = synthesis_row(synthesis_rows, "xilinx_xc7", "diagnostic_supervisor")
    xc7_period = synthesis_row(synthesis_rows, "xilinx_xc7", "period_scheduler")
    xc7_engine = synthesis_row(synthesis_rows, "xilinx_xc7", "scrub_pass_engine")
    xc7_decoder = synthesis_row(synthesis_rows, "xilinx_xc7", "secded_32_39_decoder")
    xc7_encoder = synthesis_row(synthesis_rows, "xilinx_xc7", "secded_32_39_encoder")

    adaptive_lut = int_field(xc7_adaptive, "lut_estimate")
    adaptive_ff = int_field(xc7_adaptive, "ff_estimate")
    measured_lut = int_field(xc7_measured, "lut_estimate")
    measured_ff = int_field(xc7_measured, "ff_estimate")

    measured_delta_lut = measured_lut - adaptive_lut
    measured_delta_ff = measured_ff - adaptive_ff

    fixed_passes = float_field(fixed, "pass_count")
    current_passes = float_field(current, "pass_count")
    delayed_passes = float_field(delayed, "pass_count")

    current_gain = fixed_passes / current_passes
    delayed_gain = fixed_passes / delayed_passes

    pass_reduction_current = 1.0 - current_passes / fixed_passes
    pass_reduction_delayed = 1.0 - delayed_passes / fixed_passes

    rows = [
        {
            "item": "external_current_adaptive_schedule",
            "description": "Chapter 3 current exact-risk schedule executed by external-period RTL endpoint",
            "top": "adaptive_scrub_controller",
            "flow": "xilinx_xc7",
            "lut": str(adaptive_lut),
            "ff": str(adaptive_ff),
            "cells": xc7_adaptive["cells"],
            "pass_count": current["pass_count"],
            "fixed_over_item_gain": f"{current_gain:.12g}",
            "pass_reduction_vs_fixed": f"{pass_reduction_current:.12g}",
            "p_mission": current["p_mission"],
            "risk_utilization": current["risk_utilization"],
            "delta_lut_vs_external": "0",
            "delta_ff_vs_external": "0",
            "delta_lut_percent_vs_external": "0",
            "delta_ff_percent_vs_external": "0",
        },
        {
            "item": "external_delayed_1h_adaptive_schedule",
            "description": "Chapter 3 one-hour delayed exact-risk schedule executed by same external-period endpoint",
            "top": "adaptive_scrub_controller",
            "flow": "xilinx_xc7",
            "lut": str(adaptive_lut),
            "ff": str(adaptive_ff),
            "cells": xc7_adaptive["cells"],
            "pass_count": delayed["pass_count"],
            "fixed_over_item_gain": f"{delayed_gain:.12g}",
            "pass_reduction_vs_fixed": f"{pass_reduction_delayed:.12g}",
            "p_mission": delayed["p_mission"],
            "risk_utilization": delayed["risk_utilization"],
            "delta_lut_vs_external": "0",
            "delta_ff_vs_external": "0",
            "delta_lut_percent_vs_external": "0",
            "delta_ff_percent_vs_external": "0",
        },
        {
            "item": "measured_error_onboard_fallback",
            "description": "Integrated onboard fallback: SEC-DED observations drive period_index autonomously",
            "top": "measured_error_scrub_controller",
            "flow": "xilinx_xc7",
            "lut": str(measured_lut),
            "ff": str(measured_ff),
            "cells": xc7_measured["cells"],
            "pass_count": "",
            "fixed_over_item_gain": "",
            "pass_reduction_vs_fixed": "",
            "p_mission": "",
            "risk_utilization": "",
            "delta_lut_vs_external": str(measured_delta_lut),
            "delta_ff_vs_external": str(measured_delta_ff),
            "delta_lut_percent_vs_external": pct_delta(measured_delta_lut, adaptive_lut),
            "delta_ff_percent_vs_external": pct_delta(measured_delta_ff, adaptive_ff),
        },
        {
            "item": "measured_error_estimator_only",
            "description": "Standalone measured-error period estimator",
            "top": "measured_error_period_estimator",
            "flow": "xilinx_xc7",
            "lut": xc7_estimator["lut_estimate"],
            "ff": xc7_estimator["ff_estimate"],
            "cells": xc7_estimator["cells"],
            "pass_count": "",
            "fixed_over_item_gain": "",
            "pass_reduction_vs_fixed": "",
            "p_mission": "",
            "risk_utilization": "",
            "delta_lut_vs_external": "",
            "delta_ff_vs_external": "",
            "delta_lut_percent_vs_external": "",
            "delta_ff_percent_vs_external": "",
        },
        {
            "item": "diagnostic_supervisor_only",
            "description": "Standalone diagnostic supervisor for alert, persistent-DUE, and out-of-envelope flags",
            "top": "diagnostic_supervisor",
            "flow": "xilinx_xc7",
            "lut": xc7_diag["lut_estimate"],
            "ff": xc7_diag["ff_estimate"],
            "cells": xc7_diag["cells"],
            "pass_count": "",
            "fixed_over_item_gain": "",
            "pass_reduction_vs_fixed": "",
            "p_mission": "",
            "risk_utilization": "",
            "delta_lut_vs_external": "",
            "delta_ff_vs_external": "",
            "delta_lut_percent_vs_external": "",
            "delta_ff_percent_vs_external": "",
        },
    ]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "item",
        "description",
        "top",
        "flow",
        "lut",
        "ff",
        "cells",
        "pass_count",
        "fixed_over_item_gain",
        "pass_reduction_vs_fixed",
        "p_mission",
        "risk_utilization",
        "delta_lut_vs_external",
        "delta_ff_vs_external",
        "delta_lut_percent_vs_external",
        "delta_ff_percent_vs_external",
    ]

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    certificate = {
        "git_commit": git_commit(),
        "fixed": fixed,
        "current": current,
        "delayed_1h": delayed,
        "synthesis_xc7": {
            "secded_32_39_encoder": xc7_encoder,
            "secded_32_39_decoder": xc7_decoder,
            "period_scheduler": xc7_period,
            "scrub_pass_engine": xc7_engine,
            "diagnostic_supervisor": xc7_diag,
            "adaptive_scrub_controller": xc7_adaptive,
            "measured_error_period_estimator": xc7_estimator,
            "measured_error_scrub_controller": xc7_measured,
        },
        "computed": {
            "current_gain_fixed_over_adaptive": current_gain,
            "delayed_gain_fixed_over_adaptive": delayed_gain,
            "current_pass_reduction_vs_fixed": pass_reduction_current,
            "delayed_pass_reduction_vs_fixed": pass_reduction_delayed,
            "measured_delta_lut_vs_external": measured_delta_lut,
            "measured_delta_ff_vs_external": measured_delta_ff,
            "measured_delta_lut_percent_vs_external": 100.0 * measured_delta_lut / adaptive_lut,
            "measured_delta_ff_percent_vs_external": 100.0 * measured_delta_ff / adaptive_ff,
        },
        "rows": rows,
    }

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(certificate, file, indent=2, ensure_ascii=False)

    lines = [
        "# Chapter 4 overhead/gain certificate",
        "",
        "This certificate combines the Chapter 3 five-year schedule gain with",
        "the Chapter 4 RTL resource estimates.",
        "",
        "## Schedule benefit",
        "",
        "| Strategy | Pass count | P mission | Risk utilization | Fixed/strategy gain | Pass reduction vs fixed |",
        "|---|---:|---:|---:|---:|---:|",
        f"| fixed | {fixed['pass_count']} | {fixed['p_mission']} | {fixed['risk_utilization']} | 1 | 0 |",
        f"| current adaptive | {current['pass_count']} | {current['p_mission']} | {current['risk_utilization']} | {current_gain:.12g} | {pass_reduction_current:.12g} |",
        f"| delayed 1h adaptive | {delayed['pass_count']} | {delayed['p_mission']} | {delayed['risk_utilization']} | {delayed_gain:.12g} | {pass_reduction_delayed:.12g} |",
        "",
        "## XC7 resource estimates",
        "",
        "| Component | LUT | FF | Cells | Meaning |",
        "|---|---:|---:|---:|---|",
        f"| SEC-DED encoder | {xc7_encoder['lut_estimate']} | {xc7_encoder['ff_estimate']} | {xc7_encoder['cells']} | ECC encode datapath |",
        f"| SEC-DED decoder | {xc7_decoder['lut_estimate']} | {xc7_decoder['ff_estimate']} | {xc7_decoder['cells']} | ECC decode/correction datapath |",
        f"| Period scheduler | {xc7_period['lut_estimate']} | {xc7_period['ff_estimate']} | {xc7_period['cells']} | External period-index endpoint |",
        f"| Scrub pass engine | {xc7_engine['lut_estimate']} | {xc7_engine['ff_estimate']} | {xc7_engine['cells']} | Full memory pass and writeback |",
        f"| Diagnostic supervisor | {xc7_diag['lut_estimate']} | {xc7_diag['ff_estimate']} | {xc7_diag['cells']} | Alert/DUE/out-of-envelope flags |",
        f"| External adaptive controller | {adaptive_lut} | {adaptive_ff} | {xc7_adaptive['cells']} | Chapter 3 schedule endpoint |",
        f"| Measured-error estimator | {xc7_estimator['lut_estimate']} | {xc7_estimator['ff_estimate']} | {xc7_estimator['cells']} | Onboard period estimator only |",
        f"| Measured-error controller | {measured_lut} | {measured_ff} | {xc7_measured['cells']} | Integrated onboard fallback |",
        "",
        "## Incremental measured-mode cost",
        "",
        "| Comparison | Delta LUT | Delta FF | Delta LUT % | Delta FF % |",
        "|---|---:|---:|---:|---:|",
        f"| measured_error_scrub_controller - adaptive_scrub_controller | {measured_delta_lut} | {measured_delta_ff} | {pct_delta(measured_delta_lut, adaptive_lut)} | {pct_delta(measured_delta_ff, adaptive_ff)} |",
        "",
        "## Interpretation",
        "",
        f"- The external current adaptive schedule reduces pass count by `{current_gain:.6g}x` relative to the best allowed fixed schedule.",
        f"- The delayed one-hour adaptive schedule reduces pass count by `{delayed_gain:.6g}x`.",
        f"- The measured-error onboard fallback costs `+{measured_delta_lut}` LUT and `+{measured_delta_ff}` FF over the external-period endpoint.",
        "- These are synthesis estimates only; they do not establish timing closure or Fmax.",
        "",
    ]

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print()
    print(OUT_CSV.read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
