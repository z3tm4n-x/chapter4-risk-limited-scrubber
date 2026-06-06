#!/usr/bin/env python3
"""Monte Carlo validation for the accumulated-risk kernel.

This script validates the Chapter 2 accumulated dangerous-state model by direct
random placement of independent single-bit errors over the protected memory.

The mission region is far too rare to observe directly. Therefore the Monte
Carlo uses accelerated Poisson means lambda where collisions are observable,
then compares the empirical probability against q_acc_exact(lambda). The same
table also reports the quadratic approximation alpha * lambda^2.
"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from model.risk_exact import MemoryGeometry, q_acc_exact, q_acc_quadratic


CONFIG_PATH = REPO_ROOT / "configs" / "ch3_main_1pct.json"

OUT_DIR = REPO_ROOT / "results" / "monte_carlo"
OUT_CSV = OUT_DIR / "accumulation_monte_carlo_summary.csv"
OUT_MD = OUT_DIR / "accumulation_monte_carlo_report.md"
OUT_JSON = OUT_DIR / "accumulation_monte_carlo_certificate.json"

SEED = 20260605

CASES = [
    # lambda, trials
    (50.0, 150_000),
    (100.0, 120_000),
    (200.0, 80_000),
    (300.0, 60_000),
]


@dataclass(frozen=True)
class MonteCarloCase:
    lambda_value: float
    trials: int


def load_geometry() -> MemoryGeometry:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    geometry_cfg = config["geometry"]
    return MemoryGeometry(
        word_bits=int(geometry_cfg["word_bits"]),
        codeword_count=int(geometry_cfg["codeword_count"]),
    )


def poisson_knuth(lambda_value: float, rng: random.Random) -> int:
    """Sample Poisson(lambda) using Knuth's method.

    The selected accelerated lambdas are <= 300, where this remains acceptable
    for a reproducible offline validation script.
    """

    threshold = math.exp(-lambda_value)
    product = 1.0
    k = 0

    while product > threshold:
        k += 1
        product *= rng.random()

    return k - 1


def dangerous_random_placement(k: int, geometry: MemoryGeometry, rng: random.Random) -> bool:
    """Return true if k random bit errors place at least two errors in one word."""

    if k < 2:
        return False

    if k > geometry.codeword_count:
        return True

    physical_bits = geometry.physical_bits
    word_bits = geometry.word_bits

    selected_bits: set[int] = set()
    selected_words: set[int] = set()

    while len(selected_bits) < k:
        bit = rng.randrange(physical_bits)

        if bit in selected_bits:
            continue

        selected_bits.add(bit)
        word = bit // word_bits

        if word in selected_words:
            return True

        selected_words.add(word)

    return False


def run_case(case: MonteCarloCase, geometry: MemoryGeometry, rng: random.Random) -> dict[str, str]:
    dangerous = 0

    for _ in range(case.trials):
        k = poisson_knuth(case.lambda_value, rng)

        if dangerous_random_placement(k, geometry, rng):
            dangerous += 1

    empirical = dangerous / case.trials
    exact = q_acc_exact(case.lambda_value, geometry)
    quadratic = q_acc_quadratic(case.lambda_value, geometry)

    variance = exact * (1.0 - exact) / case.trials
    stderr = math.sqrt(variance) if variance > 0.0 else 0.0

    ci95_low = max(0.0, empirical - 1.96 * stderr)
    ci95_high = min(1.0, empirical + 1.96 * stderr)

    z_score = 0.0 if stderr == 0.0 else (empirical - exact) / stderr
    pass_z = abs(z_score) <= 4.0

    rel_empirical_exact = (
        abs(empirical - exact) / exact
        if exact > 0.0
        else 0.0
    )
    rel_quadratic_exact = (
        abs(quadratic - exact) / exact
        if exact > 0.0
        else 0.0
    )

    return {
        "lambda": f"{case.lambda_value:.12g}",
        "trials": str(case.trials),
        "dangerous_trials": str(dangerous),
        "empirical_q": f"{empirical:.12g}",
        "exact_q": f"{exact:.12g}",
        "quadratic_q": f"{quadratic:.12g}",
        "empirical_minus_exact": f"{empirical - exact:.12g}",
        "relative_empirical_exact": f"{rel_empirical_exact:.12g}",
        "relative_quadratic_exact": f"{rel_quadratic_exact:.12g}",
        "stderr_vs_exact": f"{stderr:.12g}",
        "ci95_low": f"{ci95_low:.12g}",
        "ci95_high": f"{ci95_high:.12g}",
        "z_score": f"{z_score:.12g}",
        "pass_z_4sigma": str(pass_z).lower(),
    }


def write_outputs(rows: list[dict[str, str]], geometry: MemoryGeometry) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "lambda",
        "trials",
        "dangerous_trials",
        "empirical_q",
        "exact_q",
        "quadratic_q",
        "empirical_minus_exact",
        "relative_empirical_exact",
        "relative_quadratic_exact",
        "stderr_vs_exact",
        "ci95_low",
        "ci95_high",
        "z_score",
        "pass_z_4sigma",
    ]

    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    all_pass = all(row["pass_z_4sigma"] == "true" for row in rows)

    lines = [
        "# Accumulated-risk Monte Carlo validation",
        "",
        "This report validates the accumulated dangerous-state kernel by direct",
        "random placement of independent bit errors over the dissertation memory",
        "geometry. The test uses accelerated lambda values where collisions are",
        "observable in finite Monte Carlo time.",
        "",
        "## Geometry",
        "",
        "| Quantity | Value |",
        "|---|---:|",
        f"| word_bits | {geometry.word_bits} |",
        f"| codeword_count | {geometry.codeword_count} |",
        f"| physical_bits | {geometry.physical_bits} |",
        f"| alpha | {geometry.alpha:.12e} |",
        f"| seed | {SEED} |",
        "",
        "## Results",
        "",
        "| Lambda | Trials | Empirical q | Exact q | Quadratic q | Empirical/exact rel. err. | Quadratic/exact rel. err. | z-score | Pass |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            f"| {row['lambda']} | {row['trials']} | {row['empirical_q']} | "
            f"{row['exact_q']} | {row['quadratic_q']} | "
            f"{row['relative_empirical_exact']} | {row['relative_quadratic_exact']} | "
            f"{row['z_score']} | {row['pass_z_4sigma']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `q_acc_exact(lambda)` agrees with direct random placement within the configured 4-sigma statistical gate.",
            "- The quadratic kernel is close in the low-lambda region and increasingly conservative as lambda grows.",
            "- Working mission lambdas are much smaller than these accelerated validation cases; direct observation there would be impractical.",
            f"- Overall Monte Carlo pass: `{str(all_pass).lower()}`.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "seed": SEED,
                "geometry": {
                    "word_bits": geometry.word_bits,
                    "codeword_count": geometry.codeword_count,
                    "physical_bits": geometry.physical_bits,
                    "alpha": geometry.alpha,
                },
                "all_pass": all_pass,
                "rows": rows,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )


def main() -> int:
    geometry = load_geometry()
    rng = random.Random(SEED)

    rows = [
        run_case(MonteCarloCase(lambda_value=lambda_value, trials=trials), geometry, rng)
        for lambda_value, trials in CASES
    ]

    write_outputs(rows, geometry)

    print("Wrote", OUT_CSV)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    print()
    print(OUT_CSV.read_text(encoding="utf-8"))

    all_pass = all(row["pass_z_4sigma"] == "true" for row in rows)

    if not all_pass:
        raise SystemExit("Monte Carlo validation failed 4-sigma gate")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
