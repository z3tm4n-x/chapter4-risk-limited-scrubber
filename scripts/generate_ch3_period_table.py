#!/usr/bin/env python3
"""Generate the Chapter 3 period table artifacts from the main configuration."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "ch3_main_1pct.json"
CSV_PATH = REPO_ROOT / "results" / "schedules" / "ch3_period_table.csv"
SVH_PATH = REPO_ROOT / "generated" / "rtl" / "ch3_period_table_params.svh"


def ceil_log2(value: int) -> int:
    if value <= 1:
        return 1
    return math.ceil(math.log2(value))


def main() -> int:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    periods = [float(value) for value in config["period_set_seconds"]]
    if not periods:
        raise RuntimeError("empty period_set_seconds")

    if periods != sorted(set(periods)):
        raise RuntimeError(f"period_set_seconds must be strictly increasing and unique: {periods}")

    if len(periods) > 16:
        raise RuntimeError("current RTL parameterization supports up to 16 entries")

    width = max(4, ceil_log2(len(periods)))

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["period_index", "tau_seconds", "tau_cycles_at_1hz"])
        writer.writeheader()
        for idx, period in enumerate(periods):
            writer.writerow(
                {
                    "period_index": idx,
                    "tau_seconds": f"{period:g}",
                    "tau_cycles_at_1hz": int(round(period)),
                }
            )

    SVH_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "// Auto-generated from configs/ch3_main_1pct.json.",
        "// Do not edit manually.",
        "",
        "`ifndef CH3_PERIOD_TABLE_PARAMS_SVH",
        "`define CH3_PERIOD_TABLE_PARAMS_SVH",
        "",
        f"`define CH3_PERIOD_COUNT {len(periods)}",
        f"`define CH3_PERIOD_INDEX_WIDTH {width}",
    ]

    for idx, period in enumerate(periods):
        lines.append(f"`define CH3_PERIOD{idx}_CYCLES {int(round(period))}")

    lines.extend(
        [
            "",
            "`define CH3_PERIOD_PARAMETER_BINDINGS \\",
            "    .PERIOD_INDEX_WIDTH(`CH3_PERIOD_INDEX_WIDTH), \\",
        ]
    )

    for idx in range(12):
        if idx < len(periods):
            value = int(round(periods[idx]))
        else:
            value = int(round(periods[-1]))

        continuation = " \\" if idx != 11 else ""
        lines.append(f"    .PERIOD{idx}_CYCLES({value}){',' if idx != 11 else ''}{continuation}")

    lines.extend(
        [
            "",
            "`endif",
            "",
        ]
    )

    SVH_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("Generated", CSV_PATH)
    print("Generated", SVH_PATH)
    print("period_count:", len(periods))
    print("period_index_width:", width)
    print("periods:", periods)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
