#!/usr/bin/env python3
"""Run integrated measured-error scrub controller RTL test."""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "rtl_replay"
BUILD_DIR = REPO_ROOT / "generated" / "rtl"
TB_DIR = BUILD_DIR / "measured_error_controller"

SUMMARY_CSV = RESULT_DIR / "measured_error_controller_summary.csv"
SUMMARY_MD = RESULT_DIR / "measured_error_controller_report.md"
LOG_PATH = RESULT_DIR / "measured_error_controller.log"


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
    tb_path = TB_DIR / "tb_measured_error_controller.sv"

    tb_path.write_text(
        r'''`timescale 1ns/1ps

module tb_measured_error_controller;

    localparam int ADDR_WIDTH = 3;
    localparam int DEPTH = 8;
    localparam int PERIOD_INDEX_WIDTH = 4;

    logic clk;
    logic reset_n;

    logic measured_enable;
    logic measured_clear;

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

    logic [31:0] diag_alert_event_count;
    logic [31:0] diag_danger_event_count;
    logic [31:0] diag_new_due_word_count;
    logic [31:0] diag_persistent_due_count;

    logic measured_period_update_valid;
    logic [PERIOD_INDEX_WIDTH-1:0] measured_period_index;
    logic [31:0] measured_corrected_count_in_pass;
    logic [31:0] measured_due_count_in_pass;
    logic [31:0] measured_quiet_pass_count;
    logic measured_high_activity_flag;
    logic measured_quiet_relax_flag;
    logic measured_forced_safe_flag;

    logic [38:0] memory [0:DEPTH-1];

    logic [31:0] encoder_data;
    logic [38:0] encoder_codeword;

    integer addr;
    integer failures;
    integer wait_cycles;

    integer update_count;
    integer high_activity_observed;
    integer quiet_relax_observed;
    integer forced_safe_observed;

    integer period_before_activity;

    logic prev_measured_forced_safe_flag;

    secded_32_39_encoder encoder (
        .data_in(encoder_data),
        .codeword_out(encoder_codeword)
    );

    measured_error_scrub_controller #(
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
        .PERIOD8_CYCLES(10240),
        .PERIOD9_CYCLES(20480),
        .PERIOD10_CYCLES(40960),
        .PERIOD11_CYCLES(81920),
        .SAFE_PERIOD_INDEX(0),
        .MAX_CONTROL_AGE_CYCLES(32'h7fff_ffff),
        .MEASURED_INITIAL_PERIOD_INDEX(6),
        .MEASURED_CORRECTED_HIGH_THRESHOLD(3),
        .MEASURED_QUIET_PASS_THRESHOLD(2),
        .DIAG_CORRECTED_ALERT_THRESHOLD(1),
        .DIAG_ALERT_CONSECUTIVE_THRESHOLD(1),
        .DIAG_PERSISTENT_DUE_THRESHOLD(1)
    ) dut (
        .clk(clk),
        .reset_n(reset_n),
        .measured_enable(measured_enable),
        .measured_clear(measured_clear),
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
        .diag_alert_event_count(diag_alert_event_count),
        .diag_danger_event_count(diag_danger_event_count),
        .diag_new_due_word_count(diag_new_due_word_count),
        .diag_persistent_due_count(diag_persistent_due_count),
        .measured_period_update_valid(measured_period_update_valid),
        .measured_period_index(measured_period_index),
        .measured_corrected_count_in_pass(measured_corrected_count_in_pass),
        .measured_due_count_in_pass(measured_due_count_in_pass),
        .measured_quiet_pass_count(measured_quiet_pass_count),
        .measured_high_activity_flag(measured_high_activity_flag),
        .measured_quiet_relax_flag(measured_quiet_relax_flag),
        .measured_forced_safe_flag(measured_forced_safe_flag)
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

        if (measured_period_update_valid) begin
            update_count <= update_count + 1;
        end

        if (measured_high_activity_flag) begin
            high_activity_observed <= high_activity_observed + 1;
        end

        if (measured_quiet_relax_flag) begin
            quiet_relax_observed <= quiet_relax_observed + 1;
        end

        if (measured_forced_safe_flag && !prev_measured_forced_safe_flag) begin
            forced_safe_observed <= forced_safe_observed + 1;
        end

        prev_measured_forced_safe_flag <= measured_forced_safe_flag;
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
                encoder_data = 32'ha000_0000 + addr[31:0];
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

            check_condition(pass_count >= target_pass_count, "timeout waiting for pass count");
        end
    endtask

    initial begin
        failures = 0;
        update_count = 0;
        high_activity_observed = 0;
        quiet_relax_observed = 0;
        forced_safe_observed = 0;
        prev_measured_forced_safe_flag = 1'b0;

        measured_enable = 1'b1;
        measured_clear = 1'b0;

        reset_n = 1'b0;
        init_memory();

        repeat (5) @(posedge clk);
        reset_n = 1'b1;

        // Let the controller complete clean passes. The measured estimator should
        // start from index 6 and eventually relax after quiet passes.
        wait_for_pass_count(3, 20000);
        check_condition(update_count >= 2, "measured estimator should emit updates after passes");
        check_condition(measured_period_index >= 4'd6, "quiet operation should not speed up period");

        period_before_activity = measured_period_index;

        // Inject three independent single-bit errors before the next pass.
        memory[1] = memory[1] ^ 39'h0000000080;
        memory[2] = memory[2] ^ 39'h0000000010;
        memory[3] = memory[3] ^ 39'h0000000020;

        wait_for_pass_count(pass_count + 2, 30000);

        check_condition(corrected_count >= 3, "three single-bit errors should be corrected");
        check_condition(write_count >= 3, "three corrections should be written back");
        check_condition(high_activity_observed >= 1, "high corrected activity should be observed");
        check_condition(measured_period_index < period_before_activity, "high activity should speed up measured period");

        // Inject persistent same-word DUE.
        memory[5] = memory[5] ^ 39'h0000000008;
        memory[5] = memory[5] ^ 39'h0000000400;

        wait_for_pass_count(pass_count + 3, 30000);

        check_condition(detected_uncorrectable_count >= 1, "same-word double error should be detected as DUE");
        check_condition(forced_safe_observed >= 1, "DUE should force measured safe mode");
        check_condition(measured_period_index == 4'd0, "DUE should force measured period index to safe index");
        check_condition(diag_danger_detected_flag == 1'b1, "integrated diagnostics should raise danger");
        check_condition(diag_force_conservative == 1'b1, "integrated diagnostics should request conservative mode");

        $display("MEASURED_ERROR_CONTROLLER_SUMMARY passes=%0d reads=%0d writes=%0d corrected=%0d due=%0d updates=%0d high_activity=%0d quiet_relax=%0d forced_safe=%0d final_period_index=%0d diag_danger=%0d diag_force=%0d failures=%0d",
                 pass_count,
                 read_count,
                 write_count,
                 corrected_count,
                 detected_uncorrectable_count,
                 update_count,
                 high_activity_observed,
                 quiet_relax_observed,
                 forced_safe_observed,
                 measured_period_index,
                 diag_danger_detected_flag,
                 diag_force_conservative,
                 failures);

        if (failures != 0) begin
            $fatal(1, "measured-error controller test failed with %0d failures", failures);
        end

        $display("MEASURED_ERROR_CONTROLLER_PASS");
        $finish;
    end

endmodule
''',
        encoding="utf-8",
    )

    return tb_path


def parse_summary(output: str) -> dict[str, str]:
    pattern = re.compile(
        r"MEASURED_ERROR_CONTROLLER_SUMMARY passes=(\d+) reads=(\d+) writes=(\d+) "
        r"corrected=(\d+) due=(\d+) updates=(\d+) high_activity=(\d+) quiet_relax=(\d+) "
        r"forced_safe=(\d+) final_period_index=(\d+) diag_danger=(\d+) diag_force=(\d+) failures=(\d+)"
    )

    match = pattern.search(output)
    if not match:
        raise RuntimeError("could not parse measured-error controller summary")

    keys = [
        "passes",
        "reads",
        "writes",
        "corrected",
        "due",
        "updates",
        "high_activity",
        "quiet_relax",
        "forced_safe",
        "final_period_index",
        "diag_danger",
        "diag_force",
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
        "updates",
        "high_activity",
        "quiet_relax",
        "forced_safe",
        "final_period_index",
        "diag_danger",
        "diag_force",
        "failures",
    ]

    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    lines = [
        "# Integrated measured-error scrub controller RTL report",
        "",
        "This report verifies a complete onboard measured-error mode: SEC-DED",
        "observations drive an autonomous period estimator, which drives the same",
        "`period_index` interface used by the external Chapter 3 schedule path.",
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
            "- Quiet operation emits measured period updates without speeding up.",
            "- Multiple corrected single-bit events speed up the measured period.",
            "- DUE forces the measured safe period index.",
            "- The integrated diagnostic path raises danger and conservative-mode request.",
            "- This mode is a practical onboard fallback, not the exact-risk schedule compiler.",
            "",
        ]
    )

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    tb_path = generate_tb()
    sim_out = BUILD_DIR / "tb_measured_error_controller.vvp"

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
        "rtl/scrubber/measured_error_period_estimator.sv",
        "rtl/scrubber/measured_error_scrub_controller.sv",
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
