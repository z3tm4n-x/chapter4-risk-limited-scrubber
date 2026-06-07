#!/usr/bin/env python3
"""Integrated adaptive controller + diagnostic supervisor RTL test."""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "rtl_replay"
BUILD_DIR = REPO_ROOT / "generated" / "rtl"
TB_DIR = BUILD_DIR / "integrated_diagnostic_controller"

SUMMARY_CSV = RESULT_DIR / "integrated_diagnostic_controller_summary.csv"
SUMMARY_MD = RESULT_DIR / "integrated_diagnostic_controller_report.md"
LOG_PATH = RESULT_DIR / "integrated_diagnostic_controller.log"


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def generate_tb() -> Path:
    TB_DIR.mkdir(parents=True, exist_ok=True)
    tb_path = TB_DIR / "tb_integrated_diagnostic_controller.sv"

    tb_path.write_text(
        r'''`timescale 1ns/1ps

module tb_integrated_diagnostic_controller;

    localparam int ADDR_WIDTH = 3;
    localparam int DEPTH = 8;
    localparam int PERIOD_INDEX_WIDTH = 4;

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

    logic diag_alert_flag;
    logic diag_danger_detected_flag;
    logic diag_persistent_due_flag;
    logic diag_out_of_envelope_flag;
    logic diag_force_conservative;

    logic [31:0] diag_pass_corrected_count;
    logic [31:0] diag_alert_event_count;
    logic [31:0] diag_danger_event_count;
    logic [31:0] diag_new_due_word_count;
    logic [31:0] diag_persistent_due_count;
    logic [31:0] diag_consecutive_alert_passes;

    logic [38:0] memory [0:DEPTH-1];

    logic [31:0] encoder_data;
    logic [38:0] encoder_codeword;

    integer addr;
    integer failures;
    integer wait_cycles;

    secded_32_39_encoder encoder (
        .data_in(encoder_data),
        .codeword_out(encoder_codeword)
    );

    adaptive_scrub_controller #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DEPTH(DEPTH),
        .PERIOD_INDEX_WIDTH(PERIOD_INDEX_WIDTH),
        .PERIOD0_CYCLES(40),
        .PERIOD1_CYCLES(80),
        .PERIOD2_CYCLES(160),
        .PERIOD3_CYCLES(320),
        .PERIOD4_CYCLES(640),
        .PERIOD5_CYCLES(1280),
        .PERIOD6_CYCLES(2560),
        .PERIOD7_CYCLES(5120),
        .PERIOD8_CYCLES(5120),
        .PERIOD9_CYCLES(5120),
        .PERIOD10_CYCLES(5120),
        .PERIOD11_CYCLES(5120),
        .SAFE_PERIOD_INDEX(0),
        .MAX_CONTROL_AGE_CYCLES(32'h7fff_ffff),
        .DIAG_CORRECTED_ALERT_THRESHOLD(1),
        .DIAG_ALERT_CONSECUTIVE_THRESHOLD(1),
        .DIAG_PERSISTENT_DUE_THRESHOLD(1)
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
        .safe_mode_entry_count(safe_mode_entry_count),
        .diag_alert_flag(diag_alert_flag),
        .diag_danger_detected_flag(diag_danger_detected_flag),
        .diag_persistent_due_flag(diag_persistent_due_flag),
        .diag_out_of_envelope_flag(diag_out_of_envelope_flag),
        .diag_force_conservative(diag_force_conservative),
        .diag_pass_corrected_count(diag_pass_corrected_count),
        .diag_alert_event_count(diag_alert_event_count),
        .diag_danger_event_count(diag_danger_event_count),
        .diag_new_due_word_count(diag_new_due_word_count),
        .diag_persistent_due_count(diag_persistent_due_count),
        .diag_consecutive_alert_passes(diag_consecutive_alert_passes)
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

    task automatic init_memory;
        begin
            for (addr = 0; addr < DEPTH; addr = addr + 1) begin
                encoder_data = 32'h9000_0000 + addr[31:0];
                #1;
                memory[addr] = encoder_codeword;
            end
        end
    endtask

    task automatic wait_for_pass_count(input integer target_pass_count, input integer max_cycles);
        begin
            wait_cycles = 0;

            while ((pass_count < target_pass_count) && (wait_cycles < max_cycles)) begin
                @(posedge clk);
                wait_cycles = wait_cycles + 1;
            end

            check_condition(pass_count >= target_pass_count, "timeout waiting for pass_count target");
        end
    endtask

    initial begin
        failures = 0;

        period_update_valid = 1'b0;
        period_index = 4'd0;

        reset_n = 1'b0;
        init_memory();

        repeat (5) @(posedge clk);
        reset_n = 1'b1;

        @(posedge clk);
        period_update_valid = 1'b1;
        period_index = 4'd0;
        @(posedge clk);
        period_update_valid = 1'b0;

        // Correctable single-bit fault: should be repaired and should raise alert.
        memory[1] = memory[1] ^ 39'h0000000080;

        wait_for_pass_count(2, 500);

        check_condition(corrected_count >= 1, "single-bit fault should be corrected");
        check_condition(write_count >= 1, "single-bit correction should write back");
        check_condition(diag_alert_flag == 1'b1, "diagnostic alert should be raised by correction");
        check_condition(diag_alert_event_count >= 1, "diagnostic alert event count should increment");
        check_condition(diag_out_of_envelope_flag == 1'b1, "threshold=1 alert should assert out_of_envelope");

        // Same-word double fault: should become DUE and then persistent DUE.
        memory[5] = memory[5] ^ 39'h0000000008;
        memory[5] = memory[5] ^ 39'h0000000400;

        wait_for_pass_count(5, 1000);

        check_condition(detected_uncorrectable_count >= 2, "persistent DUE should be observed across passes");
        check_condition(diag_danger_detected_flag == 1'b1, "diagnostic danger flag should be raised");
        check_condition(diag_new_due_word_count >= 1, "new DUE word should be counted");
        check_condition(diag_persistent_due_flag == 1'b1, "persistent DUE flag should be raised");
        check_condition(diag_persistent_due_count >= 1, "persistent DUE count should increment");
        check_condition(diag_force_conservative == 1'b1, "diagnostic force conservative should be raised");

        $display("INTEGRATED_DIAGNOSTIC_CONTROLLER_SUMMARY passes=%0d reads=%0d writes=%0d corrected=%0d due=%0d diag_alert=%0d diag_danger=%0d diag_persistent=%0d diag_out_of_envelope=%0d diag_force_conservative=%0d diag_alert_events=%0d diag_new_due_words=%0d diag_persistent_due=%0d failures=%0d",
                 pass_count,
                 read_count,
                 write_count,
                 corrected_count,
                 detected_uncorrectable_count,
                 diag_alert_flag,
                 diag_danger_detected_flag,
                 diag_persistent_due_flag,
                 diag_out_of_envelope_flag,
                 diag_force_conservative,
                 diag_alert_event_count,
                 diag_new_due_word_count,
                 diag_persistent_due_count,
                 failures);

        if (failures != 0) begin
            $fatal(1, "integrated diagnostic controller test failed with %0d failures", failures);
        end

        $display("INTEGRATED_DIAGNOSTIC_CONTROLLER_PASS");
        $finish;
    end

endmodule
''',
        encoding="utf-8",
    )

    return tb_path


def parse_summary(output: str) -> dict[str, str]:
    pattern = re.compile(
        r"INTEGRATED_DIAGNOSTIC_CONTROLLER_SUMMARY passes=(\d+) reads=(\d+) writes=(\d+) "
        r"corrected=(\d+) due=(\d+) diag_alert=(\d+) diag_danger=(\d+) "
        r"diag_persistent=(\d+) diag_out_of_envelope=(\d+) diag_force_conservative=(\d+) "
        r"diag_alert_events=(\d+) diag_new_due_words=(\d+) diag_persistent_due=(\d+) failures=(\d+)"
    )

    match = pattern.search(output)
    if not match:
        raise RuntimeError("could not parse integrated diagnostic controller summary")

    keys = [
        "passes",
        "reads",
        "writes",
        "corrected",
        "due",
        "diag_alert",
        "diag_danger",
        "diag_persistent",
        "diag_out_of_envelope",
        "diag_force_conservative",
        "diag_alert_events",
        "diag_new_due_words",
        "diag_persistent_due",
        "failures",
    ]

    return {key: value for key, value in zip(keys, match.groups(), strict=True)}


def write_outputs(row: dict[str, str]) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "passes",
        "reads",
        "writes",
        "corrected",
        "due",
        "diag_alert",
        "diag_danger",
        "diag_persistent",
        "diag_out_of_envelope",
        "diag_force_conservative",
        "diag_alert_events",
        "diag_new_due_words",
        "diag_persistent_due",
        "failures",
    ]

    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    lines = [
        "# Integrated diagnostic controller RTL report",
        "",
        "This report verifies that the top-level adaptive scrub controller exposes",
        "diagnostic-supervisor flags from actual SEC-DED scrub events.",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]

    for key in fieldnames:
        lines.append(f"| {key} | {row[key]} |")

    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- Corrected SEC-DED events are visible to the integrated diagnostic path.",
            "- Same-word persistent DUE raises danger and persistent-DUE diagnostics.",
            "- `diag_force_conservative` is a system-level request; the controller still does not compute the radiation model.",
            "",
        ]
    )

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    tb_path = generate_tb()
    sim_out = BUILD_DIR / "tb_integrated_diagnostic_controller.vvp"

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
        LOG_PATH.write_text(compile_proc.stdout, encoding="utf-8")
        print(compile_proc.stdout)
        raise RuntimeError("compile failed")

    run_proc = run_cmd(["vvp", str(sim_out)])
    LOG_PATH.write_text(compile_proc.stdout + run_proc.stdout, encoding="utf-8")
    print(run_proc.stdout)

    if run_proc.returncode != 0:
        raise RuntimeError("simulation failed")

    row = parse_summary(run_proc.stdout)
    write_outputs(row)

    print("Wrote", SUMMARY_CSV)
    print("Wrote", SUMMARY_MD)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
