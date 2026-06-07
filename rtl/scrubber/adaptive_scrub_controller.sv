// Top-level adaptive SEC-DED scrub controller.
//
// This is the Chapter 4 hardware integration point:
//   external period_index -> period_scheduler -> full-pass scrub engine
//
// The controller does not compute the radiation/risk model. It executes an
// implementable schedule produced outside RTL by the Chapter 3 compiler.
//
// The period scheduler counts coarse timebase ticks. Simulation may compress
// time by asserting time_tick every clk; deployment can drive time_tick from
// a 1 Hz or other configured timer.

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
    parameter int MAX_CONTROL_AGE_CYCLES = 200,

    parameter int DIAG_CORRECTED_ALERT_THRESHOLD = 4,
    parameter int DIAG_ALERT_CONSECUTIVE_THRESHOLD = 2,
    parameter int DIAG_PERSISTENT_DUE_THRESHOLD = 1,
    parameter int DIAG_DUE_TRACKER_ENTRIES = 16
) (
    input  logic                            clk,
    input  logic                            reset_n,
    input  logic                            time_tick,

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
    output logic [31:0]                     safe_mode_entry_count,

    output logic                            diag_alert_flag,
    output logic                            diag_danger_detected_flag,
    output logic                            diag_persistent_due_flag,
    output logic                            diag_out_of_envelope_flag,
    output logic                            diag_force_conservative,

    output logic [31:0]                     diag_pass_corrected_count,
    output logic [31:0]                     diag_alert_event_count,
    output logic [31:0]                     diag_danger_event_count,
    output logic [31:0]                     diag_new_due_word_count,
    output logic [31:0]                     diag_persistent_due_count,
    output logic [31:0]                     diag_consecutive_alert_passes
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
        .time_tick(time_tick),
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


    diagnostic_supervisor #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DEPTH(DEPTH),
        .CORRECTED_ALERT_THRESHOLD(DIAG_CORRECTED_ALERT_THRESHOLD),
        .ALERT_CONSECUTIVE_THRESHOLD(DIAG_ALERT_CONSECUTIVE_THRESHOLD),
        .PERSISTENT_DUE_THRESHOLD(DIAG_PERSISTENT_DUE_THRESHOLD),
        .DUE_TRACKER_ENTRIES(DIAG_DUE_TRACKER_ENTRIES)
    ) diagnostic (
        .clk(clk),
        .reset_n(reset_n),
        .clear_flags(1'b0),
        .corrected_pulse(corrected_pulse),
        .detected_uncorrectable_pulse(detected_uncorrectable_pulse),
        .detected_uncorrectable_addr(mem_addr),
        .pass_done(engine_pass_done),
        .alert_flag(diag_alert_flag),
        .danger_detected_flag(diag_danger_detected_flag),
        .persistent_due_flag(diag_persistent_due_flag),
        .out_of_envelope_flag(diag_out_of_envelope_flag),
        .force_conservative(diag_force_conservative),
        .pass_corrected_count(diag_pass_corrected_count),
        .alert_event_count(diag_alert_event_count),
        .danger_event_count(diag_danger_event_count),
        .new_due_word_count(diag_new_due_word_count),
        .persistent_due_count(diag_persistent_due_count),
        .consecutive_alert_passes(diag_consecutive_alert_passes)
    );

endmodule
