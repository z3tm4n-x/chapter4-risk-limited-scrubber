// Diagnostic supervisor for scrub-controller health and protection-envelope flags.
//
// This block intentionally does not compute the Chapter 2/3 radiation model.
// It observes hardware symptoms produced by the SEC-DED scrub path and raises
// system-level flags:
//   - alert_flag: corrected-event count in a pass exceeds a configured threshold;
//   - danger_detected_flag: at least one online DUE was observed;
//   - persistent_due_flag: the same tracked DUE word was observed more than once;
//   - out_of_envelope_flag: repeated alerts or persistent DUE indicate that
//     ordinary SEC-DED scrubbing is no longer sufficient;
//   - force_conservative: request a conservative system mode.
//
// DUE persistence is tracked by a bounded associative table, not by a
// full DEPTH-bit bitmap. If the table overflows, the supervisor raises
// out_of_envelope_flag conservatively.

`timescale 1ns/1ps

module diagnostic_supervisor #(
    parameter int ADDR_WIDTH = 4,
    parameter int DEPTH = 16,

    parameter int CORRECTED_ALERT_THRESHOLD = 4,
    parameter int ALERT_CONSECUTIVE_THRESHOLD = 2,
    parameter int PERSISTENT_DUE_THRESHOLD = 1,
    parameter int DUE_TRACKER_ENTRIES = 16
) (
    input  logic                          clk,
    input  logic                          reset_n,

    input  logic                          clear_flags,

    input  logic                          corrected_pulse,
    input  logic                          detected_uncorrectable_pulse,
    input  logic [ADDR_WIDTH-1:0]         detected_uncorrectable_addr,

    input  logic                          pass_done,

    output logic                          alert_flag,
    output logic                          danger_detected_flag,
    output logic                          persistent_due_flag,
    output logic                          out_of_envelope_flag,
    output logic                          force_conservative,

    output logic [31:0]                   pass_corrected_count,
    output logic [31:0]                   alert_event_count,
    output logic [31:0]                   danger_event_count,
    output logic [31:0]                   new_due_word_count,
    output logic [31:0]                   persistent_due_count,
    output logic [31:0]                   consecutive_alert_passes
);

    localparam int DUE_TRACKER_INDEX_WIDTH =
        (DUE_TRACKER_ENTRIES <= 1) ? 1 : $clog2(DUE_TRACKER_ENTRIES);

    logic [DUE_TRACKER_ENTRIES-1:0] due_tracker_valid;
    logic [ADDR_WIDTH-1:0]          due_tracker_addr [0:DUE_TRACKER_ENTRIES-1];

    logic                           due_tracker_hit;
    logic                           due_tracker_free_found;
    logic [DUE_TRACKER_INDEX_WIDTH-1:0] due_tracker_free_index;

    integer due_scan_i;
    integer due_reset_i;

    always_comb begin
        due_tracker_hit = 1'b0;
        due_tracker_free_found = 1'b0;
        due_tracker_free_index = '0;

        for (due_scan_i = 0; due_scan_i < DUE_TRACKER_ENTRIES; due_scan_i = due_scan_i + 1) begin
            if (due_tracker_valid[due_scan_i] &&
                (due_tracker_addr[due_scan_i] == detected_uncorrectable_addr)) begin
                due_tracker_hit = 1'b1;
            end

            if (!due_tracker_valid[due_scan_i] && !due_tracker_free_found) begin
                due_tracker_free_found = 1'b1;
                due_tracker_free_index = due_scan_i[DUE_TRACKER_INDEX_WIDTH-1:0];
            end
        end
    end

    assign force_conservative = danger_detected_flag | persistent_due_flag | out_of_envelope_flag;

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            due_tracker_valid <= '0;
            for (due_reset_i = 0; due_reset_i < DUE_TRACKER_ENTRIES; due_reset_i = due_reset_i + 1) begin
                due_tracker_addr[due_reset_i] <= '0;
            end

            alert_flag <= 1'b0;
            danger_detected_flag <= 1'b0;
            persistent_due_flag <= 1'b0;
            out_of_envelope_flag <= 1'b0;

            pass_corrected_count <= 32'd0;
            alert_event_count <= 32'd0;
            danger_event_count <= 32'd0;
            new_due_word_count <= 32'd0;
            persistent_due_count <= 32'd0;
            consecutive_alert_passes <= 32'd0;
        end else if (clear_flags) begin
            due_tracker_valid <= '0;
            for (due_reset_i = 0; due_reset_i < DUE_TRACKER_ENTRIES; due_reset_i = due_reset_i + 1) begin
                due_tracker_addr[due_reset_i] <= '0;
            end

            alert_flag <= 1'b0;
            danger_detected_flag <= 1'b0;
            persistent_due_flag <= 1'b0;
            out_of_envelope_flag <= 1'b0;

            pass_corrected_count <= 32'd0;
            alert_event_count <= 32'd0;
            danger_event_count <= 32'd0;
            new_due_word_count <= 32'd0;
            persistent_due_count <= 32'd0;
            consecutive_alert_passes <= 32'd0;
        end else begin
            if (corrected_pulse) begin
                pass_corrected_count <= pass_corrected_count + 32'd1;
            end

            if (detected_uncorrectable_pulse) begin
                danger_detected_flag <= 1'b1;
                danger_event_count <= danger_event_count + 32'd1;

                if (due_tracker_hit) begin
                    persistent_due_flag <= 1'b1;
                    persistent_due_count <= persistent_due_count + 32'd1;

                    if ((persistent_due_count + 32'd1) >= PERSISTENT_DUE_THRESHOLD[31:0]) begin
                        out_of_envelope_flag <= 1'b1;
                    end
                end else if (due_tracker_free_found) begin
                    due_tracker_valid[due_tracker_free_index] <= 1'b1;
                    due_tracker_addr[due_tracker_free_index] <= detected_uncorrectable_addr;
                    new_due_word_count <= new_due_word_count + 32'd1;
                end else begin
                    // Bounded tracker exhausted: persistence can no longer be
                    // classified exactly, so escalate conservatively.
                    out_of_envelope_flag <= 1'b1;
                end
            end

            if (pass_done) begin
                if ((CORRECTED_ALERT_THRESHOLD > 0) &&
                    (pass_corrected_count >= CORRECTED_ALERT_THRESHOLD[31:0])) begin
                    alert_flag <= 1'b1;
                    alert_event_count <= alert_event_count + 32'd1;
                    consecutive_alert_passes <= consecutive_alert_passes + 32'd1;

                    if ((consecutive_alert_passes + 32'd1) >= ALERT_CONSECUTIVE_THRESHOLD[31:0]) begin
                        out_of_envelope_flag <= 1'b1;
                    end
                end else begin
                    consecutive_alert_passes <= 32'd0;
                end

                pass_corrected_count <= 32'd0;
            end
        end
    end

endmodule
