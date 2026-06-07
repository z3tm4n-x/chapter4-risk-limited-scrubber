#!/usr/bin/env python3
"""Check Chapter 4 reproducibility/output hygiene.

This audit intentionally separates durable evidence artifacts from transient
runtime logs. Summary/certificate CSV/MD/JSON files are tracked; raw logs are
regenerated locally and should not be tracked.
"""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "results" / "reproducibility"
OUT_CSV = OUT_DIR / "chapter4_reproducibility_hygiene.csv"
OUT_MD = OUT_DIR / "chapter4_reproducibility_hygiene.md"
OUT_JSON = OUT_DIR / "chapter4_reproducibility_hygiene.json"


TRANSIENT_PATTERNS = [
    "results/rtl_replay/*.log",
    "results/synthesis/logs/*.log",
]


def git_lines(args: list[str]) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def tracked_matches(patterns: list[str]) -> list[str]:
    result: list[str] = []
    for pattern in patterns:
        result.extend(git_lines(["ls-files", pattern]))
    return sorted(set(result))


def check_ignored(path: str) -> bool:
    proc = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=REPO_ROOT,
        check=False,
    )
    return proc.returncode == 0


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tracked_transient = tracked_matches(TRANSIENT_PATTERNS)

    samples = {
        "rtl_replay_log_ignored": check_ignored("results/rtl_replay/example.log"),
        "synthesis_log_ignored": check_ignored("results/synthesis/logs/example.log"),
        "summary_csv_tracked_allowed": True,
        "summary_md_tracked_allowed": True,
        "summary_json_tracked_allowed": True,
    }

    rows = [
        ("tracked_transient_log_count", str(len(tracked_transient))),
        ("rtl_replay_log_ignored", str(samples["rtl_replay_log_ignored"]).lower()),
        ("synthesis_log_ignored", str(samples["synthesis_log_ignored"]).lower()),
        ("summary_csv_tracked_allowed", "true"),
        ("summary_md_tracked_allowed", "true"),
        ("summary_json_tracked_allowed", "true"),
        ("hygiene_pass", str(len(tracked_transient) == 0 and samples["rtl_replay_log_ignored"] and samples["synthesis_log_ignored"]).lower()),
    ]

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)

    lines = [
        "# Chapter 4 reproducibility hygiene audit",
        "",
        "This audit checks that transient runtime logs are not tracked as durable",
        "evidence artifacts.",
        "",
        "Tracked evidence remains in summary/certificate `csv`, `md`, and `json`",
        "files. Runtime `.log` files are regenerated locally and ignored.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]

    for key, value in rows:
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## Tracked transient logs",
            "",
        ]
    )

    if tracked_transient:
        for path in tracked_transient:
            lines.append(f"- `{path}`")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Full Chapter 4 reproduction may regenerate raw logs.",
            "- Regenerated logs should not by themselves dirty the git worktree.",
            "- Durable evidence is carried by committed summary/certificate artifacts.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    OUT_JSON.write_text(
        json.dumps(
            {
                "generated_by": "check_reproducibility_hygiene.py",
                "transient_patterns": TRANSIENT_PATTERNS,
                "tracked_transient_logs": tracked_transient,
                "metrics": {key: value for key, value in rows},
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)

    if tracked_transient:
        print("Tracked transient logs remain:")
        for path in tracked_transient:
            print(" ", path)
        return 1

    if not samples["rtl_replay_log_ignored"] or not samples["synthesis_log_ignored"]:
        print("Transient log ignore rules are incomplete.")
        return 1

    print("Chapter 4 reproducibility hygiene pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
