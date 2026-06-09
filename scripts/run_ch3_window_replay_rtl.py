#!/usr/bin/env python3
"""Replay selected Chapter 3 schedule windows on the RTL controller.

This is the dissertation-scale model-to-RTL bridge:
  five-year model schedule -> selected period_index windows -> RTL execution.

The RTL controller is not given nu(t), risk, or the radiation model.  It only
receives period_index updates.
"""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "rtl_replay"
BUILD_DIR = REPO_ROOT / "generated" / "rtl"
GENERATED_TB_DIR = BUILD_DIR / "ch3_window_replay"

WINDOWS_PATH = REPO_ROOT / "results" / "schedules" / "ch3_replay_windows.csv"
PERIOD_TABLE_PATH = REPO_ROOT / "results" / "schedules" / "ch3_period_table.csv"

SCHEDULE_PATHS = {
    "current": REPO_ROOT / "results" / "schedules" / "ch3_five_year_schedule_current.csv",
    "delayed_1h": REPO_ROOT / "results" / "schedules" / "ch3_five_year_schedule_delayed_1h.csv",
    "forecast": REPO_ROOT / "results" / "schedules" / "ch3_five_year_schedule_forecast.csv",
}

# 1 second in the Chapter 3 schedule is represented by this many RTL cycles.
# DEPTH=4 keeps a full scrub pass shorter than the 1-second period and keeps
# the replay compact. The purpose of this replay is schedule execution, not
# large-memory capacity emulation.
SCALE_CYCLES_PER_SECOND = 32
DEPTH = 4
ADDR_WIDTH = 2


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
    rows = read_csv(PERIOD_TABLE_PATH)
    periods = [float(row["tau_seconds"]) for row in rows]

    if len(periods) != 12:
        raise RuntimeError(f"expected 12 Chapter 3 periods, got {len(periods)}")

    return periods


def load_schedule_rows(strategy: str) -> list[dict[str, str]]:
    rows = read_csv(SCHEDULE_PATHS[strategy])

    if not rows:
        raise RuntimeError(f"empty schedule for {strategy}")

    return rows


def window_schedule_rows(schedule_rows: list[dict[str, str]], window: dict[str, str]) -> list[dict[str, str]]:
    start = int(window["start_index"])
    end = int(window["end_index"])

    subset = schedule_rows[start : end + 1]

    if len(subset) != int(window["hours"]):
        raise RuntimeError(f"window length mismatch for {window['window_name']}")

    return subset


def expected_pass_count(rows: list[dict[str, str]]) -> int:
    total = 0.0

    for row in rows:
        total += float(row["passes"])

    rounded = int(round(total))

    if abs(total - rounded) > 1e-6:
        raise RuntimeError(f"expected pass count is not integral: {total}")

    return rounded


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


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", value)


def generate_tb(strategy: str, window: dict[str, str], periods: list[float], rows: list[dict[str, str]]) -> Path:
    window_name = safe_name(window["window_name"])
    tb_name = f"tb_ch3_window_replay_{strategy}_{window_name}"

    cycles, indices, mission_cycles = event_cycles_and_indices(rows)
    expected_passes = expected_pass_count(rows)

    period_params = []
    for idx, seconds in enumerate(periods):
        cycles_value = int(round(seconds * SCALE_CYCLES_PER_SECOND))
        period_params.append(f"        .PERIOD{idx}_CYCLES({cycles_value})")

    event_init = "\n".join(
        f"        event_cycle[{idx}] = {cycle}; event_index[{idx}] = 4'd{index};"
        for idx, (cycle, index) in enumerate(zip(cycles, indices, strict=True))
    )

    tb_path = GENERATED_TB_DIR / f"{tb_name}.sv"
    tb_path.parent.mkdir(parents=True, exist_ok=True)

    tb_path.write_text(
        f"""// Auto-generated Chapter 3 window replay testbench.
// strategy: {strategy}
// window:   {window['window_name']}
// start:    {window['start_timestamp_utc']}
// end:      {window['end_timestamp_utc']}

`timescale 1ns/1ps

module {tb_name};

    localparam int ADDR_WIDTH = {ADDR_WIDTH};
    localparam int DEPTH = {DEPTH};
    localparam int PERIOD_INDEX_WIDTH = 4;
    localparam int NUM_EVENTS = {len(cycles)};
    localparam int MISSION_CYCLES = {mission_cycles};
    localparam int EXPECTED_PASS_COUNT = {expected_passes};

    logic clk;
    logic reset_n;

    logic period_update_valid;
    logic [PERIOD_INDEX_WIDTH-1:0] period_index;

    logic mem_read_en;
    logic mem_write_en;
    logic [ADDR_WIDTH-1:0] mem_addr;
    logic [38:0] mem_read_data;
    logic [38:0] mem_write_data;

    logic pass_start;
    logic pass_active;
    logic pass_done;

    logic [PERIOD_INDEX_WIDTH-1:0] applied_period_index;
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
        .PERIOD_INDEX_WIDTH(PERIOD_INDEX_WIDTH),
{",\n".join(period_params)},
        .SAFE_PERIOD_INDEX(0),
        .MAX_CONTROL_AGE_CYCLES(32'h7fff_ffff)
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
{event_init}
    end

    initial begin
        failures = 0;
        period_updates_applied = 0;
        pass_starts_observed = 0;
        safe_mode_observed_after_update = 0;
        selected_period_mismatches = 0;

        period_update_valid = 1'b0;
        period_index = 4'd0;
        next_event = 0;
        mission_cycle = 0;

        reset_n = 1'b0;

        for (addr = 0; addr < DEPTH; addr = addr + 1) begin
            encoder_data = 32'h6000_0000 + addr[31:0];
            #1;
            memory[addr] = encoder_codeword;
        end

        repeat (5) @(posedge clk);
        reset_n = 1'b1;

        while (mission_cycle < MISSION_CYCLES) begin
            period_update_valid = 1'b0;

            if ((next_event < NUM_EVENTS) && (mission_cycle == event_cycle[next_event])) begin
                period_index = event_index[next_event][PERIOD_INDEX_WIDTH-1:0];
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
        check_condition(pass_starts_observed == EXPECTED_PASS_COUNT, "pass_start count does not match model expectation");
        check_condition(pass_count == EXPECTED_PASS_COUNT, "completed pass count does not match model expectation");
        check_condition(read_count == pass_count * DEPTH, "read count is inconsistent with completed passes");
        check_condition(write_count == 0, "clean replay should not write corrected data");
        check_condition(corrected_count == 0, "clean replay should not correct data");
        check_condition(detected_uncorrectable_count == 0, "clean replay should not detect DUE");

        $display("CH3_WINDOW_REPLAY_SUMMARY strategy={strategy} window={window['window_name']} mission_cycles=%0d period_updates=%0d expected_passes=%0d observed_pass_starts=%0d completed_passes=%0d reads=%0d writes=%0d safe_mode_cycles=%0d selected_mismatches=%0d failures=%0d",
                 MISSION_CYCLES,
                 period_updates_applied,
                 EXPECTED_PASS_COUNT,
                 pass_starts_observed,
                 pass_count,
                 read_count,
                 write_count,
                 safe_mode_observed_after_update,
                 selected_period_mismatches,
                 failures);

        if (failures != 0) begin
            $fatal(1, "Chapter 3 window replay failed with %0d failures", failures);
        end

        $display("CH3_WINDOW_REPLAY_PASS strategy={strategy} window={window['window_name']}");
        $finish;
    end

endmodule
""",
        encoding="utf-8",
    )

    return tb_path


def compile_and_run(strategy: str, window: dict[str, str], tb_path: Path) -> tuple[str, dict[str, int]]:
    window_name = safe_name(window["window_name"])
    sim_out = BUILD_DIR / f"tb_ch3_window_replay_{strategy}_{window_name}.vvp"
    log_path = RESULT_DIR / f"ch3_window_replay_{strategy}_{window_name}.log"

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
        raise RuntimeError(f"compile failed for {strategy}/{window['window_name']}")

    run_proc = run_cmd(["vvp", str(sim_out)])
    log_path.write_text(compile_proc.stdout + run_proc.stdout, encoding="utf-8")
    print(run_proc.stdout)

    if run_proc.returncode != 0:
        raise RuntimeError(f"simulation failed for {strategy}/{window['window_name']}")

    pattern = (
        rf"CH3_WINDOW_REPLAY_SUMMARY strategy={strategy} window={window['window_name']} "
        rf"mission_cycles=(\d+) period_updates=(\d+) expected_passes=(\d+) "
        rf"observed_pass_starts=(\d+) completed_passes=(\d+) reads=(\d+) "
        rf"writes=(\d+) safe_mode_cycles=(\d+) selected_mismatches=(\d+) failures=(\d+)"
    )

    match = re.search(pattern, run_proc.stdout)

    if not match:
        raise RuntimeError(f"could not parse summary for {strategy}/{window['window_name']}")

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
    summary_csv = RESULT_DIR / "ch3_window_replay_summary.csv"
    certificate_md = RESULT_DIR / "ch3_model_vs_rtl_window_certificate.md"

    fieldnames = [
        "strategy",
        "window_name",
        "start_timestamp_utc",
        "end_timestamp_utc",
        "hours",
        "mission_cycles",
        "period_updates",
        "expected_passes",
        "observed_pass_starts",
        "completed_passes",
        "pass_start_delta_vs_expected",
        "completed_delta_vs_expected",
        "reads",
        "writes",
        "safe_mode_cycles",
        "selected_mismatches",
        "failures",
        "log_path",
    ]

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    with summary_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Chapter 3 model-to-RTL window replay certificate",
        "",
        "The RTL controller receives only `period_index` updates. It does not receive",
        "`nu(t)`, risk values, or the radiation model.",
        "",
        "| Strategy | Window | Expected passes | RTL pass starts | Completed passes | Reads | Safe cycles | Mismatches | Failures |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            f"| {row['strategy']} | {row['window_name']} | {row['expected_passes']} | "
            f"{row['observed_pass_starts']} | {row['completed_passes']} | {row['reads']} | "
            f"{row['safe_mode_cycles']} | {row['selected_mismatches']} | {row['failures']} |"
        )

    lines.append("")
    certificate_md.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote", summary_csv)
    print("Wrote", certificate_md)


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    periods = load_period_table()
    windows = read_csv(WINDOWS_PATH)

    schedule_by_strategy = {
        strategy: load_schedule_rows(strategy)
        for strategy in SCHEDULE_PATHS
    }

    rows_for_summary: list[dict[str, str]] = []

    for window in windows:
        for strategy in ("current", "delayed_1h", "forecast"):
            subset = window_schedule_rows(schedule_by_strategy[strategy], window)
            tb_path = generate_tb(strategy, window, periods, subset)
            log_path, values = compile_and_run(strategy, window, tb_path)

            expected = values["expected_passes"]
            observed = values["observed_pass_starts"]
            completed = values["completed_passes"]

            row = {
                "strategy": strategy,
                "window_name": window["window_name"],
                "start_timestamp_utc": window["start_timestamp_utc"],
                "end_timestamp_utc": window["end_timestamp_utc"],
                "hours": window["hours"],
                **{key: str(value) for key, value in values.items()},
                "pass_start_delta_vs_expected": str(observed - expected),
                "completed_delta_vs_expected": str(completed - expected),
                "log_path": log_path,
            }

            rows_for_summary.append(row)

    write_summary(rows_for_summary)

    print()
    for row in rows_for_summary:
        print(
            f"{row['strategy']}/{row['window_name']}: "
            f"expected={row['expected_passes']} observed={row['observed_pass_starts']} "
            f"completed={row['completed_passes']} mismatches={row['selected_mismatches']} "
            f"failures={row['failures']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
