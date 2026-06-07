#!/usr/bin/env python3
"""Build a tau_min feasibility certificate for Chapter 4.

This script connects the Chapter 3 minimum scrub period to an explicit
hardware service-rate model.

It does not claim timing closure. It only checks that the assumed minimum
period is long enough to complete one full scrub pass at the configured
effective scrub service rate.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = REPO_ROOT / "configs" / "ch4_hardware_timing.json"
OUT_CSV = REPO_ROOT / "results" / "feasibility" / "tau_min_certificate.csv"
OUT_MD = REPO_ROOT / "results" / "feasibility" / "tau_min_certificate.md"
OUT_JSON = REPO_ROOT / "results" / "feasibility" / "tau_min_certificate.json"


def read_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    cfg = read_config()

    codeword_count = int(cfg["codeword_count"])
    codeword_bits = int(cfg["codeword_bits"])
    scrub_clock_hz = float(cfg["scrub_clock_hz"])
    cycles_per_word = float(cfg["cycles_per_word"])
    pipeline_overhead_cycles = float(cfg.get("pipeline_overhead_cycles", 0))
    tau_min = float(cfg["target_tau_min_seconds"])

    if codeword_count <= 0:
        raise ValueError("codeword_count must be positive")
    if codeword_bits <= 0:
        raise ValueError("codeword_bits must be positive")
    if scrub_clock_hz <= 0:
        raise ValueError("scrub_clock_hz must be positive")
    if cycles_per_word <= 0:
        raise ValueError("cycles_per_word must be positive")
    if tau_min <= 0:
        raise ValueError("target_tau_min_seconds must be positive")

    pass_cycles = codeword_count * cycles_per_word + pipeline_overhead_cycles
    pass_time_seconds = pass_cycles / scrub_clock_hz
    effective_words_per_second = scrub_clock_hz / cycles_per_word
    effective_bits_per_second = effective_words_per_second * codeword_bits
    tau_min_margin = tau_min / pass_time_seconds
    tau_min_feasible = pass_time_seconds <= tau_min

    rows = [
        ("codeword_count", codeword_count),
        ("codeword_bits", codeword_bits),
        ("protected_bits", codeword_count * codeword_bits),
        ("scrub_clock_hz", scrub_clock_hz),
        ("cycles_per_word", cycles_per_word),
        ("pipeline_overhead_cycles", pipeline_overhead_cycles),
        ("pass_cycles", pass_cycles),
        ("pass_time_seconds", pass_time_seconds),
        ("effective_words_per_second", effective_words_per_second),
        ("effective_bits_per_second", effective_bits_per_second),
        ("target_tau_min_seconds", tau_min),
        ("tau_min_margin", tau_min_margin),
        ("tau_min_feasible", str(tau_min_feasible).lower()),
    ]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)

    report = [
        "# Tau-min hardware feasibility certificate",
        "",
        "This certificate connects the Chapter 3 minimum scrub period to an",
        "explicit hardware service-rate model.",
        "",
        "It is not a place-and-route timing report. It only checks whether one",
        "complete scrub pass can fit inside the configured minimum period.",
        "",
        "## Parameters and results",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]

    for key, value in rows:
        report.append(f"| {key} | {value} |")

    report.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- One complete pass over `{codeword_count}` SEC-DED codewords takes `{pass_time_seconds:.12g}` s under the configured service-rate model.",
            f"- The Chapter 3 minimum period is `{tau_min:.12g}` s.",
            f"- The resulting tau-min margin is `{tau_min_margin:.12g}`.",
            f"- Tau-min feasibility verdict: `{str(tau_min_feasible).lower()}`.",
            "",
            "If the memory subsystem provides a lower effective scrub bandwidth,",
            "the configuration must be updated and the residual-risk boundary",
            "must be recomputed.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(report), encoding="utf-8")

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "generated_by": "build_tau_min_certificate.py",
                "config": cfg,
                "metrics": {key: value for key, value in rows},
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print()
    print(OUT_MD.read_text(encoding="utf-8"))

    if not tau_min_feasible:
        raise SystemExit("tau_min is not feasible under the configured service-rate model")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
