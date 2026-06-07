#!/usr/bin/env python3
"""Replay an external fault-event stream on fixed and adaptive RTL schedules."""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "rtl_replay"
BUILD_DIR = REPO_ROOT / "generated" / "rtl"
GENERATED_TB_DIR = BUILD_DIR / "fault_replay"

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


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_mask(bit_index: int) -> int:
    if bit_index < 0 or bit_index >= 39:
        raise ValueError(f"bit_index out of range: {bit_index}")
    return 1 << bit_index


def generate_fault_events() -> list[dict[str, str]]:
    """
    Deterministic replay stream.

    The stream includes:
      - one single-bit accumulated error;
      - one split MBU mapped to three different codewords;
      - one same-word double-bit DUE;
      - one same-word triple-bit pattern that can become SDC after false correction.
    """
    raw_events = [
        # cycle, physical_event_id, event_type, addr, bit, multiplicity, D
        (1000, 1, "single_accumulation", 1, 7, 1, 1),

        (5000, 2, "mbu_split_interleaved", 2, 2, 3, 3),
        (5000, 2, "mbu_split_interleaved", 3, 3, 3, 3),
        (5000, 2, "mbu_split_interleaved", 4, 4, 3, 3),

        (7000, 3, "mbu_same_word_due", 5, 3, 2, 1),
        (7000, 3, "mbu_same_word_due", 5, 10, 2, 1),

        # Bits 4,5,6 have syndrome 4 in this code mapping, causing a false
        # correction of parity position 4 and leaving data corrupted.
        (9000, 4, "triple_same_word_sdc", 6, 4, 3, 1),
        (9000, 4, "triple_same_word_sdc", 6, 5, 3, 1),
        (9000, 4, "triple_same_word_sdc", 6, 6, 3, 1),
    ]

    rows: list[dict[str, str]] = []

    for event_id, item in enumerate(raw_events):
        cycle, physical_id, event_type, addr, bit, multiplicity, interleave_depth = item
        rows.append(
            {
                "event_id": str(event_id),
                "cycle": str(cycle),
                "physical_event_id": str(physical_id),
                "event_type": event_type,
                "addr": str(addr),
                "bit_index": str(bit),
                "bit_mask_hex": f"{make_mask(bit):010x}",
                "multiplicity": str(multiplicity),
                "interleave_depth": str(interleave_depth),
            }
        )

    return rows


def load_period_table() -> list[float]:
    rows = read_csv(REPO_ROOT / "results" / "schedules" / "period_table.csv")
    periods = [float(row["tau_seconds"]) for row in rows]

    if len(periods) != 8:
        raise RuntimeError(f"expected 8 RTL period entries, got {len(periods)}")

    return periods


def load_schedule(strategy: str) -> list[dict[str, str]]:
    return read_csv(REPO_ROOT / "results" / "schedules" / f"schedule_{strategy}.csv")


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


def expected_pass_count(rows: list[dict[str, str]]) -> int:
    total = 0.0

    for row in rows:
        total += float(row["dt_hours"]) * 3600.0 / float(row["tau_seconds"])

    return int(round(total))


def generate_tb(
    strategy: str,
    periods: list[float],
    schedule_rows: list[dict[str, str]],
    fault_rows: list[dict[str, str]],
) -> Path:
    schedule_cycles, schedule_indices, mission_cycles = event_cycles_and_indices(schedule_rows)

    period_params_block = ",\n".join(
        f"        .PERIOD{idx}_CYCLES({int(round(seconds * SCALE_CYCLES_PER_SECOND))})"
        for idx, seconds in enumerate(periods)
    )

    schedule_init = "\n".join(
        f"        schedule_cycle[{idx}] = {cycle}; schedule_index[{idx}] = 3'd{index};"
        for idx, (cycle, index) in enumerate(zip(schedule_cycles, schedule_indices, strict=True))
    )

    fault_init = "\n".join(
        f"        fault_cycle[{idx}] = {row['cycle']}; "
        f"fault_addr[{idx}] = {row['addr']}; "
        f"fault_mask[{idx}] = 39'h{row['bit_mask_hex']};"
        for idx, row in enumerate(fault_rows)
    )

    tb_path = GENERATED_TB_DIR / f"tb_fault_replay_{strategy}.sv"
    tb_path.parent.mkdir(parents=True, exist_ok=True)

    tb_path.write_text(
        f"""// Auto-generated fault replay testbench for strategy: {strategy}

`timescale 1ns/1ps

module tb_fault_replay_{strategy};

    localparam int ADDR_WIDTH = {ADDR_WIDTH};
    localparam int DEPTH = {DEPTH};
    localparam int NUM_SCHEDULE_EVENTS = {len(schedule_cycles)};
    localparam int NUM_FAULT_EVENTS = {len(fault_rows)};
    localparam int MISSION_CYCLES = {mission_cycles};
    localparam int EXPECTED_PASS_COUNT_ROUNDED = {expected_pass_count(schedule_rows)};

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
    logic [38:0] golden_codeword [0:DEPTH-1];
    logic [31:0] golden_data [0:DEPTH-1];

    logic [31:0] encoder_data;
    logic [38:0] encoder_codeword;

    logic [38:0] audit_codeword;
    logic [38:0] audit_corrected_codeword;
    logic [31:0] audit_data;
    logic audit_no_error;
    logic audit_corrected;
    logic audit_detected_uncorrectable;
    logic [5:0] audit_syndrome;
    logic [5:0] audit_corrected_position;

    integer schedule_cycle [0:NUM_SCHEDULE_EVENTS-1];
    integer schedule_index [0:NUM_SCHEDULE_EVENTS-1];

    integer fault_cycle [0:NUM_FAULT_EVENTS-1];
    integer fault_addr [0:NUM_FAULT_EVENTS-1];
    logic [38:0] fault_mask [0:NUM_FAULT_EVENTS-1];

    integer addr;
    integer mission_cycle;
    integer next_schedule_event;
    integer fault_event_index;
    integer faults_injected;
    integer period_updates_applied;
    integer pass_starts_observed;
    integer selected_period_mismatches;
    integer safe_mode_observed_after_update;
    integer failures;

    integer final_uncorrectable_words;
    integer final_sdc_words;
    integer final_dangerous_words;

    secded_32_39_encoder encoder (
        .data_in(encoder_data),
        .codeword_out(encoder_codeword)
    );

    secded_32_39_decoder audit_decoder (
        .codeword_in(audit_codeword),
        .codeword_corrected(audit_corrected_codeword),
        .data_out(audit_data),
        .no_error(audit_no_error),
        .corrected(audit_corrected),
        .detected_uncorrectable(audit_detected_uncorrectable),
        .syndrome(audit_syndrome),
        .corrected_position(audit_corrected_position)
    );

    adaptive_scrub_controller #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DEPTH(DEPTH),
{period_params_block},
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
{schedule_init}
    end

    initial begin
{fault_init}
    end

    initial begin
        failures = 0;
        faults_injected = 0;
        period_updates_applied = 0;
        pass_starts_observed = 0;
        selected_period_mismatches = 0;
        safe_mode_observed_after_update = 0;

        period_update_valid = 1'b0;
        period_index = 3'd0;
        next_schedule_event = 0;
        mission_cycle = 0;

        reset_n = 1'b0;

        for (addr = 0; addr < DEPTH; addr = addr + 1) begin
            encoder_data = 32'h6000_0000 + addr[31:0];
            #1;
            golden_data[addr] = encoder_data;
            golden_codeword[addr] = encoder_codeword;
            memory[addr] = encoder_codeword;
        end

        repeat (5) @(posedge clk);
        reset_n = 1'b1;

        while (mission_cycle < MISSION_CYCLES) begin
            period_update_valid = 1'b0;

            if ((next_schedule_event < NUM_SCHEDULE_EVENTS) &&
                (mission_cycle == schedule_cycle[next_schedule_event])) begin
                period_index = schedule_index[next_schedule_event][2:0];
                period_update_valid = 1'b1;
                period_updates_applied = period_updates_applied + 1;
                next_schedule_event = next_schedule_event + 1;
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

            // Apply all fault events scheduled for this model cycle after the
            // clock edge. Multiple rows with the same cycle model simultaneous
            // physical events and are XORed before the next scrub operation.
            for (fault_event_index = 0; fault_event_index < NUM_FAULT_EVENTS; fault_event_index = fault_event_index + 1) begin
                if (fault_cycle[fault_event_index] == mission_cycle) begin
                    memory[fault_addr[fault_event_index][ADDR_WIDTH-1:0]] =
                        memory[fault_addr[fault_event_index][ADDR_WIDTH-1:0]] ^
                        fault_mask[fault_event_index];
                    faults_injected = faults_injected + 1;
                end
            end

            mission_cycle = mission_cycle + 1;
        end

        final_uncorrectable_words = 0;
        final_sdc_words = 0;

        for (addr = 0; addr < DEPTH; addr = addr + 1) begin
            audit_codeword = memory[addr];
            #1;

            if (audit_detected_uncorrectable) begin
                final_uncorrectable_words = final_uncorrectable_words + 1;
            end else if (audit_data != golden_data[addr]) begin
                final_sdc_words = final_sdc_words + 1;
            end
        end

        final_dangerous_words = final_uncorrectable_words + final_sdc_words;

        check_condition(period_updates_applied == NUM_SCHEDULE_EVENTS, "not all schedule events were applied");
        check_condition(faults_injected == NUM_FAULT_EVENTS, "not all fault events were injected");
        check_condition(selected_period_mismatches == 0, "period index mismatch during replay");
        check_condition(safe_mode_observed_after_update == 0, "safe mode asserted during valid replay");
        check_condition(pass_starts_observed == EXPECTED_PASS_COUNT_ROUNDED, "pass_start count mismatch");
        check_condition(final_uncorrectable_words == 1, "expected one final uncorrectable word");
        check_condition(final_sdc_words == 1, "expected one final SDC word");
        check_condition(final_dangerous_words == 2, "expected two final dangerous words");

        $display("FAULT_REPLAY_SUMMARY strategy={strategy} mission_cycles=%0d schedule_updates=%0d faults_injected=%0d expected_passes=%0d observed_pass_starts=%0d completed_passes=%0d reads=%0d writes=%0d corrected_events=%0d detected_due_events=%0d final_uncorrectable_words=%0d final_sdc_words=%0d final_dangerous_words=%0d safe_mode_cycles=%0d selected_mismatches=%0d failures=%0d",
                 MISSION_CYCLES,
                 period_updates_applied,
                 faults_injected,
                 EXPECTED_PASS_COUNT_ROUNDED,
                 pass_starts_observed,
                 pass_count,
                 read_count,
                 write_count,
                 corrected_count,
                 detected_uncorrectable_count,
                 final_uncorrectable_words,
                 final_sdc_words,
                 final_dangerous_words,
                 safe_mode_observed_after_update,
                 selected_period_mismatches,
                 failures);

        if (failures != 0) begin
            $fatal(1, "fault replay failed with %0d failures", failures);
        end

        $display("FAULT_REPLAY_PASS strategy={strategy}");
        $finish;
    end

endmodule
""",
        encoding="utf-8",
    )

    return tb_path


def compile_and_run(strategy: str, tb_path: Path) -> tuple[str, dict[str, int]]:
    sim_out = BUILD_DIR / f"tb_fault_replay_{strategy}.vvp"
    log_path = RESULT_DIR / f"fault_replay_{strategy}.log"

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
        rf"FAULT_REPLAY_SUMMARY strategy={strategy} mission_cycles=(\d+) "
        rf"schedule_updates=(\d+) faults_injected=(\d+) expected_passes=(\d+) "
        rf"observed_pass_starts=(\d+) completed_passes=(\d+) reads=(\d+) "
        rf"writes=(\d+) corrected_events=(\d+) detected_due_events=(\d+) "
        rf"final_uncorrectable_words=(\d+) final_sdc_words=(\d+) "
        rf"final_dangerous_words=(\d+) safe_mode_cycles=(\d+) "
        rf"selected_mismatches=(\d+) failures=(\d+)"
    )

    match = re.search(pattern, run_proc.stdout)

    if not match:
        raise RuntimeError(f"could not parse fault replay summary for {strategy}")

    keys = [
        "mission_cycles",
        "schedule_updates",
        "faults_injected",
        "expected_passes",
        "observed_pass_starts",
        "completed_passes",
        "reads",
        "writes",
        "corrected_events",
        "detected_due_events",
        "final_uncorrectable_words",
        "final_sdc_words",
        "final_dangerous_words",
        "safe_mode_cycles",
        "selected_mismatches",
        "failures",
    ]

    values = {key: int(value) for key, value in zip(keys, match.groups(), strict=True)}
    return str(log_path.relative_to(REPO_ROOT)), values


def write_summary(rows: list[dict[str, str]]) -> None:
    summary_csv = RESULT_DIR / "fault_replay_summary.csv"
    summary_md = RESULT_DIR / "fault_replay_summary.md"

    fieldnames = [
        "strategy",
        "mission_cycles",
        "schedule_updates",
        "faults_injected",
        "expected_passes",
        "observed_pass_starts",
        "completed_passes",
        "reads",
        "writes",
        "corrected_events",
        "detected_due_events",
        "final_uncorrectable_words",
        "final_sdc_words",
        "final_dangerous_words",
        "safe_mode_cycles",
        "selected_mismatches",
        "failures",
        "log_path",
    ]

    write_csv(summary_csv, rows, fieldnames)

    lines = [
        "# Fault-event replay summary",
        "",
        "| Strategy | Passes | Reads | Writes | Corrected | DUE events | Final DUE words | Final SDC words | Final dangerous | Failures |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            "| {strategy} | {completed_passes} | {reads} | {writes} | "
            "{corrected_events} | {detected_due_events} | {final_uncorrectable_words} | "
            "{final_sdc_words} | {final_dangerous_words} | {failures} |".format(**row)
        )

    lines.extend(
        [
            "",
            "The same external fault stream is replayed against fixed and adaptive",
            "period-index schedules. Faults are supplied as data, not hardcoded in",
            "the RTL controller.",
            "",
        ]
    )

    summary_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    schedule_proc = run_cmd(["python3", "scripts/run_schedule_demo.py"])
    print(schedule_proc.stdout)
    if schedule_proc.returncode != 0:
        return schedule_proc.returncode

    fault_rows = generate_fault_events()
    fault_csv = RESULT_DIR / "fault_events.csv"
    write_csv(
        fault_csv,
        fault_rows,
        [
            "event_id",
            "cycle",
            "physical_event_id",
            "event_type",
            "addr",
            "bit_index",
            "bit_mask_hex",
            "multiplicity",
            "interleave_depth",
        ],
    )

    periods = load_period_table()

    summary_rows: list[dict[str, str]] = []

    for strategy in ("fixed", "adaptive"):
        schedule_rows = load_schedule(strategy)
        tb_path = generate_tb(strategy, periods, schedule_rows, fault_rows)
        log_path, values = compile_and_run(strategy, tb_path)

        summary_rows.append(
            {
                "strategy": strategy,
                **{key: str(value) for key, value in values.items()},
                "log_path": log_path,
            }
        )

    write_summary(summary_rows)

    print("Fault replay summary written to", RESULT_DIR / "fault_replay_summary.csv")

    for row in summary_rows:
        print(
            f"{row['strategy']}: passes={row['completed_passes']} reads={row['reads']} "
            f"writes={row['writes']} corrected={row['corrected_events']} "
            f"due_events={row['detected_due_events']} "
            f"final_dangerous={row['final_dangerous_words']} failures={row['failures']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
