// Integrated measured-error adaptive scrub controller.
//
// This top-level connects the autonomous measured-error estimator to the same
// period_index interface consumed by the regular adaptive scrub controller.
//
// It is a practical onboard fallback mode:
//   SEC-DED observations -> measured_error_period_estimator -> period_index
//
// It does not compute nu(t), g_D, E_residual, or exact mission risk.

`timescale 1ns/1ps

module measured_error_scrub_controller #(
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

    parameter int MEASURED_MIN_PERIOD_INDEX = 0,
    parameter int MEASURED_MAX_PERIOD_INDEX = 11,
    parameter int MEASURED_INITIAL_PERIOD_INDEX = 6,
    parameter int MEASURED_CORRECTED_HIGH_THRESHOLD = 3,
    parameter int MEASURED_CORRECTED_LOW_THRESHOLD = 0,
    parameter int MEASURED_QUIET_PASS_THRESHOLD = 2,
    parameter int MEASURED_SPEEDUP_STEP = 1,
    parameter int MEASURED_RELAX_STEP = 1,

    parameter int DIAG_CORRECTED_ALERT_THRESHOLD = 4,
    parameter int DIAG_ALERT_CONSECUTIVE_THRESHOLD = 2,
    parameter int DIAG_PERSISTENT_DUE_THRESHOLD = 1
) (
    input  logic                            clk,
    input  logic                            reset_n,
    input  logic                            time_tick,

    input  logic                            measured_enable,
    input  logic                            measured_clear,

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

    output logic [31:0]                     diag_alert_event_count,
    output logic [31:0]                     diag_danger_event_count,
    output logic [31:0]                     diag_new_due_word_count,
    output logic [31:0]                     diag_persistent_due_count,

    output logic                            measured_period_update_valid,
    output logic [PERIOD_INDEX_WIDTH-1:0]   measured_period_index,
    output logic [31:0]                     measured_corrected_count_in_pass,
    output logic [31:0]                     measured_due_count_in_pass,
    output logic [31:0]                     measured_quiet_pass_count,
    output logic                            measured_high_activity_flag,
    output logic                            measured_quiet_relax_flag,
    output logic                            measured_forced_safe_flag
);

    logic [31:0] unused_diag_pass_corrected_count;
    logic [31:0] unused_diag_consecutive_alert_passes;

    measured_error_period_estimator #(
        .PERIOD_INDEX_WIDTH(PERIOD_INDEX_WIDTH),
        .MIN_PERIOD_INDEX(MEASURED_MIN_PERIOD_INDEX),
        .MAX_PERIOD_INDEX(MEASURED_MAX_PERIOD_INDEX),
        .INITIAL_PERIOD_INDEX(MEASURED_INITIAL_PERIOD_INDEX),
        .SAFE_PERIOD_INDEX(SAFE_PERIOD_INDEX),
        .CORRECTED_HIGH_THRESHOLD(MEASURED_CORRECTED_HIGH_THRESHOLD),
        .CORRECTED_LOW_THRESHOLD(MEASURED_CORRECTED_LOW_THRESHOLD),
        .QUIET_PASS_THRESHOLD(MEASURED_QUIET_PASS_THRESHOLD),
        .SPEEDUP_STEP(MEASURED_SPEEDUP_STEP),
        .RELAX_STEP(MEASURED_RELAX_STEP)
    ) estimator (
        .clk(clk),
        .reset_n(reset_n),
        .clear(measured_clear),
        .enable(measured_enable),
        .corrected_pulse(corrected_pulse),
        .detected_uncorrectable_pulse(detected_uncorrectable_pulse),
        .pass_done(pass_done),
        .period_update_valid(measured_period_update_valid),
        .period_index(measured_period_index),
        .corrected_count_in_pass(measured_corrected_count_in_pass),
        .due_count_in_pass(measured_due_count_in_pass),
        .quiet_pass_count(measured_quiet_pass_count),
        .high_activity_flag(measured_high_activity_flag),
        .quiet_relax_flag(measured_quiet_relax_flag),
        .forced_safe_flag(measured_forced_safe_flag)
    );

    adaptive_scrub_controller #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DEPTH(DEPTH),
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
        .MAX_CONTROL_AGE_CYCLES(MAX_CONTROL_AGE_CYCLES),
        .DIAG_CORRECTED_ALERT_THRESHOLD(DIAG_CORRECTED_ALERT_THRESHOLD),
        .DIAG_ALERT_CONSECUTIVE_THRESHOLD(DIAG_ALERT_CONSECUTIVE_THRESHOLD),
        .DIAG_PERSISTENT_DUE_THRESHOLD(DIAG_PERSISTENT_DUE_THRESHOLD)
    ) controller (
        .clk(clk),
        .reset_n(reset_n),
        .time_tick(time_tick),
        .period_update_valid(measured_period_update_valid),
        .period_index(measured_period_index),
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
        .diag_pass_corrected_count(unused_diag_pass_corrected_count),
        .diag_alert_event_count(diag_alert_event_count),
        .diag_danger_event_count(diag_danger_event_count),
        .diag_new_due_word_count(diag_new_due_word_count),
        .diag_persistent_due_count(diag_persistent_due_count),
        .diag_consecutive_alert_passes(unused_diag_consecutive_alert_passes)
    );

endmodule
