#!/usr/bin/env python3
"""Replay radiation-window fault streams on the RTL controller.

The same fault stream is replayed against the Chapter 3 current and delayed
period-index schedules.  DUE detections are split into:
  - detected_due_events: every online DUE pulse;
  - new_due_words: first observed DUE word;
  - persistent_due_detections: repeated detections of already-known DUE words.

SDC is not an online SEC-DED flag.  It is computed only by the golden-reference
verification audit at the end of each replay.
"""

from __future__ import annotations

import csv
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "rtl_replay"
BUILD_DIR = REPO_ROOT / "generated" / "rtl"
GENERATED_TB_DIR = BUILD_DIR / "ch3_fault_replay"
FAULT_DIR = RESULT_DIR

WINDOWS_PATH = REPO_ROOT / "results" / "schedules" / "ch3_replay_windows.csv"
PERIOD_TABLE_PATH = REPO_ROOT / "results" / "schedules" / "ch3_period_table.csv"

SCHEDULE_PATHS = {
    "current": REPO_ROOT / "results" / "schedules" / "ch3_five_year_schedule_current.csv",
    "delayed_1h": REPO_ROOT / "results" / "schedules" / "ch3_five_year_schedule_delayed_1h.csv",
}

FAULT_EVENTS_CSV = RESULT_DIR / "ch3_window_fault_events.csv"

SCALE_CYCLES_PER_SECOND = 32
DEPTH = 8
ADDR_WIDTH = 3


@dataclass(frozen=True)
class FaultEvent:
    window_name: str
    event_id: int
    cycle: int
    physical_event_id: int
    event_type: str
    addr: int
    bit_index: int
    multiplicity: int
    interleave_depth: int

    @property
    def mask_hex(self) -> str:
        return f"{1 << self.bit_index:010x}"


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


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", value)


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
    total = sum(float(row["passes"]) for row in rows)
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


def hour_cycle(hour: int, offset_cycles: int = 100) -> int:
    return int(round(hour * 3600 * SCALE_CYCLES_PER_SECOND + offset_cycles))


def fault_events_for_window(window: dict[str, str]) -> list[FaultEvent]:
    name = window["window_name"]
    max_nu = float(window["max_nu"])

    events: list[FaultEvent] = []
    eid = 0
    physical_id_base = 1000 + int(window["start_index"])

    def add(cycle: int, physical_id: int, event_type: str, addr: int, bit: int, multiplicity: int, d: int) -> None:
        nonlocal eid
        events.append(
            FaultEvent(
                window_name=name,
                event_id=eid,
                cycle=cycle,
                physical_event_id=physical_id,
                event_type=event_type,
                addr=addr,
                bit_index=bit,
                multiplicity=multiplicity,
                interleave_depth=d,
            )
        )
        eid += 1

    # Always inject a correctable accumulated single-bit error.
    add(hour_cycle(3), physical_id_base + 1, "single_accumulation", 1, 7, 1, 1)

    # Always inject one physical 3-bit event that is split by interleaving into
    # three different codewords.  This should be corrected as three singles.
    split_cycle = hour_cycle(6)
    for addr, bit in ((2, 2), (3, 3), (4, 4)):
        add(split_cycle, physical_id_base + 2, "mbu_split_interleaved", addr, bit, 3, 3)

    # High-radiation windows additionally receive same-word events.  These are
    # outside what a scrub period alone can fix.
    if max_nu >= 20.0:
        double_cycle = hour_cycle(12)
        add(double_cycle, physical_id_base + 3, "mbu_same_word_due", 5, 3, 2, 1)
        add(double_cycle, physical_id_base + 3, "mbu_same_word_due", 5, 10, 2, 1)

        triple_cycle = hour_cycle(18)
        for bit in (4, 5, 6):
            add(triple_cycle, physical_id_base + 4, "triple_same_word_sdc", 6, bit, 3, 1)

    return events


def write_fault_events_csv(windows: list[dict[str, str]]) -> dict[str, list[FaultEvent]]:
    FAULT_DIR.mkdir(parents=True, exist_ok=True)

    events_by_window = {
        window["window_name"]: fault_events_for_window(window)
        for window in windows
    }

    with FAULT_EVENTS_CSV.open("w", encoding="utf-8", newline="") as file:
        fieldnames = [
            "window_name",
            "event_id",
            "cycle",
            "physical_event_id",
            "event_type",
            "addr",
            "bit_index",
            "bit_mask_hex",
            "multiplicity",
            "interleave_depth",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for window_name in events_by_window:
            for event in events_by_window[window_name]:
                writer.writerow(
                    {
                        "window_name": event.window_name,
                        "event_id": event.event_id,
                        "cycle": event.cycle,
                        "physical_event_id": event.physical_event_id,
                        "event_type": event.event_type,
                        "addr": event.addr,
                        "bit_index": event.bit_index,
                        "bit_mask_hex": event.mask_hex,
                        "multiplicity": event.multiplicity,
                        "interleave_depth": event.interleave_depth,
                    }
                )

    return events_by_window


def generate_tb(
    strategy: str,
    window: dict[str, str],
    periods: list[float],
    rows: list[dict[str, str]],
    faults: list[FaultEvent],
) -> Path:
    window_name = safe_name(window["window_name"])
    tb_name = f"tb_ch3_fault_replay_{strategy}_{window_name}"

    cycles, indices, mission_cycles = event_cycles_and_indices(rows)
    expected_passes = expected_pass_count(rows)

    period_params = []
    for idx, seconds in enumerate(periods):
        cycles_value = int(round(seconds * SCALE_CYCLES_PER_SECOND))
        period_params.append(f"        .PERIOD{idx}_CYCLES({cycles_value})")

    schedule_event_init = "\n".join(
        f"        schedule_cycle[{idx}] = {cycle}; schedule_index[{idx}] = 4'd{index};"
        for idx, (cycle, index) in enumerate(zip(cycles, indices, strict=True))
    )

    fault_event_init = "\n".join(
        f"        fault_cycle[{idx}] = {event.cycle}; fault_addr[{idx}] = {ADDR_WIDTH}'d{event.addr}; "
        f"fault_mask[{idx}] = 39'h{event.mask_hex};"
        for idx, event in enumerate(faults)
    )

    high_window = float(window["max_nu"]) >= 20.0
    expected_final_dangerous_min = 2 if high_window else 0
    expected_corrected_min = 4

    tb_path = GENERATED_TB_DIR / f"{tb_name}.sv"
    tb_path.parent.mkdir(parents=True, exist_ok=True)

    tb_path.write_text(
        f"""// Auto-generated Chapter 3 fault replay testbench.
// strategy: {strategy}
// window:   {window['window_name']}
// start:    {window['start_timestamp_utc']}
// end:      {window['end_timestamp_utc']}

`timescale 1ns/1ps

module {tb_name};

    localparam int ADDR_WIDTH = {ADDR_WIDTH};
    localparam int DEPTH = {DEPTH};
    localparam int PERIOD_INDEX_WIDTH = 4;
    localparam int NUM_SCHEDULE_EVENTS = {len(cycles)};
    localparam int NUM_FAULT_EVENTS = {len(faults)};
    localparam int MISSION_CYCLES = {mission_cycles};
    localparam int EXPECTED_PASS_COUNT = {expected_passes};
    localparam int EXPECTED_CORRECTED_MIN = {expected_corrected_min};
    localparam int EXPECTED_FINAL_DANGEROUS_MIN = {expected_final_dangerous_min};

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
    logic [31:0] golden_data [0:DEPTH-1];

    logic [31:0] encoder_data;
    logic [38:0] encoder_codeword;

    logic [38:0] audit_codeword;
    logic [38:0] audit_codeword_corrected;
    logic [31:0] audit_data;
    logic audit_no_error;
    logic audit_corrected;
    logic audit_detected_uncorrectable;
    logic [5:0] audit_syndrome;
    logic [5:0] audit_corrected_position;

    integer schedule_cycle [0:NUM_SCHEDULE_EVENTS-1];
    integer schedule_index [0:NUM_SCHEDULE_EVENTS-1];

    integer fault_cycle [0:NUM_FAULT_EVENTS-1];
    logic [ADDR_WIDTH-1:0] fault_addr [0:NUM_FAULT_EVENTS-1];
    logic [38:0] fault_mask [0:NUM_FAULT_EVENTS-1];

    logic due_seen [0:DEPTH-1];

    integer addr;
    integer mission_cycle;
    integer next_schedule_event;
    integer next_fault_event;
    integer failures;
    integer period_updates_applied;
    integer faults_injected;
    integer pass_starts_observed;
    integer safe_mode_observed_after_update;
    integer selected_period_mismatches;

    integer detected_due_events_online;
    integer new_due_words;
    integer persistent_due_detections;

    integer final_uncorrectable_words;
    integer final_sdc_words;
    integer final_dangerous_words;

    secded_32_39_encoder encoder (
        .data_in(encoder_data),
        .codeword_out(encoder_codeword)
    );

    secded_32_39_decoder audit_decoder (
        .codeword_in(audit_codeword),
        .codeword_corrected(audit_codeword_corrected),
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
        .PERIOD_INDEX_WIDTH(PERIOD_INDEX_WIDTH),
{",\n".join(period_params)},
        .SAFE_PERIOD_INDEX(0),
        .MAX_CONTROL_AGE_CYCLES(32'h7fff_ffff)
    ) dut (
        .clk(clk),
        .reset_n(reset_n),
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

    always_ff @(posedge clk) begin
        if (detected_uncorrectable_pulse) begin
            detected_due_events_online <= detected_due_events_online + 1;

            if (!due_seen[mem_addr]) begin
                due_seen[mem_addr] <= 1'b1;
                new_due_words <= new_due_words + 1;
            end else begin
                persistent_due_detections <= persistent_due_detections + 1;
            end
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

    task automatic inject_fault(input logic [ADDR_WIDTH-1:0] target_addr, input logic [38:0] target_mask);
        begin
            memory[target_addr] = memory[target_addr] ^ target_mask;
            faults_injected = faults_injected + 1;
        end
    endtask

    task automatic audit_final_memory;
        begin
            final_uncorrectable_words = 0;
            final_sdc_words = 0;

            for (addr = 0; addr < DEPTH; addr = addr + 1) begin
                audit_codeword = memory[addr];
                #1;

                if (audit_detected_uncorrectable) begin
                    final_uncorrectable_words = final_uncorrectable_words + 1;
                end else if (audit_data !== golden_data[addr]) begin
                    final_sdc_words = final_sdc_words + 1;
                end
            end

            final_dangerous_words = final_uncorrectable_words + final_sdc_words;
        end
    endtask

    initial begin
{schedule_event_init}
    end

    initial begin
{fault_event_init}
    end

    initial begin
        failures = 0;
        period_updates_applied = 0;
        faults_injected = 0;
        pass_starts_observed = 0;
        safe_mode_observed_after_update = 0;
        selected_period_mismatches = 0;

        detected_due_events_online = 0;
        new_due_words = 0;
        persistent_due_detections = 0;

        period_update_valid = 1'b0;
        period_index = 4'd0;
        next_schedule_event = 0;
        next_fault_event = 0;
        mission_cycle = 0;

        reset_n = 1'b0;

        for (addr = 0; addr < DEPTH; addr = addr + 1) begin
            encoder_data = 32'h7000_0000 + addr[31:0];
            golden_data[addr] = encoder_data;
            due_seen[addr] = 1'b0;
            #1;
            memory[addr] = encoder_codeword;
        end

        repeat (5) @(posedge clk);
        reset_n = 1'b1;

        while (mission_cycle < MISSION_CYCLES) begin
            period_update_valid = 1'b0;

            while ((next_fault_event < NUM_FAULT_EVENTS) && (mission_cycle == fault_cycle[next_fault_event])) begin
                inject_fault(fault_addr[next_fault_event], fault_mask[next_fault_event]);
                next_fault_event = next_fault_event + 1;
            end

            if ((next_schedule_event < NUM_SCHEDULE_EVENTS) && (mission_cycle == schedule_cycle[next_schedule_event])) begin
                period_index = schedule_index[next_schedule_event][PERIOD_INDEX_WIDTH-1:0];
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

            mission_cycle = mission_cycle + 1;
        end

        audit_final_memory();

        check_condition(period_updates_applied == NUM_SCHEDULE_EVENTS, "not all period events were applied");
        check_condition(faults_injected == NUM_FAULT_EVENTS, "not all fault events were injected");
        check_condition(selected_period_mismatches == 0, "selected period index mismatch during updates");
        check_condition(safe_mode_observed_after_update == 0, "safe mode asserted after valid schedule updates");
        check_condition(pass_starts_observed == EXPECTED_PASS_COUNT, "pass_start count does not match model expectation");
        check_condition(pass_count == EXPECTED_PASS_COUNT, "completed pass count does not match model expectation");
        check_condition(read_count == pass_count * DEPTH, "read count is inconsistent with completed passes");
        check_condition(corrected_count >= EXPECTED_CORRECTED_MIN, "not enough corrected events");
        check_condition(final_dangerous_words >= EXPECTED_FINAL_DANGEROUS_MIN, "dangerous-state audit below expected minimum");

        if (EXPECTED_FINAL_DANGEROUS_MIN == 0) begin
            check_condition(final_dangerous_words == 0, "quiet/split-only window should finish without dangerous words");
        end

        $display("CH3_FAULT_REPLAY_SUMMARY strategy={strategy} window={window['window_name']} mission_cycles=%0d period_updates=%0d faults_injected=%0d expected_passes=%0d observed_pass_starts=%0d completed_passes=%0d reads=%0d writes=%0d corrected_events=%0d detected_due_events=%0d new_due_words=%0d persistent_due_detections=%0d final_uncorrectable_words=%0d final_sdc_words=%0d final_dangerous_words=%0d safe_mode_cycles=%0d selected_mismatches=%0d failures=%0d",
                 MISSION_CYCLES,
                 period_updates_applied,
                 faults_injected,
                 EXPECTED_PASS_COUNT,
                 pass_starts_observed,
                 pass_count,
                 read_count,
                 write_count,
                 corrected_count,
                 detected_due_events_online,
                 new_due_words,
                 persistent_due_detections,
                 final_uncorrectable_words,
                 final_sdc_words,
                 final_dangerous_words,
                 safe_mode_observed_after_update,
                 selected_period_mismatches,
                 failures);

        if (failures != 0) begin
            $fatal(1, "Chapter 3 fault replay failed with %0d failures", failures);
        end

        $display("CH3_FAULT_REPLAY_PASS strategy={strategy} window={window['window_name']}");
        $finish;
    end

endmodule
""",
        encoding="utf-8",
    )

    return tb_path


def compile_and_run(
    strategy: str,
    window: dict[str, str],
    tb_path: Path,
) -> tuple[str, dict[str, int]]:
    window_name = safe_name(window["window_name"])
    sim_out = BUILD_DIR / f"tb_ch3_fault_replay_{strategy}_{window_name}.vvp"
    log_path = RESULT_DIR / f"ch3_fault_replay_{strategy}_{window_name}.log"

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
        rf"CH3_FAULT_REPLAY_SUMMARY strategy={strategy} window={window['window_name']} "
        rf"mission_cycles=(\d+) period_updates=(\d+) faults_injected=(\d+) "
        rf"expected_passes=(\d+) observed_pass_starts=(\d+) completed_passes=(\d+) "
        rf"reads=(\d+) writes=(\d+) corrected_events=(\d+) detected_due_events=(\d+) "
        rf"new_due_words=(\d+) persistent_due_detections=(\d+) "
        rf"final_uncorrectable_words=(\d+) final_sdc_words=(\d+) final_dangerous_words=(\d+) "
        rf"safe_mode_cycles=(\d+) selected_mismatches=(\d+) failures=(\d+)"
    )

    match = re.search(pattern, run_proc.stdout)

    if not match:
        raise RuntimeError(f"could not parse summary for {strategy}/{window['window_name']}")

    keys = [
        "mission_cycles",
        "period_updates",
        "faults_injected",
        "expected_passes",
        "observed_pass_starts",
        "completed_passes",
        "reads",
        "writes",
        "corrected_events",
        "detected_due_events",
        "new_due_words",
        "persistent_due_detections",
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
    summary_csv = RESULT_DIR / "ch3_fault_replay_summary.csv"
    summary_md = RESULT_DIR / "ch3_fault_replay_summary.md"

    fieldnames = [
        "strategy",
        "window_name",
        "start_timestamp_utc",
        "end_timestamp_utc",
        "hours",
        "mission_cycles",
        "period_updates",
        "faults_injected",
        "expected_passes",
        "observed_pass_starts",
        "completed_passes",
        "pass_start_delta_vs_expected",
        "completed_delta_vs_expected",
        "reads",
        "writes",
        "corrected_events",
        "detected_due_events",
        "new_due_words",
        "persistent_due_detections",
        "final_uncorrectable_words",
        "final_sdc_words",
        "final_dangerous_words",
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
        "# Chapter 3 radiation-window fault replay summary",
        "",
        "The same external fault stream is replayed against current and delayed",
        "period-index schedules for each selected radiation window.",
        "",
        "`detected_due_events` counts every online DUE pulse. `new_due_words` and",
        "`persistent_due_detections` separate first observations from repeated",
        "diagnostic load. `final_sdc_words` is a verification-only golden-reference",
        "audit metric, not an online SEC-DED output.",
        "",
        "| Strategy | Window | Passes | Reads | Writes | Corrected | DUE events | New DUE words | Persistent DUE | Final DUE | Final SDC | Final dangerous | Failures |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            f"| {row['strategy']} | {row['window_name']} | {row['completed_passes']} | "
            f"{row['reads']} | {row['writes']} | {row['corrected_events']} | "
            f"{row['detected_due_events']} | {row['new_due_words']} | "
            f"{row['persistent_due_detections']} | {row['final_uncorrectable_words']} | "
            f"{row['final_sdc_words']} | {row['final_dangerous_words']} | {row['failures']} |"
        )

    lines.append("")
    summary_md.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote", summary_csv)
    print("Wrote", summary_md)


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    periods = load_period_table()
    windows = read_csv(WINDOWS_PATH)
    faults_by_window = write_fault_events_csv(windows)

    schedule_by_strategy = {
        strategy: load_schedule_rows(strategy)
        for strategy in SCHEDULE_PATHS
    }

    rows_for_summary: list[dict[str, str]] = []

    for window in windows:
        faults = faults_by_window[window["window_name"]]

        for strategy in ("current", "delayed_1h"):
            subset = window_schedule_rows(schedule_by_strategy[strategy], window)
            tb_path = generate_tb(strategy, window, periods, subset, faults)
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
    print("Wrote", FAULT_EVENTS_CSV)
    print()
    for row in rows_for_summary:
        print(
            f"{row['strategy']}/{row['window_name']}: "
            f"passes={row['completed_passes']} corrected={row['corrected_events']} "
            f"due_events={row['detected_due_events']} new_due={row['new_due_words']} "
            f"persistent_due={row['persistent_due_detections']} "
            f"final_dangerous={row['final_dangerous_words']} failures={row['failures']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
