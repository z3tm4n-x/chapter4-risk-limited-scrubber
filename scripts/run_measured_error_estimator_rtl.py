#!/usr/bin/env python3
"""Run measured-error period estimator RTL test."""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "rtl_replay"
BUILD_DIR = REPO_ROOT / "generated" / "rtl"
TB_DIR = BUILD_DIR / "measured_error_estimator"

SUMMARY_CSV = RESULT_DIR / "measured_error_estimator_summary.csv"
SUMMARY_MD = RESULT_DIR / "measured_error_estimator_report.md"
LOG_PATH = RESULT_DIR / "measured_error_estimator.log"


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
    tb_path = TB_DIR / "tb_measured_error_estimator.sv"

    tb_path.write_text(
        r'''`timescale 1ns/1ps

module tb_measured_error_estimator;

    logic clk;
    logic reset_n;

    logic clear;
    logic enable;
    logic corrected_pulse;
    logic detected_uncorrectable_pulse;
    logic pass_done;

    logic period_update_valid;
    logic [3:0] period_index;

    logic [31:0] corrected_count_in_pass;
    logic [31:0] due_count_in_pass;
    logic [31:0] quiet_pass_count;

    logic high_activity_flag;
    logic quiet_relax_flag;
    logic forced_safe_flag;

    integer failures;
    integer update_count;
    integer high_activity_events;
    integer quiet_relax_events;
    integer forced_safe_events;

    measured_error_period_estimator #(
        .PERIOD_INDEX_WIDTH(4),
        .MIN_PERIOD_INDEX(0),
        .MAX_PERIOD_INDEX(11),
        .INITIAL_PERIOD_INDEX(6),
        .SAFE_PERIOD_INDEX(0),
        .CORRECTED_HIGH_THRESHOLD(3),
        .CORRECTED_LOW_THRESHOLD(0),
        .QUIET_PASS_THRESHOLD(2),
        .SPEEDUP_STEP(1),
        .RELAX_STEP(1)
    ) dut (
        .clk(clk),
        .reset_n(reset_n),
        .clear(clear),
        .enable(enable),
        .corrected_pulse(corrected_pulse),
        .detected_uncorrectable_pulse(detected_uncorrectable_pulse),
        .pass_done(pass_done),
        .period_update_valid(period_update_valid),
        .period_index(period_index),
        .corrected_count_in_pass(corrected_count_in_pass),
        .due_count_in_pass(due_count_in_pass),
        .quiet_pass_count(quiet_pass_count),
        .high_activity_flag(high_activity_flag),
        .quiet_relax_flag(quiet_relax_flag),
        .forced_safe_flag(forced_safe_flag)
    );

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    always_ff @(posedge clk) begin
        if (period_update_valid) begin
            update_count <= update_count + 1;
        end

        if (high_activity_flag) begin
            high_activity_events <= high_activity_events + 1;
        end

        if (quiet_relax_flag) begin
            quiet_relax_events <= quiet_relax_events + 1;
        end

        if (forced_safe_flag) begin
            forced_safe_events <= forced_safe_events + 1;
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

    task automatic pulse_corrected;
        begin
            corrected_pulse = 1'b1;
            @(posedge clk);
            #1;
            corrected_pulse = 1'b0;
        end
    endtask

    task automatic pulse_due;
        begin
            detected_uncorrectable_pulse = 1'b1;
            @(posedge clk);
            #1;
            detected_uncorrectable_pulse = 1'b0;
        end
    endtask

    task automatic finish_pass;
        begin
            pass_done = 1'b1;
            @(posedge clk);
            #1;
            pass_done = 1'b0;
            @(posedge clk);
            #1;
        end
    endtask

    initial begin
        failures = 0;
        update_count = 0;
        high_activity_events = 0;
        quiet_relax_events = 0;
        forced_safe_events = 0;

        clear = 1'b0;
        enable = 1'b1;
        corrected_pulse = 1'b0;
        detected_uncorrectable_pulse = 1'b0;
        pass_done = 1'b0;

        reset_n = 1'b0;
        repeat (4) @(posedge clk);
        reset_n = 1'b1;
        #1;

        check_condition(period_index == 4'd6, "initial period index must be 6");

        // Quiet pass 1: hold period, remember one quiet pass.
        finish_pass();
        check_condition(period_index == 4'd6, "first quiet pass should hold period");
        check_condition(quiet_pass_count == 32'd1, "first quiet pass should increment quiet counter");

        // Quiet pass 2: relax period index upward.
        finish_pass();
        check_condition(period_index == 4'd7, "second quiet pass should relax period to index 7");
        check_condition(quiet_pass_count == 32'd0, "relax should clear quiet counter");

        // High corrected activity: speed up period index downward.
        pulse_corrected();
        pulse_corrected();
        pulse_corrected();
        finish_pass();
        check_condition(period_index == 4'd6, "high corrected activity should speed up to index 6");

        pulse_corrected();
        pulse_corrected();
        pulse_corrected();
        finish_pass();
        check_condition(period_index == 4'd5, "second high activity pass should speed up to index 5");

        // Moderate single correction below threshold: hold, no quiet relaxation.
        pulse_corrected();
        finish_pass();
        check_condition(period_index == 4'd5, "below-threshold correction should hold period");
        check_condition(quiet_pass_count == 32'd0, "non-quiet below-threshold pass should clear quiet counter");

        // DUE: force conservative safe period.
        pulse_due();
        finish_pass();
        check_condition(period_index == 4'd0, "DUE should force safe period index");
        check_condition(forced_safe_flag == 1'b1, "DUE should latch forced_safe_flag");

        // Clear returns to initial policy state.
        clear = 1'b1;
        @(posedge clk);
        #1;
        clear = 1'b0;

        check_condition(period_index == 4'd6, "clear should restore initial period index");
        check_condition(forced_safe_flag == 1'b0, "clear should reset forced_safe_flag");

        $display("MEASURED_ERROR_ESTIMATOR_SUMMARY final_period_index=%0d updates=%0d high_activity_events=%0d quiet_relax_events=%0d forced_safe_events=%0d failures=%0d",
                 period_index,
                 update_count,
                 high_activity_events,
                 quiet_relax_events,
                 forced_safe_events,
                 failures);

        if (failures != 0) begin
            $fatal(1, "measured-error estimator test failed with %0d failures", failures);
        end

        $display("MEASURED_ERROR_ESTIMATOR_PASS");
        $finish;
    end

endmodule
''',
        encoding="utf-8",
    )

    return tb_path


def parse_summary(output: str) -> dict[str, str]:
    pattern = re.compile(
        r"MEASURED_ERROR_ESTIMATOR_SUMMARY final_period_index=(\d+) updates=(\d+) "
        r"high_activity_events=(\d+) quiet_relax_events=(\d+) forced_safe_events=(\d+) failures=(\d+)"
    )

    match = pattern.search(output)
    if not match:
        raise RuntimeError("could not parse measured-error estimator summary")

    keys = [
        "final_period_index",
        "updates",
        "high_activity_events",
        "quiet_relax_events",
        "forced_safe_events",
        "failures",
    ]

    return {key: value for key, value in zip(keys, match.groups(), strict=True)}


def write_outputs(row: dict[str, str]) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "final_period_index",
        "updates",
        "high_activity_events",
        "quiet_relax_events",
        "forced_safe_events",
        "failures",
    ]

    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    lines = [
        "# Measured-error period estimator RTL report",
        "",
        "This unit test verifies an autonomous onboard period-index estimator",
        "driven only by SEC-DED corrected/DUE observations.",
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
            "- Quiet passes relax the scrub period toward larger period indices.",
            "- High corrected-event activity accelerates scrubbing by lowering the period index.",
            "- Any DUE forces the conservative safe period index.",
            "- This is an onboard fallback strategy; it is not the exact-risk schedule compiler.",
            "",
        ]
    )

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    tb_path = generate_tb()
    sim_out = BUILD_DIR / "tb_measured_error_estimator.vvp"

    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-o",
        str(sim_out),
        "rtl/scrubber/measured_error_period_estimator.sv",
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
