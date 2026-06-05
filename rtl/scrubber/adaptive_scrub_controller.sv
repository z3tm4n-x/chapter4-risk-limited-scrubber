// Top-level adaptive SEC-DED scrub controller.
//
// This is the Chapter 4 hardware integration point:
//   external period_index -> period_scheduler -> full-pass scrub engine
//
// The controller does not compute the radiation/risk model. It executes an
// implementable schedule produced outside RTL by the Chapter 3 compiler.

`timescale 1ns/1ps

module adaptive_scrub_controller #(
    parameter int ADDR_WIDTH = 4,
    parameter int DEPTH = 16,

    parameter int PERIOD_INDEX_WIDTH = 4,

    parameter int PERIOD0_CYCLES  = 10,
    parameter int PERIOD1_CYCLES  = 20,
    parameter int PERIOD2_CYCLES  = 50,
    parameter int PERIOD3_CYCLES  = 100,
    parameter int PERIOD4_CYCLES  = 200,
    parameter int PERIOD5_CYCLES  = 500,
    parameter int PERIOD6_CYCLES  = 1000,
    parameter int PERIOD7_CYCLES  = 2000,
    parameter int PERIOD8_CYCLES  = 2000,
    parameter int PERIOD9_CYCLES  = 2000,
    parameter int PERIOD10_CYCLES = 2000,
    parameter int PERIOD11_CYCLES = 2000,

    parameter int SAFE_PERIOD_INDEX = 0,
    parameter int MAX_CONTROL_AGE_CYCLES = 200
) (
    input  logic                            clk,
    input  logic                            reset_n,

    input  logic                            period_update_valid,
    input  logic [PERIOD_INDEX_WIDTH-1:0]   period_index,

    output logic                            mem_read_en,
    output logic                            mem_write_en,
    output logic [ADDR_WIDTH-1:0]           mem_addr,
    input  logic [38:0]                     mem_read_data,
    output logic [38:0]                     mem_write_data,

    output logic                            pass_start,
    output logic                            pass_active,
    output logic                            pass_done,

    output logic [PERIOD_INDEX_WIDTH-1:0]   applied_period_index,
    output logic [31:0]                     selected_period_cycles,
    output logic                            safe_mode_active,
    output logic                            stale_control_flag,
    output logic [31:0]                     last_pass_cycles,

    output logic                            corrected_pulse,
    output logic                            detected_uncorrectable_pulse,

    output logic [31:0]                     pass_count,
    output logic [31:0]                     read_count,
    output logic [31:0]                     write_count,
    output logic [31:0]                     corrected_count,
    output logic [31:0]                     detected_uncorrectable_count,
    output logic [31:0]                     safe_mode_entry_count
);

    logic scheduler_pass_start;
    logic engine_pass_done;

    assign pass_start = scheduler_pass_start;
    assign pass_done = engine_pass_done;

    period_scheduler #(
        .PERIOD_INDEX_WIDTH(PERIOD_INDEX_WIDTH),
        .PERIOD0_CYCLES(PERIOD0_CYCLES),
        .PERIOD1_CYCLES(PERIOD1_CYCLES),
        .PERIOD2_CYCLES(PERIOD2_CYCLES),
        .PERIOD3_CYCLES(PERIOD3_CYCLES),
        .PERIOD4_CYCLES(PERIOD4_CYCLES),
        .PERIOD5_CYCLES(PERIOD5_CYCLES),
        .PERIOD6_CYCLES(PERIOD6_CYCLES),
        .PERIOD7_CYCLES(PERIOD7_CYCLES),
        .PERIOD8_CYCLES(PERIOD8_CYCLES),
        .PERIOD9_CYCLES(PERIOD9_CYCLES),
        .PERIOD10_CYCLES(PERIOD10_CYCLES),
        .PERIOD11_CYCLES(PERIOD11_CYCLES),
        .SAFE_PERIOD_INDEX(SAFE_PERIOD_INDEX),
        .MAX_CONTROL_AGE_CYCLES(MAX_CONTROL_AGE_CYCLES)
    ) scheduler (
        .clk(clk),
        .reset_n(reset_n),
        .period_update_valid(period_update_valid),
        .period_index(period_index),
        .pass_done(engine_pass_done),
        .pass_start(scheduler_pass_start),
        .applied_period_index(applied_period_index),
        .selected_period_cycles(selected_period_cycles),
        .safe_mode_active(safe_mode_active),
        .stale_control_flag(stale_control_flag),
        .last_pass_cycles(last_pass_cycles),
        .safe_mode_entry_count(safe_mode_entry_count)
    );

    scrub_pass_engine #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DEPTH(DEPTH)
    ) pass_engine (
        .clk(clk),
        .reset_n(reset_n),
        .pass_start(scheduler_pass_start),
        .pass_active(pass_active),
        .pass_done(engine_pass_done),
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

endmodule
