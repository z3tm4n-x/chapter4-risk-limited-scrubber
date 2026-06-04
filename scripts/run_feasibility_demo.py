#!/usr/bin/env python3
"""
Generate a Chapter 2 protection-envelope evidence pack.

The generated cases are intentionally illustrative. They show the three logical
regions needed before the Chapter 3 schedule compiler is allowed to select a
scrub period.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from model.envelope import evaluate_feasibility_case  # noqa: E402
from model.risk_exact import MemoryGeometry, risk_from_mission_probability  # noqa: E402


OUTPUT_DIR = REPO_ROOT / "results" / "feasibility"


def result_to_row(result) -> dict[str, str]:
    return {
        "case_name": result.case_name,
        "description": result.description,
        "status": result.status,
        "target_e": f"{result.target_e:.12g}",
        "event_count": f"{result.event_count:.12g}",
        "g_D": f"{result.g_d:.12g}",
        "E_inst": f"{result.e_inst:.12g}",
        "E_residual": f"{result.e_residual:.12g}",
        "E_acc_at_tau_min": f"{result.e_acc_at_tau_min:.12g}",
        "tau_min_seconds": f"{result.tau_min_seconds:.12g}",
        "risk_slack_after_tau_min": f"{result.risk_slack_after_tau_min:.12g}",
        "instant_utilization": f"{result.instant_utilization:.12g}",
        "residual_utilization_at_tau_min": f"{result.residual_utilization_at_tau_min:.12g}",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "case_name",
        "description",
        "status",
        "target_e",
        "event_count",
        "g_D",
        "E_inst",
        "E_residual",
        "E_acc_at_tau_min",
        "tau_min_seconds",
        "risk_slack_after_tau_min",
        "instant_utilization",
        "residual_utilization_at_tau_min",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Protection-envelope feasibility evidence pack",
        "",
        "This report demonstrates the Chapter 2 go/no-go handoff before the",
        "Chapter 3 scrub-period scheduler is used.",
        "",
        "The cases are illustrative. Their purpose is to verify the logic:",
        "",
        "1. instant MBU risk can consume the budget;",
        "2. residual budget can remain positive while tau_min is still insufficient;",
        "3. if both checks pass, scrub-period selection is meaningful.",
        "",
        "| Case | Status | g_D | E_inst | E_residual | E_acc(tau_min) | Slack |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            "| {case_name} | {status} | {g_D} | {E_inst} | {E_residual} | "
            "{E_acc_at_tau_min} | {risk_slack_after_tau_min} |".format(**row)
        )

    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- `architecture_change_required`: decreasing the scrub period does not solve",
            "  the problem because the instant component already exceeds the budget.",
            "- `bandwidth_or_tau_min_insufficient`: instant risk is acceptable, but even",
            "  continuous operation at tau_min cannot fit the accumulated-risk residual.",
            "- `scrub_period_selectable`: the design point can be handed to the Chapter 3",
            "  schedule compiler.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    geometry = MemoryGeometry(word_bits=39, codeword_count=4096)
    target_probability = 0.001
    target_e = risk_from_mission_probability(target_probability)

    cases = [
        evaluate_feasibility_case(
            case_name="scrub_period_selectable_D3",
            description="Sufficient interleaving suppresses instant MBU mapping.",
            target_e=target_e,
            event_count=1000.0,
            pm={1: 0.97, 2: 0.02, 3: 0.01},
            hmd={2: 0.0, 3: 0.0},
            nu_values=[1.0, 30.0, 1.0, 30.0, 1.0, 30.0],
            dt_hours=[1.0] * 6,
            tau_min_seconds=1.0,
            geometry=geometry,
        ),
        evaluate_feasibility_case(
            case_name="architecture_change_required_D1",
            description="Instant MBU mapping alone exceeds the risk target.",
            target_e=target_e,
            event_count=1.0,
            pm={1: 0.97, 2: 0.02, 3: 0.01},
            hmd={2: 0.2, 3: 0.5},
            nu_values=[1.0, 30.0, 1.0, 30.0, 1.0, 30.0],
            dt_hours=[1.0] * 6,
            tau_min_seconds=1.0,
            geometry=geometry,
        ),
        evaluate_feasibility_case(
            case_name="bandwidth_or_tau_min_insufficient",
            description="Residual budget is positive but tau_min cannot meet accumulated risk.",
            target_e=target_e,
            event_count=1000.0,
            pm={1: 0.999999, 2: 0.000001},
            hmd={2: 0.1},
            nu_values=[200.0, 200.0, 200.0],
            dt_hours=[1.0, 1.0, 1.0],
            tau_min_seconds=1.0,
            geometry=geometry,
        ),
    ]

    rows = [result_to_row(result) for result in cases]

    write_csv(OUTPUT_DIR / "feasibility_summary.csv", rows)
    write_markdown(OUTPUT_DIR / "feasibility_summary.md", rows)

    certificate = {
        "geometry": {
            "word_bits": geometry.word_bits,
            "codeword_count": geometry.codeword_count,
            "physical_bits": geometry.physical_bits,
            "alpha": geometry.alpha,
        },
        "target_probability": target_probability,
        "target_e": target_e,
        "cases": rows,
        "risk_kernel": "exact",
    }

    (OUTPUT_DIR / "feasibility_certificate.json").write_text(
        json.dumps(certificate, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("Feasibility evidence pack written to", OUTPUT_DIR)
    for row in rows:
        print(row["case_name"], row["status"], "slack", row["risk_slack_after_tau_min"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
