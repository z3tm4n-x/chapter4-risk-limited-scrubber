#!/usr/bin/env python3
"""Select representative Chapter 3 windows for RTL schedule replay."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_PATH = REPO_ROOT / "results" / "schedules" / "ch3_five_year_schedule_current.csv"
DELAYED_PATH = REPO_ROOT / "results" / "schedules" / "ch3_five_year_schedule_delayed_1h.csv"
OUT_CSV = REPO_ROOT / "results" / "schedules" / "ch3_replay_windows.csv"
OUT_MD = REPO_ROOT / "results" / "schedules" / "ch3_replay_windows.md"


@dataclass(frozen=True)
class ScheduleRow:
    index: int
    timestamp: str
    nu: float
    nu_hat: float
    tau: float
    period_index: int
    passes: float


def read_schedule(path: Path) -> list[ScheduleRow]:
    rows: list[ScheduleRow] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append(
                ScheduleRow(
                    index=int(row["time_index"]),
                    timestamp=row["timestamp_utc"],
                    nu=float(row["nu"]),
                    nu_hat=float(row["nu_hat"]),
                    tau=float(row["tau_seconds"]),
                    period_index=int(row["period_index"]),
                    passes=float(row["passes"]),
                )
            )

    return rows


def clamp_window(center: int, half_width: int, n: int) -> tuple[int, int]:
    start = max(0, center - half_width)
    end = min(n - 1, center + half_width)

    # Try to keep a stable length when close to boundaries.
    desired = 2 * half_width + 1
    actual = end - start + 1

    if actual < desired:
        if start == 0:
            end = min(n - 1, desired - 1)
        elif end == n - 1:
            start = max(0, n - desired)

    return start, end


def window_metrics(rows: list[ScheduleRow], start: int, end: int) -> dict[str, float | int | str]:
    subset = rows[start : end + 1]
    return {
        "start_index": start,
        "end_index": end,
        "start_timestamp_utc": subset[0].timestamp,
        "end_timestamp_utc": subset[-1].timestamp,
        "hours": len(subset),
        "mean_nu": mean(row.nu for row in subset),
        "max_nu": max(row.nu for row in subset),
        "min_tau_seconds": min(row.tau for row in subset),
        "max_tau_seconds": max(row.tau for row in subset),
        "expected_passes": sum(row.passes for row in subset),
        "dominant_period_index": max(
            sorted(set(row.period_index for row in subset)),
            key=lambda idx: sum(1 for row in subset if row.period_index == idx),
        ),
    }


def select_windows(current: list[ScheduleRow], delayed: list[ScheduleRow]) -> list[dict[str, str]]:
    n = len(current)
    half_width = 24  # 49-hour windows: compact for RTL, still includes transitions.

    max_nu_index = max(range(n), key=lambda i: current[i].nu)

    # Largest positive one-hour growth.
    max_growth_index = max(
        range(1, n),
        key=lambda i: current[i].nu / max(current[i - 1].nu, 1e-30),
    )

    # Largest one-hour decay from previous hour.
    max_decay_index = max(
        range(1, n),
        key=lambda i: current[i - 1].nu / max(current[i].nu, 1e-30),
    )

    # Quiet window: low nu, non-boundary period, avoid very beginning.
    quiet_candidates = [
        i for i in range(720, n - 720)
        if current[i].nu < 4.0 and current[i].tau >= 60.0
    ]
    quiet_index = min(quiet_candidates, key=lambda i: current[i].nu) if quiet_candidates else 1000

    # Tau-min saturation: center on a current schedule tau=1 hour.
    tau_min_indices = [i for i, row in enumerate(current) if row.tau == 1.0]
    tau_min_index = tau_min_indices[len(tau_min_indices) // 2] if tau_min_indices else max_nu_index

    # Delayed-sensitive: current and delayed period index differ maximally.
    delayed_sensitive_index = max(
        range(n),
        key=lambda i: (
            abs(current[i].period_index - delayed[i].period_index),
            current[i].nu,
        ),
    )

    selected = [
        ("quiet_background", quiet_index),
        ("storm_rise", max_growth_index),
        ("storm_peak", max_nu_index),
        ("storm_decay", max_decay_index),
        ("tau_min_saturation", tau_min_index),
        ("delayed_sensitive", delayed_sensitive_index),
    ]

    output: list[dict[str, str]] = []
    seen_ranges: set[tuple[int, int]] = set()

    for name, center in selected:
        start, end = clamp_window(center, half_width, n)

        # If two windows collide exactly, keep both names but record same interval.
        seen_ranges.add((start, end))

        current_metrics = window_metrics(current, start, end)
        delayed_metrics = window_metrics(delayed, start, end)

        output.append(
            {
                "window_name": name,
                "center_index": str(center),
                "center_timestamp_utc": current[center].timestamp,
                "start_index": str(start),
                "end_index": str(end),
                "start_timestamp_utc": str(current_metrics["start_timestamp_utc"]),
                "end_timestamp_utc": str(current_metrics["end_timestamp_utc"]),
                "hours": str(current_metrics["hours"]),
                "current_expected_passes": f"{float(current_metrics['expected_passes']):.12g}",
                "delayed_expected_passes": f"{float(delayed_metrics['expected_passes']):.12g}",
                "mean_nu": f"{float(current_metrics['mean_nu']):.12g}",
                "max_nu": f"{float(current_metrics['max_nu']):.12g}",
                "current_tau_range_seconds": f"{float(current_metrics['min_tau_seconds']):.12g}..{float(current_metrics['max_tau_seconds']):.12g}",
                "delayed_tau_range_seconds": f"{float(delayed_metrics['min_tau_seconds']):.12g}..{float(delayed_metrics['max_tau_seconds']):.12g}",
                "current_dominant_period_index": str(current_metrics["dominant_period_index"]),
                "delayed_dominant_period_index": str(delayed_metrics["dominant_period_index"]),
                "center_current_period_index": str(current[center].period_index),
                "center_delayed_period_index": str(delayed[center].period_index),
                "center_current_tau_seconds": f"{current[center].tau:.12g}",
                "center_delayed_tau_seconds": f"{delayed[center].tau:.12g}",
            }
        )

    return output


def write_outputs(rows: list[dict[str, str]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "window_name",
        "center_index",
        "center_timestamp_utc",
        "start_index",
        "end_index",
        "start_timestamp_utc",
        "end_timestamp_utc",
        "hours",
        "current_expected_passes",
        "delayed_expected_passes",
        "mean_nu",
        "max_nu",
        "current_tau_range_seconds",
        "delayed_tau_range_seconds",
        "current_dominant_period_index",
        "delayed_dominant_period_index",
        "center_current_period_index",
        "center_delayed_period_index",
        "center_current_tau_seconds",
        "center_delayed_tau_seconds",
    ]

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Chapter 3 RTL replay window selection",
        "",
        "| Window | Start | End | Hours | Current passes | Delayed passes | Max nu | Current tau range | Delayed tau range | Center current/delayed tau |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            f"| {row['window_name']} | {row['start_timestamp_utc']} | {row['end_timestamp_utc']} | "
            f"{row['hours']} | {row['current_expected_passes']} | {row['delayed_expected_passes']} | "
            f"{row['max_nu']} | {row['current_tau_range_seconds']} | {row['delayed_tau_range_seconds']} | "
            f"{row['center_current_tau_seconds']} / {row['center_delayed_tau_seconds']} |"
        )

    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    current = read_schedule(CURRENT_PATH)
    delayed = read_schedule(DELAYED_PATH)

    if len(current) != len(delayed):
        raise RuntimeError("current and delayed schedule lengths differ")

    rows = select_windows(current, delayed)
    write_outputs(rows)

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print()
    print(OUT_CSV.read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
