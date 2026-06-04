#!/usr/bin/env python3
"""
Generate a Chapter 4 schedule evidence pack.

This script demonstrates the model-side output consumed by the future RTL
controller:

    nu(t), target risk, period set -> fixed/adaptive implementable schedules

The adaptive schedule uses:
    tau_calc = C / nu_hat
    tau_impl = floor_down_to_period_set(tau_calc, T)
    exact accumulated-risk verification

The generated CSV/Markdown files are intended to become Chapter 4 evidence
artifacts, not just debug output.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from model.risk_exact import (  # noqa: E402
    MemoryGeometry,
    risk_from_mission_probability,
)
from model.schedule_compiler import (  # noqa: E402
    compile_adaptive_current_schedule,
    compile_fixed_allowed_schedule,
    normalize_period_set,
    schedule_rows,
    write_schedule_csv,
)


OUTPUT_DIR = REPO_ROOT / "results" / "schedules"


def demo_series() -> tuple[list[float], list[float], list[float]]:
    """
    Return a compact six-hour demonstration series.

    Units:
        nu_values: single-bit error rate per hour over the protected array
        nu_hat: controller-side estimate used by the scheduler
        dt_hours: duration of each interval

    The alternating low/high pattern intentionally exposes the benefit of
    adapting tau to nu(t).
    """
    nu_values = [1.0, 30.0, 1.0, 30.0, 1.0, 30.0]
    nu_hat = list(nu_values)
    dt_hours = [1.0 for _ in nu_values]
    return nu_values, nu_hat, dt_hours


def write_period_table(path: Path, period_set_seconds: Iterable[float]) -> None:
    periods = normalize_period_set(period_set_seconds)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["period_index", "tau_seconds", "tau_model_cycles"],
        )
        writer.writeheader()

        # For the first model-side artifact, use one model cycle per second.
        # Later RTL-scaled experiments may use a separate mapping.
        for index, tau_seconds in enumerate(periods):
            writer.writerow(
                {
                    "period_index": index,
                    "tau_seconds": f"{tau_seconds:.12g}",
                    "tau_model_cycles": str(int(round(tau_seconds))),
                }
            )


def summary_row(result, target_e: float, fixed_pass_count: float | None = None) -> dict[str, str]:
    gain_vs_this = ""
    if fixed_pass_count is not None:
        gain_vs_this = f"{fixed_pass_count / result.stats.pass_count:.12g}"

    return {
        "strategy": result.strategy,
        "target_e": f"{target_e:.12g}",
        "risk_e": f"{result.stats.risk_e:.12g}",
        "risk_utilization": f"{result.stats.risk_e / target_e:.12g}",
        "p_mission": f"{result.stats.p_mission:.12g}",
        "pass_count": f"{result.stats.pass_count:.12g}",
        "gain_fixed_over_strategy": gain_vs_this,
        "mean_tau_seconds": f"{result.stats.mean_tau_seconds:.12g}",
        "min_tau_seconds": f"{result.stats.min_tau_seconds:.12g}",
        "max_tau_seconds": f"{result.stats.max_tau_seconds:.12g}",
        "saturated_at_tau_min": str(result.stats.saturated_at_tau_min).lower(),
        "saturated_at_tau_max": str(result.stats.saturated_at_tau_max).lower(),
    }


def write_summary_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "strategy",
        "target_e",
        "risk_e",
        "risk_utilization",
        "p_mission",
        "pass_count",
        "gain_fixed_over_strategy",
        "mean_tau_seconds",
        "min_tau_seconds",
        "max_tau_seconds",
        "saturated_at_tau_min",
        "saturated_at_tau_max",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_summary(
    path: Path,
    geometry: MemoryGeometry,
    period_set_seconds: tuple[float, ...],
    target_probability: float,
    target_e: float,
    fixed,
    adaptive,
) -> None:
    gain = fixed.stats.pass_count / adaptive.stats.pass_count

    text = f"""# Schedule evidence pack

This evidence pack demonstrates the model-side schedule output that the Chapter 4
RTL controller will consume as an external `period_index` stream.

## Geometry and target

| Quantity | Value |
|---|---:|
| word_bits | {geometry.word_bits} |
| codeword_count | {geometry.codeword_count} |
| physical_bits | {geometry.physical_bits} |
| alpha | {geometry.alpha:.12e} |
| target_probability | {target_probability:.12g} |
| target_e | {target_e:.12g} |

The geometry is intentionally small enough for later RTL replay experiments. The
mathematical functions are parameterized and also support the full dissertation
geometry.

## Allowed period set

`{list(period_set_seconds)}` seconds.

The adaptive schedule uses conservative floor-down rounding:

`tau_impl = max{{tau in T : tau <= tau_calc}}`

with clamping to the minimum and maximum allowed period.

## Strategy comparison

| Strategy | Exact E_acc | P_mission | Pass count | Risk utilization | Tau range, s |
|---|---:|---:|---:|---:|---:|
| {fixed.strategy} | {fixed.stats.risk_e:.12g} | {fixed.stats.p_mission:.12g} | {fixed.stats.pass_count:.6f} | {fixed.stats.risk_e / target_e:.6f} | {fixed.stats.min_tau_seconds:g}..{fixed.stats.max_tau_seconds:g} |
| {adaptive.strategy} | {adaptive.stats.risk_e:.12g} | {adaptive.stats.p_mission:.12g} | {adaptive.stats.pass_count:.6f} | {adaptive.stats.risk_e / target_e:.6f} | {adaptive.stats.min_tau_seconds:g}..{adaptive.stats.max_tau_seconds:g} |

## Main result

The implementable adaptive schedule reduces the full-pass count by a factor of:

**{gain:.6f}**

relative to the largest fixed allowed period satisfying the same exact-risk
target.

## Generated files

- `period_table.csv`
- `schedule_fixed.csv`
- `schedule_adaptive.csv`
- `schedule_summary.csv`
- `schedule_demo_certificate.json`
"""

    path.write_text(text, encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    geometry = MemoryGeometry(word_bits=39, codeword_count=4096)
    period_set_seconds = (
        1.0,
        2.0,
        5.0,
        10.0,
        30.0,
        60.0,
        120.0,
        300.0,
        600.0,
    )
    target_probability = 0.001
    target_e = risk_from_mission_probability(target_probability)

    nu_values, nu_hat, dt_hours = demo_series()

    fixed = compile_fixed_allowed_schedule(
        nu_values=nu_values,
        dt_hours=dt_hours,
        target_e=target_e,
        period_set_seconds=period_set_seconds,
        geometry=geometry,
    )

    adaptive = compile_adaptive_current_schedule(
        nu_values=nu_values,
        dt_hours=dt_hours,
        target_e=target_e,
        period_set_seconds=period_set_seconds,
        geometry=geometry,
    )

    write_period_table(OUTPUT_DIR / "period_table.csv", period_set_seconds)

    write_schedule_csv(
        OUTPUT_DIR / "schedule_fixed.csv",
        fixed,
        nu_values=nu_values,
        estimate_values=nu_hat,
        dt_hours=dt_hours,
    )

    write_schedule_csv(
        OUTPUT_DIR / "schedule_adaptive.csv",
        adaptive,
        nu_values=nu_values,
        estimate_values=nu_hat,
        dt_hours=dt_hours,
    )

    summary_rows = [
        summary_row(fixed, target_e, fixed_pass_count=fixed.stats.pass_count),
        summary_row(adaptive, target_e, fixed_pass_count=fixed.stats.pass_count),
    ]

    write_summary_csv(OUTPUT_DIR / "schedule_summary.csv", summary_rows)

    certificate = {
        "geometry": {
            "word_bits": geometry.word_bits,
            "codeword_count": geometry.codeword_count,
            "physical_bits": geometry.physical_bits,
            "alpha": geometry.alpha,
        },
        "target_probability": target_probability,
        "target_e": target_e,
        "period_set_seconds": list(period_set_seconds),
        "nu_values_per_hour": nu_values,
        "nu_hat_values_per_hour": nu_hat,
        "dt_hours": dt_hours,
        "fixed": summary_rows[0],
        "adaptive": summary_rows[1],
        "gain_fixed_over_adaptive": fixed.stats.pass_count / adaptive.stats.pass_count,
        "risk_kernel": "exact",
        "rounding_rule": "floor_down_to_period_set",
    }

    (OUTPUT_DIR / "schedule_demo_certificate.json").write_text(
        json.dumps(certificate, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    write_markdown_summary(
        OUTPUT_DIR / "schedule_summary.md",
        geometry=geometry,
        period_set_seconds=period_set_seconds,
        target_probability=target_probability,
        target_e=target_e,
        fixed=fixed,
        adaptive=adaptive,
    )

    print("Schedule evidence pack written to", OUTPUT_DIR)
    print("fixed_pass_count:", f"{fixed.stats.pass_count:.6f}")
    print("adaptive_pass_count:", f"{adaptive.stats.pass_count:.6f}")
    print("gain_fixed_over_adaptive:", f"{fixed.stats.pass_count / adaptive.stats.pass_count:.6f}")
    print("fixed_risk_e:", f"{fixed.stats.risk_e:.12g}")
    print("adaptive_risk_e:", f"{adaptive.stats.risk_e:.12g}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
