#!/usr/bin/env python3
"""Build a tau_min feasibility certificate for Chapter 4.

The certificate separates two timing questions:

1. Can the RTL controller core issue scrub service fast enough?
2. Can the system-level memory interface sustain the assumed scrub pass rate?

The Chapter 4 text uses the memory-interface-limited scenario as the binding
design constraint for tau_min. The controller-core scenario demonstrates that
the RTL core itself is not the bottleneck.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = REPO_ROOT / "configs" / "ch4_hardware_timing.json"
OUT_CSV = REPO_ROOT / "results" / "feasibility" / "tau_min_certificate.csv"
OUT_DETAIL_CSV = REPO_ROOT / "results" / "feasibility" / "tau_min_certificate_detail.csv"
OUT_MD = REPO_ROOT / "results" / "feasibility" / "tau_min_certificate.md"
OUT_JSON = REPO_ROOT / "results" / "feasibility" / "tau_min_certificate.json"


def read_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def evaluate_scenario(
    *,
    scenario: dict,
    codeword_count: int,
    codeword_bits: int,
    pipeline_overhead_cycles: float,
    tau_min: float,
) -> dict:
    key = scenario["key"]
    description = scenario.get("description", "")

    protected_bits = codeword_count * codeword_bits

    if "scrub_clock_hz" in scenario:
        scrub_clock_hz = float(scenario["scrub_clock_hz"])
        cycles_per_word = float(scenario.get("cycles_per_word", 1.0))

        if scrub_clock_hz <= 0:
            raise ValueError(f"{key}: scrub_clock_hz must be positive")
        if cycles_per_word <= 0:
            raise ValueError(f"{key}: cycles_per_word must be positive")

        pass_cycles = codeword_count * cycles_per_word + pipeline_overhead_cycles
        pass_time_seconds = pass_cycles / scrub_clock_hz
        effective_words_per_second = scrub_clock_hz / cycles_per_word
        effective_bits_per_second = effective_words_per_second * codeword_bits
        service_model = "clocked_codeword_service"

    elif "effective_bits_per_second" in scenario:
        effective_bits_per_second = float(scenario["effective_bits_per_second"])

        if effective_bits_per_second <= 0:
            raise ValueError(f"{key}: effective_bits_per_second must be positive")

        pass_bits = (codeword_count + pipeline_overhead_cycles) * codeword_bits
        pass_cycles = ""
        pass_time_seconds = pass_bits / effective_bits_per_second
        effective_words_per_second = effective_bits_per_second / codeword_bits
        service_model = "memory_interface_bandwidth"

    else:
        raise ValueError(f"{key}: scenario must define scrub_clock_hz or effective_bits_per_second")

    tau_min_margin = tau_min / pass_time_seconds
    tau_min_feasible = pass_time_seconds <= tau_min

    return {
        "scenario": key,
        "description": description,
        "service_model": service_model,
        "codeword_count": codeword_count,
        "codeword_bits": codeword_bits,
        "protected_bits": protected_bits,
        "pass_cycles": pass_cycles,
        "pass_time_seconds": pass_time_seconds,
        "effective_words_per_second": effective_words_per_second,
        "effective_bits_per_second": effective_bits_per_second,
        "target_tau_min_seconds": tau_min,
        "tau_min_margin": tau_min_margin,
        "tau_min_feasible": str(tau_min_feasible).lower(),
    }


def main() -> int:
    cfg = read_config()

    codeword_count = int(cfg["codeword_count"])
    codeword_bits = int(cfg["codeword_bits"])
    pipeline_overhead_cycles = float(cfg.get("pipeline_overhead_cycles", 0))
    tau_min = float(cfg["target_tau_min_seconds"])
    primary_key = cfg.get("primary_scenario", "memory_interface_limited")

    if codeword_count <= 0:
        raise ValueError("codeword_count must be positive")
    if codeword_bits <= 0:
        raise ValueError("codeword_bits must be positive")
    if pipeline_overhead_cycles < 0:
        raise ValueError("pipeline_overhead_cycles must be non-negative")
    if tau_min <= 0:
        raise ValueError("target_tau_min_seconds must be positive")

    scenarios = cfg.get("scenarios")
    if not scenarios:
        scenarios = [
            {
                "key": "controller_core_ooc",
                "description": "Legacy controller-core service model.",
                "scrub_clock_hz": float(cfg["scrub_clock_hz"]),
                "cycles_per_word": float(cfg["cycles_per_word"]),
            }
        ]

    detail_rows = [
        evaluate_scenario(
            scenario=scenario,
            codeword_count=codeword_count,
            codeword_bits=codeword_bits,
            pipeline_overhead_cycles=pipeline_overhead_cycles,
            tau_min=tau_min,
        )
        for scenario in scenarios
    ]

    by_key = {row["scenario"]: row for row in detail_rows}
    if primary_key not in by_key:
        raise ValueError(f"primary_scenario {primary_key!r} not found in scenarios")

    primary = by_key[primary_key]

    metric_rows = [
        ("codeword_count", codeword_count),
        ("codeword_bits", codeword_bits),
        ("protected_bits", codeword_count * codeword_bits),
        ("pipeline_overhead_cycles", pipeline_overhead_cycles),
        ("target_tau_min_seconds", tau_min),
        ("primary_scenario", primary_key),
        ("pass_time_seconds", primary["pass_time_seconds"]),
        ("effective_words_per_second", primary["effective_words_per_second"]),
        ("effective_bits_per_second", primary["effective_bits_per_second"]),
        ("tau_min_margin", primary["tau_min_margin"]),
        ("tau_min_feasible", primary["tau_min_feasible"]),
    ]

    for row in detail_rows:
        prefix = row["scenario"]
        metric_rows.extend(
            [
                (f"{prefix}_pass_time_seconds", row["pass_time_seconds"]),
                (f"{prefix}_effective_words_per_second", row["effective_words_per_second"]),
                (f"{prefix}_effective_bits_per_second", row["effective_bits_per_second"]),
                (f"{prefix}_tau_min_margin", row["tau_min_margin"]),
                (f"{prefix}_tau_min_feasible", row["tau_min_feasible"]),
            ]
        )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["metric", "value"])
        writer.writerows(metric_rows)

    with OUT_DETAIL_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(detail_rows[0].keys()))
        writer.writeheader()
        writer.writerows(detail_rows)

    report = [
        "# Tau-min hardware feasibility certificate",
        "",
        "This certificate connects the Chapter 3 minimum scrub period to two",
        "explicit service-rate models:",
        "",
        "- a controller-core model, used to show that the RTL scrub core is not",
        "  the bottleneck;",
        "- a memory-interface-limited model, used as the binding design constraint",
        "  for the Chapter 3/4 choice `tau_min = 1 s`.",
        "",
        "It is not a place-and-route timing report. Vivado OOC timing evidence is",
        "reported separately.",
        "",
        "## Scenario results",
        "",
        "| Scenario | Service model | Effective words/s | Effective bits/s | Pass time, s | Tau-min margin | Feasible |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    for row in detail_rows:
        report.append(
            "| {scenario} | {service_model} | {effective_words_per_second:.12g} | "
            "{effective_bits_per_second:.12g} | {pass_time_seconds:.12g} | "
            "{tau_min_margin:.12g} | {tau_min_feasible} |".format(**row)
        )

    report.extend(
        [
            "",
            "## Binding interpretation",
            "",
            f"- The primary binding scenario is `{primary_key}`.",
            f"- Under the binding scenario, one complete pass over `{codeword_count}`",
            f"  SEC-DED codewords takes `{primary['pass_time_seconds']:.12g}` s.",
            f"- The Chapter 3 minimum period is `{tau_min:.12g}` s.",
            f"- The binding tau-min margin is `{primary['tau_min_margin']:.12g}`.",
            f"- Tau-min feasibility verdict: `{primary['tau_min_feasible']}`.",
            "",
        ]
    )

    if "controller_core_ooc" in by_key and "memory_interface_limited" in by_key:
        core = by_key["controller_core_ooc"]
        iface = by_key["memory_interface_limited"]
        report.extend(
            [
                "## Design conclusion",
                "",
                f"- The controller-core service model gives a pass time of `{core['pass_time_seconds']:.12g}` s",
                f"  and a margin of `{core['tau_min_margin']:.12g}`.",
                f"- The memory-interface-limited model gives a pass time of `{iface['pass_time_seconds']:.12g}` s",
                f"  and a margin of `{iface['tau_min_margin']:.12g}`.",
                "- Therefore the scrub controller logic is not the limiting factor for",
                "  `tau_min`; the binding constraint is the sustained memory-interface",
                "  service bandwidth reserved for scrub traffic.",
                "",
            ]
        )

    OUT_MD.write_text("\n".join(report), encoding="utf-8")

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "generated_by": "build_tau_min_certificate.py",
                "config": cfg,
                "primary_scenario": primary_key,
                "metrics": {key: value for key, value in metric_rows},
                "detail": detail_rows,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_DETAIL_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print()
    print(OUT_MD.read_text(encoding="utf-8"))

    failed = [row for row in detail_rows if row["tau_min_feasible"] != "true"]
    if failed:
        raise SystemExit("tau_min is not feasible under at least one configured service-rate model")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
