#!/usr/bin/env python3
"""Replay model-generated period-index schedules on the integrated RTL controller."""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "rtl_replay"
BUILD_DIR = REPO_ROOT / "generated" / "rtl"
GENERATED_TB_DIR = BUILD_DIR / "schedule_replay"


SCALE_CYCLES_PER_SECOND = 10
DEPTH = 8
ADDR_WIDTH = 3


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def load_period_table() -> list[float]:
    rows = read_csv(REPO_ROOT / "results" / "schedules" / "period_table.csv")
    periods: list[float] = []

    for row in rows:
        periods.append(float(row["tau_seconds"]))

    if len(periods) != 8:
        raise RuntimeError(
            f"RTL scheduler has 8 period entries, but period_table.csv has {len(periods)}"
        )

    return periods


def load_schedule(strategy: str) -> list[dict[str, str]]:
    path = REPO_ROOT / "results" / "schedules" / f"schedule_{strategy}.csv"
    rows = read_csv(path)

    if not rows:
        raise RuntimeError(f"empty schedule: {path}")

    return rows


def expected_pass_count(rows: list[dict[str, str]]) -> float:
    total = 0.0
    for row in rows:
        tau_seconds = float(row["tau_seconds"])
        dt_hours = float(row["dt_hours"])
        total += dt_hours * 3600.0 / tau_seconds
    return total


def event_cycles_and_indices(rows: list[dict[str, str]]) -> tuple[list[int], list[int], int]:
    cycles: list[int] = []
    indices: list[int] = []
    current_cycle = 0

    for row in rows:
        cycles.append(current_cycle)
        indices.append(int(row["period_index"]))

        dt_seconds = float(row["dt_hours"]) * 3600.0
        current_cycle += int(round(dt_seconds * SCALE_CYCLES_PER_SECOND))

    return cycles, indices, current_cycle


def generate_tb(strategy: str, periods: list[float], rows: list[dict[str, str]]) -> Path:
    cycles, indices, mission_cycles = event_cycles_and_indices(rows)

    period_params = []
    for idx, seconds in enumerate(periods):
        cycles_value = int(round(seconds * SCALE_CYCLES_PER_SECOND))
        period_params.append(f"        .PERIOD{idx}_CYCLES({cycles_value})")

    event_cycle_init = "\n".join(
        f"        event_cycle[{idx}] = {cycle}; event_index[{idx}] = 3'd{index};"
        for idx, (cycle, index) in enumerate(zip(cycles, indices, strict=True))
    )

    tb_path = GENERATED_TB_DIR / f"tb_schedule_replay_{strategy}.sv"
    tb_path.parent.mkdir(parents=True, exist_ok=True)

    tb_path.write_text(
        f"""// Auto-generated schedule replay testbench for strategy: {strategy}

`timescale 1ns/1ps

module tb_schedule_replay_{strategy};

    localparam int ADDR_WIDTH = {ADDR_WIDTH};
    localparam int DEPTH = {DEPTH};
    localparam int NUM_EVENTS = {len(cycles)};
    localparam int MISSION_CYCLES = {mission_cycles};
    localparam int EXPECTED_PASS_COUNT_ROUNDED = {int(round(expected_pass_count(rows)))};

    logic clk;
    logic reset_n;

    logic period_update_valid;
    logic [2:0] period_index;

    logic mem_read_en;
    logic mem_write_en;
    logic [ADDR_WIDTH-1:0] mem_addr;
    logic [38:0] mem_read_data;
    logic [38:0] mem_write_data;

    logic pass_start;
    logic pass_active;
    logic pass_done;

    logic [2:0] applied_period_index;
    logic [31:0] selected_period_cycles;
    logic safe_mode_active;
    logic stale_control_flag;
    logic [31:0] last_pass_cycles;

    logic corrected_pulse;
    logic detected_uncorrectable_pulse;

    logic [31:0] pass_count;
    logic [31:0] read_count;
    logic [31:0] write_count;
    logic [31:0] corrected_count;
    logic [31:0] detected_uncorrectable_count;
    logic [31:0] safe_mode_entry_count;

    logic [38:0] memory [0:DEPTH-1];

    logic [31:0] encoder_data;
    logic [38:0] encoder_codeword;

    integer event_cycle [0:NUM_EVENTS-1];
    integer event_index [0:NUM_EVENTS-1];

    integer addr;
    integer mission_cycle;
    integer next_event;
    integer failures;
    integer period_updates_applied;
    integer pass_starts_observed;
    integer safe_mode_observed_after_update;
    integer selected_period_mismatches;

    secded_32_39_encoder encoder (
        .data_in(encoder_data),
        .codeword_out(encoder_codeword)
    );

    adaptive_scrub_controller #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DEPTH(DEPTH),
{",\n".join(period_params)},
        .SAFE_PERIOD_INDEX(0),
        .MAX_CONTROL_AGE_CYCLES(1000000000)
    ) dut (
        .clk(clk),
        .reset_n(reset_n),
        .time_tick(1'b1),
        .period_update_valid(period_update_valid),
        .period_index(period_index),
        .mem_read_en(mem_read_en),
        .mem_write_en(mem_write_en),
        .mem_addr(mem_addr),
        .mem_read_data(mem_read_data),
        .mem_write_data(mem_write_data),
        .pass_start(pass_start),
        .pass_active(pass_active),
        .pass_done(pass_done),
        .applied_period_index(applied_period_index),
        .selected_period_cycles(selected_period_cycles),
        .safe_mode_active(safe_mode_active),
        .stale_control_flag(stale_control_flag),
        .last_pass_cycles(last_pass_cycles),
        .corrected_pulse(corrected_pulse),
        .detected_uncorrectable_pulse(detected_uncorrectable_pulse),
        .pass_count(pass_count),
        .read_count(read_count),
        .write_count(write_count),
        .corrected_count(corrected_count),
        .detected_uncorrectable_count(detected_uncorrectable_count),
        .safe_mode_entry_count(safe_mode_entry_count)
    );

    assign mem_read_data = memory[mem_addr];

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    always_ff @(posedge clk) begin
        if (mem_write_en) begin
            memory[mem_addr] <= mem_write_data;
        end
    end

    task automatic check_condition(input bit condition, input string message);
        begin
            if (!condition) begin
                $display("FAIL: %s", message);
                failures = failures + 1;
            end
        end
    endtask

    initial begin
{event_cycle_init}
    end

    initial begin
        failures = 0;
        period_updates_applied = 0;
        pass_starts_observed = 0;
        safe_mode_observed_after_update = 0;
        selected_period_mismatches = 0;

        period_update_valid = 1'b0;
        period_index = 3'd0;
        next_event = 0;
        mission_cycle = 0;

        reset_n = 1'b0;

        for (addr = 0; addr < DEPTH; addr = addr + 1) begin
            encoder_data = 32'h5000_0000 + addr[31:0];
            #1;
            memory[addr] = encoder_codeword;
        end

        repeat (5) @(posedge clk);
        reset_n = 1'b1;

        while (mission_cycle < MISSION_CYCLES) begin
            period_update_valid = 1'b0;

            if ((next_event < NUM_EVENTS) && (mission_cycle == event_cycle[next_event])) begin
                period_index = event_index[next_event][2:0];
                period_update_valid = 1'b1;
                period_updates_applied = period_updates_applied + 1;
                next_event = next_event + 1;
            end

            @(posedge clk);

            if (pass_start) begin
                pass_starts_observed = pass_starts_observed + 1;
            end

            if ((period_updates_applied > 0) && safe_mode_active) begin
                safe_mode_observed_after_update = safe_mode_observed_after_update + 1;
            end

            if (period_update_valid) begin
                #1;
                if (applied_period_index !== period_index) begin
                    selected_period_mismatches = selected_period_mismatches + 1;
                end
            end

            mission_cycle = mission_cycle + 1;
        end

        check_condition(period_updates_applied == NUM_EVENTS, "not all period events were applied");
        check_condition(selected_period_mismatches == 0, "selected period index mismatch during updates");
        check_condition(safe_mode_observed_after_update == 0, "safe mode asserted after valid schedule updates");
        check_condition(pass_starts_observed > 0, "no pass_start events observed");
        check_condition(pass_count > 0, "pass_count did not increment");
        check_condition(read_count >= pass_count * DEPTH, "read_count is inconsistent with completed passes");

        $display("SCHEDULE_REPLAY_SUMMARY strategy={strategy} mission_cycles=%0d period_updates=%0d expected_passes=%0d observed_pass_starts=%0d completed_passes=%0d reads=%0d writes=%0d safe_mode_cycles=%0d selected_mismatches=%0d failures=%0d",
                 MISSION_CYCLES,
                 period_updates_applied,
                 EXPECTED_PASS_COUNT_ROUNDED,
                 pass_starts_observed,
                 pass_count,
                 read_count,
                 write_count,
                 safe_mode_observed_after_update,
                 selected_period_mismatches,
                 failures);

        if (failures != 0) begin
            $fatal(1, "schedule replay failed with %0d failures", failures);
        end

        $display("SCHEDULE_REPLAY_PASS strategy={strategy}");
        $finish;
    end

endmodule
""",
        encoding="utf-8",
    )

    return tb_path


def compile_and_run(strategy: str, tb_path: Path) -> tuple[str, dict[str, int]]:
    sim_out = BUILD_DIR / f"tb_schedule_replay_{strategy}.vvp"
    log_path = RESULT_DIR / f"schedule_replay_{strategy}.log"

    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-o",
        str(sim_out),
        "rtl/ecc/secded_32_39_encoder.sv",
        "rtl/ecc/secded_32_39_decoder.sv",
        "rtl/scrubber/period_scheduler.sv",
        "rtl/scrubber/scrub_pass_engine.sv",
        "rtl/scrubber/diagnostic_supervisor.sv",
        "rtl/scrubber/adaptive_scrub_controller.sv",
        str(tb_path),
    ]

    compile_proc = run_cmd(compile_cmd)

    if compile_proc.returncode != 0:
        log_path.write_text(compile_proc.stdout, encoding="utf-8")
        print(compile_proc.stdout)
        raise RuntimeError(f"compile failed for {strategy}")

    run_proc = run_cmd(["vvp", str(sim_out)])
    log_path.write_text(compile_proc.stdout + run_proc.stdout, encoding="utf-8")
    print(run_proc.stdout)

    if run_proc.returncode != 0:
        raise RuntimeError(f"simulation failed for {strategy}")

    pattern = (
        rf"SCHEDULE_REPLAY_SUMMARY strategy={strategy} mission_cycles=(\d+) "
        rf"period_updates=(\d+) expected_passes=(\d+) observed_pass_starts=(\d+) "
        rf"completed_passes=(\d+) reads=(\d+) writes=(\d+) safe_mode_cycles=(\d+) "
        rf"selected_mismatches=(\d+) failures=(\d+)"
    )

    match = re.search(pattern, run_proc.stdout)

    if not match:
        raise RuntimeError(f"could not parse schedule replay summary for {strategy}")

    keys = [
        "mission_cycles",
        "period_updates",
        "expected_passes",
        "observed_pass_starts",
        "completed_passes",
        "reads",
        "writes",
        "safe_mode_cycles",
        "selected_mismatches",
        "failures",
    ]

    values = {key: int(value) for key, value in zip(keys, match.groups(), strict=True)}
    return str(log_path.relative_to(REPO_ROOT)), values


def write_summary(rows: list[dict[str, str]]) -> None:
    summary_csv = RESULT_DIR / "schedule_replay_summary.csv"
    summary_md = RESULT_DIR / "model_vs_rtl_schedule_certificate.md"

    fieldnames = [
        "strategy",
        "mission_cycles",
        "period_updates",
        "expected_passes",
        "observed_pass_starts",
        "completed_passes",
        "pass_start_delta_vs_expected",
        "reads",
        "writes",
        "safe_mode_cycles",
        "selected_mismatches",
        "failures",
        "log_path",
    ]

    with summary_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Model-to-RTL schedule replay certificate",
        "",
        "| Strategy | Expected passes | Observed pass starts | Completed passes | Reads | Safe cycles | Mismatches | Failures |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            "| {strategy} | {expected_passes} | {observed_pass_starts} | {completed_passes} | "
            "{reads} | {safe_mode_cycles} | {selected_mismatches} | {failures} |".format(**row)
        )

    lines.extend(
        [
            "",
            "The replay uses the model-generated schedule CSV files and converts their",
            "period indices into RTL period update events. The controller is not given",
            "the radiation/risk model; it only receives period indices.",
            "",
        ]
    )

    summary_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Regenerate schedules so period_table.csv is consistent with the 8-entry RTL table.
    schedule_proc = run_cmd(["python3", "scripts/run_schedule_demo.py"])
    print(schedule_proc.stdout)
    if schedule_proc.returncode != 0:
        return schedule_proc.returncode

    periods = load_period_table()

    rows_for_summary: list[dict[str, str]] = []

    for strategy in ("fixed", "adaptive"):
        schedule_rows = load_schedule(strategy)
        tb_path = generate_tb(strategy, periods, schedule_rows)
        log_path, values = compile_and_run(strategy, tb_path)

        expected = values["expected_passes"]
        observed = values["observed_pass_starts"]

        row = {
            "strategy": strategy,
            **{key: str(value) for key, value in values.items()},
            "pass_start_delta_vs_expected": str(observed - expected),
            "log_path": log_path,
        }

        rows_for_summary.append(row)

    write_summary(rows_for_summary)

    print("Schedule replay summary written to", RESULT_DIR / "schedule_replay_summary.csv")

    for row in rows_for_summary:
        print(
            f"{row['strategy']}: expected={row['expected_passes']} "
            f"observed={row['observed_pass_starts']} "
            f"completed={row['completed_passes']} reads={row['reads']} "
            f"failures={row['failures']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
