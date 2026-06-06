#!/usr/bin/env python3
"""RTL interleaving experiment for one physical MBU event.

The experiment compares two logical mappings of the same 3-bit physical event:

  D=1: all affected bits land in one SEC-DED codeword.
       This is outside the guaranteed SEC-DED correction envelope.

  D=3: affected bits are split across three different codewords.
       Each codeword contains one bit error and is corrected by scrubbing.

This script verifies the Chapter 2/4 point that interleaving does not change
the physical event, but changes whether it becomes an online-correctable
accumulated pattern or a dangerous same-codeword state.
"""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = REPO_ROOT / "results" / "rtl_replay"
BUILD_DIR = REPO_ROOT / "generated" / "rtl"
TB_DIR = BUILD_DIR / "interleaving_mbu"

SUMMARY_CSV = RESULT_DIR / "interleaving_mbu_summary.csv"
SUMMARY_MD = RESULT_DIR / "interleaving_mbu_summary.md"


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
    tb_path = TB_DIR / "tb_interleaving_mbu.sv"

    tb_path.write_text(
        r'''`timescale 1ns/1ps

module tb_interleaving_mbu;

    localparam int ADDR_WIDTH = 3;
    localparam int DEPTH = 8;

    logic clk;
    logic reset_n;

    logic pass_start;
    logic pass_active;
    logic pass_done;

    logic mem_read_en;
    logic mem_write_en;
    logic [ADDR_WIDTH-1:0] mem_addr;
    logic [38:0] mem_read_data;
    logic [38:0] mem_write_data;

    logic corrected_pulse;
    logic detected_uncorrectable_pulse;

    logic [31:0] pass_count;
    logic [31:0] read_count;
    logic [31:0] write_count;
    logic [31:0] corrected_count;
    logic [31:0] detected_uncorrectable_count;

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

    integer addr;
    integer scenario;
    integer failures;

    integer d1_corrected;
    integer d1_due_events;
    integer d1_writes;
    integer d1_final_uncorrectable;
    integer d1_final_sdc;
    integer d1_final_dangerous;

    integer d3_corrected;
    integer d3_due_events;
    integer d3_writes;
    integer d3_final_uncorrectable;
    integer d3_final_sdc;
    integer d3_final_dangerous;

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

    scrub_pass_engine #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DEPTH(DEPTH)
    ) dut (
        .clk(clk),
        .reset_n(reset_n),
        .pass_start(pass_start),
        .pass_active(pass_active),
        .pass_done(pass_done),
        .mem_read_en(mem_read_en),
        .mem_write_en(mem_write_en),
        .mem_addr(mem_addr),
        .mem_read_data(mem_read_data),
        .mem_write_data(mem_write_data),
        .corrected_pulse(corrected_pulse),
        .detected_uncorrectable_pulse(detected_uncorrectable_pulse),
        .pass_count(pass_count),
        .read_count(read_count),
        .write_count(write_count),
        .corrected_count(corrected_count),
        .detected_uncorrectable_count(detected_uncorrectable_count)
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

    task automatic initialize_memory;
        begin
            for (addr = 0; addr < DEPTH; addr = addr + 1) begin
                encoder_data = 32'h8000_0000 + addr[31:0];
                golden_data[addr] = encoder_data;
                #1;
                memory[addr] = encoder_codeword;
            end
        end
    endtask

    task automatic audit_final_memory(
        output integer final_uncorrectable,
        output integer final_sdc,
        output integer final_dangerous
    );
        begin
            final_uncorrectable = 0;
            final_sdc = 0;

            for (addr = 0; addr < DEPTH; addr = addr + 1) begin
                audit_codeword = memory[addr];
                #1;

                if (audit_detected_uncorrectable) begin
                    final_uncorrectable = final_uncorrectable + 1;
                end else if (audit_data !== golden_data[addr]) begin
                    final_sdc = final_sdc + 1;
                end
            end

            final_dangerous = final_uncorrectable + final_sdc;
        end
    endtask

    task automatic run_one_pass;
        begin
            pass_start = 1'b1;
            @(posedge clk);
            pass_start = 1'b0;

            while (!pass_done) begin
                @(posedge clk);
            end

            @(posedge clk);
        end
    endtask

    initial begin
        failures = 0;
        pass_start = 1'b0;
        reset_n = 1'b0;

        initialize_memory();

        repeat (5) @(posedge clk);
        reset_n = 1'b1;
        repeat (2) @(posedge clk);

        // Scenario D=1: one physical 3-bit MBU maps into one SEC-DED word.
        scenario = 1;
        memory[1] = memory[1] ^ 39'h0000000010; // bit 4
        memory[1] = memory[1] ^ 39'h0000000020; // bit 5
        memory[1] = memory[1] ^ 39'h0000000040; // bit 6

        run_one_pass();

        d1_corrected = corrected_count;
        d1_due_events = detected_uncorrectable_count;
        d1_writes = write_count;
        audit_final_memory(d1_final_uncorrectable, d1_final_sdc, d1_final_dangerous);

        // Reset DUT and memory for scenario D=3.
        reset_n = 1'b0;
        repeat (5) @(posedge clk);
        initialize_memory();
        repeat (2) @(posedge clk);
        reset_n = 1'b1;
        repeat (2) @(posedge clk);

        // Scenario D=3: the same physical 3-bit MBU is split across three
        // codewords, so each codeword has a single-bit error.
        scenario = 3;
        memory[2] = memory[2] ^ 39'h0000000010; // bit 4
        memory[3] = memory[3] ^ 39'h0000000020; // bit 5
        memory[4] = memory[4] ^ 39'h0000000040; // bit 6

        run_one_pass();

        d3_corrected = corrected_count;
        d3_due_events = detected_uncorrectable_count;
        d3_writes = write_count;
        audit_final_memory(d3_final_uncorrectable, d3_final_sdc, d3_final_dangerous);

        // D=1 is outside the guaranteed SEC-DED envelope. Depending on the
        // concrete triple-bit pattern, it may become online DUE or SDC.
        check_condition(d1_final_dangerous >= 1, "D=1 same-word MBU should leave a dangerous word");

        // D=3 should be fully repaired as three independent single-bit errors.
        check_condition(d3_corrected >= 3, "D=3 split MBU should produce at least three corrections");
        check_condition(d3_writes >= 3, "D=3 split MBU should write back corrected words");
        check_condition(d3_due_events == 0, "D=3 split MBU should not produce DUE");
        check_condition(d3_final_dangerous == 0, "D=3 split MBU should finish without dangerous words");

        $display("INTERLEAVING_MBU_SUMMARY scenario=D1_same_word physical_multiplicity=3 interleave_depth=1 corrected=%0d detected_due=%0d writes=%0d final_uncorrectable=%0d final_sdc=%0d final_dangerous=%0d failures=%0d",
                 d1_corrected,
                 d1_due_events,
                 d1_writes,
                 d1_final_uncorrectable,
                 d1_final_sdc,
                 d1_final_dangerous,
                 failures);

        $display("INTERLEAVING_MBU_SUMMARY scenario=D3_split physical_multiplicity=3 interleave_depth=3 corrected=%0d detected_due=%0d writes=%0d final_uncorrectable=%0d final_sdc=%0d final_dangerous=%0d failures=%0d",
                 d3_corrected,
                 d3_due_events,
                 d3_writes,
                 d3_final_uncorrectable,
                 d3_final_sdc,
                 d3_final_dangerous,
                 failures);

        if (failures != 0) begin
            $fatal(1, "interleaving MBU experiment failed with %0d failures", failures);
        end

        $display("INTERLEAVING_MBU_PASS");
        $finish;
    end

endmodule
''',
        encoding="utf-8",
    )

    return tb_path


def parse_summary(output: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r"INTERLEAVING_MBU_SUMMARY scenario=(\S+) physical_multiplicity=(\d+) "
        r"interleave_depth=(\d+) corrected=(\d+) detected_due=(\d+) writes=(\d+) "
        r"final_uncorrectable=(\d+) final_sdc=(\d+) final_dangerous=(\d+) failures=(\d+)"
    )

    rows: list[dict[str, str]] = []

    for match in pattern.finditer(output):
        rows.append(
            {
                "scenario": match.group(1),
                "physical_multiplicity": match.group(2),
                "interleave_depth": match.group(3),
                "corrected": match.group(4),
                "detected_due": match.group(5),
                "writes": match.group(6),
                "final_uncorrectable": match.group(7),
                "final_sdc": match.group(8),
                "final_dangerous": match.group(9),
                "failures": match.group(10),
            }
        )

    if len(rows) != 2:
        raise RuntimeError(f"expected 2 summary rows, got {len(rows)}")

    return rows


def write_outputs(rows: list[dict[str, str]]) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scenario",
        "physical_multiplicity",
        "interleave_depth",
        "corrected",
        "detected_due",
        "writes",
        "final_uncorrectable",
        "final_sdc",
        "final_dangerous",
        "failures",
    ]

    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Interleaving MBU RTL experiment",
        "",
        "The same physical 3-bit MBU is replayed with two logical mappings.",
        "",
        "| Scenario | Physical multiplicity | Interleave depth | Corrected | DUE | Writes | Final DUE | Final SDC | Final dangerous | Failures |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            f"| {row['scenario']} | {row['physical_multiplicity']} | {row['interleave_depth']} | "
            f"{row['corrected']} | {row['detected_due']} | {row['writes']} | "
            f"{row['final_uncorrectable']} | {row['final_sdc']} | {row['final_dangerous']} | {row['failures']} |"
        )

    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- Without interleaving, the physical MBU maps into one SEC-DED codeword and leaves the guaranteed correction envelope.",
            "- With interleaving depth 3, the same physical multiplicity maps to three single-bit codeword errors and is repaired by scrub writeback.",
            "- SDC is reported only by golden-reference verification audit, not by online SEC-DED hardware.",
            "",
        ]
    )

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    tb_path = generate_tb()
    sim_out = BUILD_DIR / "tb_interleaving_mbu.vvp"
    log_path = RESULT_DIR / "interleaving_mbu.log"

    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-o",
        str(sim_out),
        "rtl/ecc/secded_32_39_encoder.sv",
        "rtl/ecc/secded_32_39_decoder.sv",
        "rtl/scrubber/scrub_pass_engine.sv",
        str(tb_path),
    ]

    compile_proc = run_cmd(compile_cmd)

    if compile_proc.returncode != 0:
        log_path.write_text(compile_proc.stdout, encoding="utf-8")
        print(compile_proc.stdout)
        raise RuntimeError("compile failed")

    run_proc = run_cmd(["vvp", str(sim_out)])
    log_path.write_text(compile_proc.stdout + run_proc.stdout, encoding="utf-8")
    print(run_proc.stdout)

    if run_proc.returncode != 0:
        raise RuntimeError("simulation failed")

    rows = parse_summary(run_proc.stdout)
    write_outputs(rows)

    print("Wrote", SUMMARY_CSV)
    print("Wrote", SUMMARY_MD)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
