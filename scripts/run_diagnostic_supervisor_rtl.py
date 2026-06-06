#!/usr/bin/env python3
"""Run the diagnostic supervisor RTL unit test."""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "rtl_replay"
BUILD_DIR = REPO_ROOT / "generated" / "rtl"
TB_DIR = BUILD_DIR / "diagnostic_supervisor"

SUMMARY_CSV = RESULT_DIR / "diagnostic_supervisor_summary.csv"
SUMMARY_MD = RESULT_DIR / "diagnostic_supervisor_report.md"
LOG_PATH = RESULT_DIR / "diagnostic_supervisor.log"


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
    tb_path = TB_DIR / "tb_diagnostic_supervisor.sv"

    tb_path.write_text(
        r'''`timescale 1ns/1ps

module tb_diagnostic_supervisor;

    logic clk;
    logic reset_n;
    logic clear_flags;

    logic corrected_pulse;
    logic detected_uncorrectable_pulse;
    logic [3:0] detected_uncorrectable_addr;
    logic pass_done;

    logic alert_flag;
    logic danger_detected_flag;
    logic persistent_due_flag;
    logic out_of_envelope_flag;
    logic force_conservative;

    logic [31:0] pass_corrected_count;
    logic [31:0] alert_event_count;
    logic [31:0] danger_event_count;
    logic [31:0] new_due_word_count;
    logic [31:0] persistent_due_count;
    logic [31:0] consecutive_alert_passes;

    integer failures;

    diagnostic_supervisor #(
        .ADDR_WIDTH(4),
        .DEPTH(16),
        .CORRECTED_ALERT_THRESHOLD(3),
        .ALERT_CONSECUTIVE_THRESHOLD(2),
        .PERSISTENT_DUE_THRESHOLD(1)
    ) dut (
        .clk(clk),
        .reset_n(reset_n),
        .clear_flags(clear_flags),
        .corrected_pulse(corrected_pulse),
        .detected_uncorrectable_pulse(detected_uncorrectable_pulse),
        .detected_uncorrectable_addr(detected_uncorrectable_addr),
        .pass_done(pass_done),
        .alert_flag(alert_flag),
        .danger_detected_flag(danger_detected_flag),
        .persistent_due_flag(persistent_due_flag),
        .out_of_envelope_flag(out_of_envelope_flag),
        .force_conservative(force_conservative),
        .pass_corrected_count(pass_corrected_count),
        .alert_event_count(alert_event_count),
        .danger_event_count(danger_event_count),
        .new_due_word_count(new_due_word_count),
        .persistent_due_count(persistent_due_count),
        .consecutive_alert_passes(consecutive_alert_passes)
    );

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
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

    task automatic pulse_due(input logic [3:0] addr);
        begin
            detected_uncorrectable_addr = addr;
            detected_uncorrectable_pulse = 1'b1;
            @(posedge clk);
            #1;
            detected_uncorrectable_pulse = 1'b0;
        end
    endtask

    task automatic pulse_pass_done;
        begin
            pass_done = 1'b1;
            @(posedge clk);
            #1;
            pass_done = 1'b0;
        end
    endtask

    task automatic pulse_clear;
        begin
            clear_flags = 1'b1;
            @(posedge clk);
            #1;
            clear_flags = 1'b0;
        end
    endtask

    initial begin
        failures = 0;

        clear_flags = 1'b0;
        corrected_pulse = 1'b0;
        detected_uncorrectable_pulse = 1'b0;
        detected_uncorrectable_addr = 4'd0;
        pass_done = 1'b0;

        reset_n = 1'b0;
        repeat (4) @(posedge clk);
        reset_n = 1'b1;
        #1;

        // Normal empty pass: no flags.
        pulse_pass_done();
        check_condition(alert_flag == 1'b0, "normal pass must not assert alert");
        check_condition(danger_detected_flag == 1'b0, "normal pass must not assert danger");
        check_condition(out_of_envelope_flag == 1'b0, "normal pass must not assert out-of-envelope");
        check_condition(force_conservative == 1'b0, "normal pass must not force conservative mode");

        // First alert pass: corrected count reaches threshold.
        pulse_corrected();
        pulse_corrected();
        pulse_corrected();
        pulse_pass_done();

        check_condition(alert_flag == 1'b1, "first high-correction pass should assert alert");
        check_condition(alert_event_count == 32'd1, "first alert pass should increment alert_event_count");
        check_condition(consecutive_alert_passes == 32'd1, "first alert pass should set consecutive_alert_passes=1");
        check_condition(out_of_envelope_flag == 1'b0, "one alert pass should not yet assert out-of-envelope");

        // Second consecutive alert pass: out-of-envelope.
        pulse_corrected();
        pulse_corrected();
        pulse_corrected();
        pulse_pass_done();

        check_condition(alert_event_count == 32'd2, "second alert pass should increment alert_event_count");
        check_condition(consecutive_alert_passes == 32'd2, "second alert pass should set consecutive_alert_passes=2");
        check_condition(out_of_envelope_flag == 1'b1, "two alert passes should assert out-of-envelope");
        check_condition(force_conservative == 1'b1, "out-of-envelope should force conservative mode");

        // Clear and check DUE/persistent-DUE logic separately.
        pulse_clear();

        check_condition(alert_flag == 1'b0, "clear should deassert alert");
        check_condition(danger_detected_flag == 1'b0, "clear should deassert danger");
        check_condition(persistent_due_flag == 1'b0, "clear should deassert persistent due");
        check_condition(out_of_envelope_flag == 1'b0, "clear should deassert out-of-envelope");
        check_condition(force_conservative == 1'b0, "clear should deassert force_conservative");

        pulse_due(4'd5);

        check_condition(danger_detected_flag == 1'b1, "new DUE should assert danger");
        check_condition(danger_event_count == 32'd1, "new DUE should increment danger_event_count");
        check_condition(new_due_word_count == 32'd1, "first DUE at word should increment new_due_word_count");
        check_condition(persistent_due_flag == 1'b0, "first DUE at word should not be persistent");
        check_condition(force_conservative == 1'b1, "danger should force conservative mode");

        pulse_due(4'd5);

        check_condition(danger_event_count == 32'd2, "second DUE should increment danger_event_count");
        check_condition(new_due_word_count == 32'd1, "repeated DUE should not increment new_due_word_count");
        check_condition(persistent_due_flag == 1'b1, "repeated DUE should assert persistent_due");
        check_condition(persistent_due_count == 32'd1, "repeated DUE should increment persistent_due_count");
        check_condition(out_of_envelope_flag == 1'b1, "persistent DUE should assert out-of-envelope");

        $display("DIAGNOSTIC_SUPERVISOR_SUMMARY alert_events=%0d danger_events=%0d new_due_words=%0d persistent_due=%0d consecutive_alert_passes=%0d out_of_envelope=%0d force_conservative=%0d failures=%0d",
                 alert_event_count,
                 danger_event_count,
                 new_due_word_count,
                 persistent_due_count,
                 consecutive_alert_passes,
                 out_of_envelope_flag,
                 force_conservative,
                 failures);

        if (failures != 0) begin
            $fatal(1, "diagnostic supervisor test failed with %0d failures", failures);
        end

        $display("DIAGNOSTIC_SUPERVISOR_PASS");
        $finish;
    end

endmodule
''',
        encoding="utf-8",
    )

    return tb_path


def parse_summary(output: str) -> dict[str, str]:
    pattern = re.compile(
        r"DIAGNOSTIC_SUPERVISOR_SUMMARY alert_events=(\d+) danger_events=(\d+) "
        r"new_due_words=(\d+) persistent_due=(\d+) consecutive_alert_passes=(\d+) "
        r"out_of_envelope=(\d+) force_conservative=(\d+) failures=(\d+)"
    )

    match = pattern.search(output)
    if not match:
        raise RuntimeError("could not parse diagnostic supervisor summary")

    keys = [
        "alert_events",
        "danger_events",
        "new_due_words",
        "persistent_due",
        "consecutive_alert_passes",
        "out_of_envelope",
        "force_conservative",
        "failures",
    ]

    return {key: value for key, value in zip(keys, match.groups(), strict=True)}


def write_outputs(row: dict[str, str]) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "alert_events",
        "danger_events",
        "new_due_words",
        "persistent_due",
        "consecutive_alert_passes",
        "out_of_envelope",
        "force_conservative",
        "failures",
    ]

    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    lines = [
        "# Diagnostic supervisor RTL report",
        "",
        "This unit test verifies the hardware diagnostic layer used to escalate",
        "from ordinary SEC-DED scrubbing to conservative/out-of-envelope modes.",
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
            "- A high corrected-event count raises `alert_flag`.",
            "- Consecutive alert passes raise `out_of_envelope_flag`.",
            "- A new DUE raises `danger_detected_flag` and `force_conservative`.",
            "- Repeated DUE at the same word raises `persistent_due_flag` and `out_of_envelope_flag`.",
            "- The block observes SEC-DED symptoms; it does not compute the radiation model.",
            "",
        ]
    )

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    tb_path = generate_tb()
    sim_out = BUILD_DIR / "tb_diagnostic_supervisor.vvp"

    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-o",
        str(sim_out),
        "rtl/scrubber/diagnostic_supervisor.sv",
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
