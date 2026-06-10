#!/usr/bin/env python3
"""Estimate-update-rate sensitivity experiment for Chapter 3.

The experiment has two families:

1. Pure lag family:
       nu_hat(t_i) = nu(t_i - L)

2. Session/hold family:
       sessions every U hours;
       at a session, the freshest available estimate has age A hours;
       between sessions, the last estimate is held.

Two calibration modes are reported:

- reoptimized: choose the largest C under exact risk for each estimate stream;
- frozen_1h: reuse the C value calibrated for the baseline delayed_1h stream.

The second mode is the actual degradation/failure test for an external branch
that was designed for hourly updates but later receives less frequent updates.
"""

from __future__ import annotations

import bisect
import csv
import json
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from model.risk_exact import MemoryGeometry, mission_probability_from_risk, q_acc_exact, risk_from_mission_probability
from model.schedule_compiler import normalize_period_set


CONFIG_PATH = REPO_ROOT / "configs" / "ch3_lag_sweep.json"
OUT_SUMMARY_CSV = REPO_ROOT / "results" / "schedules" / "ch3_lag_sweep_summary.csv"
OUT_CERT_MD = REPO_ROOT / "results" / "schedules" / "ch3_lag_sweep_certificate.md"
OUT_CERT_JSON = REPO_ROOT / "results" / "schedules" / "ch3_lag_sweep_certificate.json"


EPS_NU = 1e-30


@dataclass(frozen=True)
class VariantResult:
    family: str
    variant_key: str
    mode: str
    lag_hours: int | None
    hold_hours: int | None
    estimate_age_hours: int | None
    phase_hours: int | None
    aggregate: str
    c_value: float
    risk_e: float
    p_mission: float
    risk_utilization: float
    pass_count: float
    gain_fixed_over_strategy: float
    mean_tau_seconds: float
    min_tau_seconds: float
    max_tau_seconds: float
    saturated_at_tau_min: bool
    saturated_at_tau_max: bool
    max_q_per_pass: float
    max_hourly_risk_contribution_e: float
    max_hourly_budget_fraction: float
    verdict: str
    note: str = ""


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_series(path: Path) -> tuple[list[str], list[float], list[float]]:
    timestamps: list[str] = []
    nu_values: list[float] = []
    dt_hours: list[float] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            timestamps.append(row["timestamp_utc"])
            nu_values.append(float(row["upsets_total_nu"]))
            dt_hours.append(1.0)

    if not timestamps:
        raise RuntimeError("empty five-year series")

    return timestamps, nu_values, dt_hours


def lag_estimate(values: list[float], lag_hours: int) -> list[float]:
    if lag_hours < 0:
        raise ValueError("lag_hours must be non-negative")

    return [values[max(0, index - lag_hours)] for index in range(len(values))]


def hold_estimate(
    values: list[float],
    *,
    hold_hours: int,
    estimate_age_hours: int,
    phase_hours: int,
) -> list[float]:
    if hold_hours <= 0:
        raise ValueError("hold_hours must be positive")
    if estimate_age_hours < 0:
        raise ValueError("estimate_age_hours must be non-negative")
    if phase_hours < 0 or phase_hours >= hold_hours:
        raise ValueError("phase_hours must be in [0, hold_hours)")

    held: list[float] = []

    for index in range(len(values)):
        # Latest session on the shifted grid phase + k * U.
        if index >= phase_hours:
            session_index = phase_hours + ((index - phase_hours) // hold_hours) * hold_hours
        else:
            session_index = phase_hours - hold_hours

        source_index = max(0, session_index - estimate_age_hours)
        held.append(values[source_index])

    return held


def period_index_from_c(
    estimate_value: float,
    c_value: float,
    periods: tuple[float, ...],
) -> int:
    safe_estimate = max(estimate_value, EPS_NU)
    tau_calc_seconds = (c_value / safe_estimate) * 3600.0

    if tau_calc_seconds <= periods[0]:
        return 0
    if tau_calc_seconds >= periods[-1]:
        return len(periods) - 1

    return bisect.bisect_right(periods, tau_calc_seconds) - 1


def precompute_period_contributions(
    *,
    nu_values: list[float],
    dt_hours: list[float],
    periods: tuple[float, ...],
    geometry: MemoryGeometry,
) -> tuple[list[list[float]], list[list[float]], list[list[float]]]:
    risk_by_period: list[list[float]] = []
    q_by_period: list[list[float]] = []
    passes_by_period: list[list[float]] = []

    for period in periods:
        tau_hours = period / 3600.0
        risks: list[float] = []
        q_values: list[float] = []
        passes: list[float] = []

        for nu, dt in zip(nu_values, dt_hours, strict=True):
            lambda_value = nu * tau_hours
            q_value = q_acc_exact(lambda_value, geometry)
            q_values.append(q_value)
            risks.append((dt / tau_hours) * q_value)
            passes.append(dt / tau_hours)

        risk_by_period.append(risks)
        q_by_period.append(q_values)
        passes_by_period.append(passes)

    return risk_by_period, q_by_period, passes_by_period


def evaluate_c(
    *,
    family: str,
    variant_key: str,
    mode: str,
    estimate_values: list[float],
    c_value: float,
    periods: tuple[float, ...],
    risk_by_period: list[list[float]],
    q_by_period: list[list[float]],
    passes_by_period: list[list[float]],
    target_e: float,
    fixed_pass_count: float,
    lag_hours: int | None,
    hold_hours: int | None,
    estimate_age_hours: int | None,
    phase_hours: int | None,
    aggregate: str = "raw",
    note: str = "",
) -> VariantResult:
    risk_e = 0.0
    pass_count = 0.0
    tau_sum = 0.0
    min_tau = periods[-1]
    max_tau = periods[0]
    max_q = 0.0
    max_hourly_risk = 0.0

    for index, estimate in enumerate(estimate_values):
        period_index = period_index_from_c(estimate, c_value, periods)
        tau_seconds = periods[period_index]

        hourly_risk = risk_by_period[period_index][index]
        q_value = q_by_period[period_index][index]

        risk_e += hourly_risk
        pass_count += passes_by_period[period_index][index]
        tau_sum += tau_seconds
        min_tau = min(min_tau, tau_seconds)
        max_tau = max(max_tau, tau_seconds)
        max_q = max(max_q, q_value)
        max_hourly_risk = max(max_hourly_risk, hourly_risk)

    p_mission = mission_probability_from_risk(risk_e)
    utilization = risk_e / target_e
    verdict = "pass" if p_mission <= mission_probability_from_risk(target_e) + 1e-15 else "fail"

    return VariantResult(
        family=family,
        variant_key=variant_key,
        mode=mode,
        lag_hours=lag_hours,
        hold_hours=hold_hours,
        estimate_age_hours=estimate_age_hours,
        phase_hours=phase_hours,
        aggregate=aggregate,
        c_value=c_value,
        risk_e=risk_e,
        p_mission=p_mission,
        risk_utilization=utilization,
        pass_count=pass_count,
        gain_fixed_over_strategy=fixed_pass_count / pass_count,
        mean_tau_seconds=tau_sum / len(estimate_values),
        min_tau_seconds=min_tau,
        max_tau_seconds=max_tau,
        saturated_at_tau_min=(min_tau == periods[0]),
        saturated_at_tau_max=(max_tau == periods[-1]),
        max_q_per_pass=max_q,
        max_hourly_risk_contribution_e=max_hourly_risk,
        max_hourly_budget_fraction=max_hourly_risk / target_e,
        verdict=verdict,
        note=note,
    )


def find_largest_c(
    *,
    family: str,
    variant_key: str,
    estimate_values: list[float],
    periods: tuple[float, ...],
    risk_by_period: list[list[float]],
    q_by_period: list[list[float]],
    passes_by_period: list[list[float]],
    target_e: float,
    fixed_pass_count: float,
    lag_hours: int | None,
    hold_hours: int | None,
    estimate_age_hours: int | None,
    phase_hours: int | None,
    mode: str = "reoptimized",
) -> VariantResult:
    all_min = evaluate_c(
        family=family,
        variant_key=variant_key,
        mode=mode,
        estimate_values=estimate_values,
        c_value=0.0,
        periods=periods,
        risk_by_period=risk_by_period,
        q_by_period=q_by_period,
        passes_by_period=passes_by_period,
        target_e=target_e,
        fixed_pass_count=fixed_pass_count,
        lag_hours=lag_hours,
        hold_hours=hold_hours,
        estimate_age_hours=estimate_age_hours,
        phase_hours=phase_hours,
    )

    if all_min.risk_e > target_e:
        return VariantResult(**{**all_min.__dict__, "verdict": "fail", "note": "tau_min infeasible"})

    max_tau_hours = periods[-1] / 3600.0
    c_all_max = max(max(value, EPS_NU) * max_tau_hours for value in estimate_values)

    all_max = evaluate_c(
        family=family,
        variant_key=variant_key,
        mode=mode,
        estimate_values=estimate_values,
        c_value=c_all_max,
        periods=periods,
        risk_by_period=risk_by_period,
        q_by_period=q_by_period,
        passes_by_period=passes_by_period,
        target_e=target_e,
        fixed_pass_count=fixed_pass_count,
        lag_hours=lag_hours,
        hold_hours=hold_hours,
        estimate_age_hours=estimate_age_hours,
        phase_hours=phase_hours,
    )

    if all_max.risk_e <= target_e:
        return all_max

    low = 0.0
    high = c_all_max
    best = all_min

    for _ in range(90):
        mid = 0.5 * (low + high)
        candidate = evaluate_c(
            family=family,
            variant_key=variant_key,
            mode=mode,
            estimate_values=estimate_values,
            c_value=mid,
            periods=periods,
            risk_by_period=risk_by_period,
            q_by_period=q_by_period,
            passes_by_period=passes_by_period,
            target_e=target_e,
            fixed_pass_count=fixed_pass_count,
            lag_hours=lag_hours,
            hold_hours=hold_hours,
            estimate_age_hours=estimate_age_hours,
            phase_hours=phase_hours,
        )

        if candidate.risk_e <= target_e:
            low = mid
            best = candidate
        else:
            high = mid

    return best


def result_to_row(result: VariantResult) -> dict[str, str]:
    return {
        "family": result.family,
        "variant_key": result.variant_key,
        "mode": result.mode,
        "lag_hours": "" if result.lag_hours is None else str(result.lag_hours),
        "hold_hours": "" if result.hold_hours is None else str(result.hold_hours),
        "estimate_age_hours": "" if result.estimate_age_hours is None else str(result.estimate_age_hours),
        "phase_hours": "" if result.phase_hours is None else str(result.phase_hours),
        "aggregate": result.aggregate,
        "c_value": f"{result.c_value:.12g}",
        "risk_e": f"{result.risk_e:.12g}",
        "p_mission": f"{result.p_mission:.12g}",
        "risk_utilization": f"{result.risk_utilization:.12g}",
        "pass_count": f"{result.pass_count:.12g}",
        "gain_fixed_over_strategy": f"{result.gain_fixed_over_strategy:.12g}",
        "mean_tau_seconds": f"{result.mean_tau_seconds:.12g}",
        "min_tau_seconds": f"{result.min_tau_seconds:.12g}",
        "max_tau_seconds": f"{result.max_tau_seconds:.12g}",
        "saturated_at_tau_min": str(result.saturated_at_tau_min).lower(),
        "saturated_at_tau_max": str(result.saturated_at_tau_max).lower(),
        "max_q_per_pass": f"{result.max_q_per_pass:.12g}",
        "max_hourly_risk_contribution_e": f"{result.max_hourly_risk_contribution_e:.12g}",
        "max_hourly_budget_fraction": f"{result.max_hourly_budget_fraction:.12g}",
        "verdict": result.verdict,
        "note": result.note,
    }


def median_result(
    *,
    family: str,
    variant_key: str,
    mode: str,
    hold_hours: int,
    estimate_age_hours: int,
    phase_results: list[VariantResult],
) -> VariantResult:
    def med(field: str) -> float:
        return float(statistics.median(getattr(row, field) for row in phase_results))

    verdict = "pass" if all(row.verdict == "pass" for row in phase_results) else "fail"

    return VariantResult(
        family=family,
        variant_key=variant_key,
        mode=mode,
        lag_hours=None,
        hold_hours=hold_hours,
        estimate_age_hours=estimate_age_hours,
        phase_hours=None,
        aggregate="median_phase",
        c_value=med("c_value"),
        risk_e=med("risk_e"),
        p_mission=med("p_mission"),
        risk_utilization=med("risk_utilization"),
        pass_count=med("pass_count"),
        gain_fixed_over_strategy=med("gain_fixed_over_strategy"),
        mean_tau_seconds=med("mean_tau_seconds"),
        min_tau_seconds=med("min_tau_seconds"),
        max_tau_seconds=med("max_tau_seconds"),
        saturated_at_tau_min=any(row.saturated_at_tau_min for row in phase_results),
        saturated_at_tau_max=any(row.saturated_at_tau_max for row in phase_results),
        max_q_per_pass=med("max_q_per_pass"),
        max_hourly_risk_contribution_e=med("max_hourly_risk_contribution_e"),
        max_hourly_budget_fraction=med("max_hourly_budget_fraction"),
        verdict=verdict,
        note="median across phases; verdict requires all phases to pass",
    )


def write_summary(rows: list[VariantResult]) -> None:
    OUT_SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(result_to_row(rows[0]).keys())

    with OUT_SUMMARY_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for result in rows:
            writer.writerow(result_to_row(result))


def write_certificate(
    *,
    cfg: dict,
    rows: list[VariantResult],
    control_result: VariantResult,
    control_ok: bool,
) -> None:
    age_rows = [row for row in rows if row.family == "age" and row.aggregate == "raw"]
    session_worst = [row for row in rows if row.family == "session" and row.aggregate == "worst_phase"]
    session_median = [row for row in rows if row.family == "session" and row.aggregate == "median_phase"]

    lines = [
        "# Chapter 3 estimate-update-rate sensitivity certificate",
        "",
        "## Pre-registration",
        "",
        f"- Admissibility rule: {cfg['admissibility_rule']}",
        f"- Threshold rule: {cfg['threshold_rule']}",
        f"- Edge rule: {cfg['edge_rule']}",
        f"- Prediction recorded before inspecting results: {cfg['pre_registered_prediction']}",
        "",
        "Two calibration modes are reported:",
        "",
        "- `reoptimized`: each estimate stream receives its own exact-risk-calibrated C;",
        "- `frozen_1h`: the C calibrated for delayed_1h is reused after degrading the estimate-update channel.",
        "",
        "The `frozen_1h` mode is the operational degradation test. The `reoptimized`",
        "mode is a design curve showing how many extra passes are required if the",
        "communication cadence is known in advance.",
        "",
        "## Control check",
        "",
        f"- Control variant: `{control_result.variant_key}` / `{control_result.mode}`.",
        f"- Pass count: `{control_result.pass_count:.12g}`.",
        f"- P_mission: `{control_result.p_mission:.12g}`.",
        f"- max_q_per_pass: `{control_result.max_q_per_pass:.12g}`.",
        f"- Control verdict: `{'pass' if control_ok else 'fail'}`.",
        "",
        "## Age-family results",
        "",
        "| Mode | L, h | P mission | Risk util. | Passes | Fixed/gain | max q/pass | max hourly budget frac. | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in age_rows:
        lines.append(
            f"| {row.mode} | {row.lag_hours} | {row.p_mission:.12g} | {row.risk_utilization:.12g} | "
            f"{row.pass_count:.12g} | {row.gain_fixed_over_strategy:.12g} | "
            f"{row.max_q_per_pass:.12g} | {row.max_hourly_budget_fraction:.12g} | {row.verdict} |"
        )

    lines.extend(
        [
            "",
            "## Session-family aggregate results",
            "",
            "| Mode | U, h | Aggregate | Worst/median phase | P mission | Risk util. | Passes | Fixed/gain | max q/pass | Verdict |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for row in session_worst + session_median:
        phase = "-" if row.phase_hours is None else str(row.phase_hours)
        lines.append(
            f"| {row.mode} | {row.hold_hours} | {row.aggregate} | {phase} | "
            f"{row.p_mission:.12g} | {row.risk_utilization:.12g} | "
            f"{row.pass_count:.12g} | {row.gain_fixed_over_strategy:.12g} | "
            f"{row.max_q_per_pass:.12g} | {row.verdict} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation notes",
            "",
            "- `max_q_per_pass` is the largest exact accumulated-risk probability for one scrub cycle.",
            "- `max_hourly_budget_fraction` is the largest single-hour additive-risk contribution divided by the five-year target E.",
            "- For session variants, `worst_phase` is selected by maximum risk utilization.",
            "- A session cadence is considered admissible only if all phases pass.",
            "",
        ]
    )

    OUT_CERT_MD.write_text("\n".join(lines), encoding="utf-8")

    with OUT_CERT_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "config": cfg,
                "control_ok": control_ok,
                "control": result_to_row(control_result),
                "rows": [result_to_row(row) for row in rows],
            },
            file,
            indent=2,
            ensure_ascii=False,
        )


def main() -> int:
    cfg = read_json(CONFIG_PATH)
    base_config = read_json(REPO_ROOT / cfg["base_config"])

    timestamps, nu_values, dt_hours = read_series(REPO_ROOT / cfg["series_path"])
    del timestamps

    target_p = float(cfg["target_mission_probability"])
    target_e = risk_from_mission_probability(target_p)

    geometry_cfg = base_config["geometry"]
    geometry = MemoryGeometry(
        word_bits=int(geometry_cfg["word_bits"]),
        codeword_count=int(geometry_cfg["codeword_count"]),
    )

    periods = normalize_period_set(float(value) for value in base_config["period_set_seconds"])

    print("Precomputing exact q/risk contribution matrix...")
    risk_by_period, q_by_period, passes_by_period = precompute_period_contributions(
        nu_values=nu_values,
        dt_hours=dt_hours,
        periods=periods,
        geometry=geometry,
    )

    # Fixed 5 s pass count from the allowed fixed baseline used in Chapter 3.
    fixed_index = periods.index(5.0)
    fixed_pass_count = sum(passes_by_period[fixed_index])

    print("Calibrating delayed_1h control...")
    delayed_1h_estimate = lag_estimate(nu_values, 1)
    delayed_1h = find_largest_c(
        family="age",
        variant_key="age_L1",
        mode="reoptimized",
        estimate_values=delayed_1h_estimate,
        periods=periods,
        risk_by_period=risk_by_period,
        q_by_period=q_by_period,
        passes_by_period=passes_by_period,
        target_e=target_e,
        fixed_pass_count=fixed_pass_count,
        lag_hours=1,
        hold_hours=None,
        estimate_age_hours=None,
        phase_hours=None,
    )
    frozen_c = delayed_1h.c_value

    control_cfg = cfg["control"]
    control_ok = (
        abs(delayed_1h.pass_count - float(control_cfg["expected_pass_count"]))
        <= float(control_cfg["pass_count_tolerance"])
        and abs(delayed_1h.p_mission - float(control_cfg["expected_p_mission"]))
        <= float(control_cfg["p_mission_tolerance"])
    )

    expected_q = control_cfg.get("expected_max_q_per_pass_approx")
    if expected_q is not None:
        expected_q = float(expected_q)
        rel = abs(delayed_1h.max_q_per_pass - expected_q) / expected_q
        control_ok = control_ok and rel <= float(control_cfg["max_q_relative_tolerance"])

    if not control_ok:
        write_summary([delayed_1h])
        write_certificate(cfg=cfg, rows=[delayed_1h], control_result=delayed_1h, control_ok=False)
        raise SystemExit(
            "Control L=1 did not reproduce the existing delayed_1h certificate. "
            "Inspect results/schedules/ch3_lag_sweep_certificate.md before continuing."
        )

    rows: list[VariantResult] = []

    print("Running age-family sweep...")
    for lag in cfg["age_family_lag_hours"]:
        lag = int(lag)
        estimate = lag_estimate(nu_values, lag)

        reopt = find_largest_c(
            family="age",
            variant_key=f"age_L{lag}",
            mode="reoptimized",
            estimate_values=estimate,
            periods=periods,
            risk_by_period=risk_by_period,
            q_by_period=q_by_period,
            passes_by_period=passes_by_period,
            target_e=target_e,
            fixed_pass_count=fixed_pass_count,
            lag_hours=lag,
            hold_hours=None,
            estimate_age_hours=None,
            phase_hours=None,
        )
        rows.append(reopt)

        frozen = evaluate_c(
            family="age",
            variant_key=f"age_L{lag}",
            mode="frozen_1h",
            estimate_values=estimate,
            c_value=frozen_c,
            periods=periods,
            risk_by_period=risk_by_period,
            q_by_period=q_by_period,
            passes_by_period=passes_by_period,
            target_e=target_e,
            fixed_pass_count=fixed_pass_count,
            lag_hours=lag,
            hold_hours=None,
            estimate_age_hours=None,
            phase_hours=None,
        )
        rows.append(frozen)

    print("Running session-family sweep over phases...")
    estimate_age = int(cfg["session_estimate_age_hours"])
    for hold in cfg["session_family_hold_hours"]:
        hold = int(hold)
        for mode in cfg["modes"]:
            phase_results: list[VariantResult] = []

            for phase in range(hold):
                estimate = hold_estimate(
                    nu_values,
                    hold_hours=hold,
                    estimate_age_hours=estimate_age,
                    phase_hours=phase,
                )

                if mode == "reoptimized":
                    result = find_largest_c(
                        family="session",
                        variant_key=f"session_U{hold}_A{estimate_age}_P{phase}",
                        mode=mode,
                        estimate_values=estimate,
                        periods=periods,
                        risk_by_period=risk_by_period,
                        q_by_period=q_by_period,
                        passes_by_period=passes_by_period,
                        target_e=target_e,
                        fixed_pass_count=fixed_pass_count,
                        lag_hours=None,
                        hold_hours=hold,
                        estimate_age_hours=estimate_age,
                        phase_hours=phase,
                    )
                elif mode == "frozen_1h":
                    result = evaluate_c(
                        family="session",
                        variant_key=f"session_U{hold}_A{estimate_age}_P{phase}",
                        mode=mode,
                        estimate_values=estimate,
                        c_value=frozen_c,
                        periods=periods,
                        risk_by_period=risk_by_period,
                        q_by_period=q_by_period,
                        passes_by_period=passes_by_period,
                        target_e=target_e,
                        fixed_pass_count=fixed_pass_count,
                        lag_hours=None,
                        hold_hours=hold,
                        estimate_age_hours=estimate_age,
                        phase_hours=phase,
                    )
                else:
                    raise ValueError(f"unknown mode: {mode}")

                rows.append(result)
                phase_results.append(result)

            worst = max(phase_results, key=lambda row: row.risk_utilization)
            rows.append(
                VariantResult(
                    **{
                        **worst.__dict__,
                        "variant_key": f"session_U{hold}_A{estimate_age}_worst_phase",
                        "aggregate": "worst_phase",
                        "note": f"worst phase selected by risk_utilization; phase={worst.phase_hours}",
                    }
                )
            )

            rows.append(
                median_result(
                    family="session",
                    variant_key=f"session_U{hold}_A{estimate_age}_median_phase",
                    mode=mode,
                    hold_hours=hold,
                    estimate_age_hours=estimate_age,
                    phase_results=phase_results,
                )
            )

    write_summary(rows)
    write_certificate(cfg=cfg, rows=rows, control_result=delayed_1h, control_ok=True)

    print("Wrote", OUT_SUMMARY_CSV)
    print("Wrote", OUT_CERT_MD)
    print("Wrote", OUT_CERT_JSON)
    print()
    print(OUT_CERT_MD.read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
