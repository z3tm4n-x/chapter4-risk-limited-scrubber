// Measured-error period estimator.
//
// This block implements a practical onboard fallback/adaptive mode based only
// on SEC-DED scrub observations. It does not compute nu(t), risk, or the
// Chapter 2/3 model. It reacts to observed corrected/DUE events:
//
//   - many corrected events in one pass -> speed up scrub rate;
//   - quiet passes -> relax scrub rate;
//   - any DUE -> force conservative safe period.
//
// The output can be connected to the same period_index interface consumed by
// period_scheduler.

`timescale 1ns/1ps

module measured_error_period_estimator #(
    parameter int PERIOD_INDEX_WIDTH = 4,

    parameter int MIN_PERIOD_INDEX = 0,
    parameter int MAX_PERIOD_INDEX = 11,
    parameter int INITIAL_PERIOD_INDEX = 6,
    parameter int SAFE_PERIOD_INDEX = 0,

    parameter int CORRECTED_HIGH_THRESHOLD = 3,
    parameter int CORRECTED_LOW_THRESHOLD = 0,
    parameter int QUIET_PASS_THRESHOLD = 2,

    parameter int SPEEDUP_STEP = 1,
    parameter int RELAX_STEP = 1
) (
    input  logic                          clk,
    input  logic                          reset_n,

    input  logic                          clear,
    input  logic                          enable,

    input  logic                          corrected_pulse,
    input  logic                          detected_uncorrectable_pulse,
    input  logic                          pass_done,

    output logic                          period_update_valid,
    output logic [PERIOD_INDEX_WIDTH-1:0] period_index,

    output logic [31:0]                   corrected_count_in_pass,
    output logic [31:0]                   due_count_in_pass,
    output logic [31:0]                   quiet_pass_count,

    output logic                          high_activity_flag,
    output logic                          quiet_relax_flag,
    output logic                          forced_safe_flag
);

    function automatic logic [PERIOD_INDEX_WIDTH-1:0] clamp_index(input int value);
        begin
            if (value < MIN_PERIOD_INDEX) begin
                clamp_index = PERIOD_INDEX_WIDTH'(MIN_PERIOD_INDEX);
            end else if (value > MAX_PERIOD_INDEX) begin
                clamp_index = PERIOD_INDEX_WIDTH'(MAX_PERIOD_INDEX);
            end else begin
                clamp_index = PERIOD_INDEX_WIDTH'(value);
            end
        end
    endfunction

    function automatic int current_index_as_int;
        begin
            current_index_as_int = period_index;
        end
    endfunction

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            period_update_valid <= 1'b0;
            period_index <= clamp_index(INITIAL_PERIOD_INDEX);

            corrected_count_in_pass <= 32'd0;
            due_count_in_pass <= 32'd0;
            quiet_pass_count <= 32'd0;

            high_activity_flag <= 1'b0;
            quiet_relax_flag <= 1'b0;
            forced_safe_flag <= 1'b0;
        end else if (clear) begin
            period_update_valid <= 1'b0;
            period_index <= clamp_index(INITIAL_PERIOD_INDEX);

            corrected_count_in_pass <= 32'd0;
            due_count_in_pass <= 32'd0;
            quiet_pass_count <= 32'd0;

            high_activity_flag <= 1'b0;
            quiet_relax_flag <= 1'b0;
            forced_safe_flag <= 1'b0;
        end else begin
            period_update_valid <= 1'b0;
            high_activity_flag <= 1'b0;
            quiet_relax_flag <= 1'b0;

            if (enable) begin
                if (corrected_pulse) begin
                    corrected_count_in_pass <= corrected_count_in_pass + 32'd1;
                end

                if (detected_uncorrectable_pulse) begin
                    due_count_in_pass <= due_count_in_pass + 32'd1;
                end

                if (pass_done) begin
                    period_update_valid <= 1'b1;

                    if ((due_count_in_pass != 32'd0) || detected_uncorrectable_pulse) begin
                        period_index <= clamp_index(SAFE_PERIOD_INDEX);
                        quiet_pass_count <= 32'd0;
                        forced_safe_flag <= 1'b1;
                    end else if ((CORRECTED_HIGH_THRESHOLD > 0) &&
                                 (corrected_count_in_pass >= CORRECTED_HIGH_THRESHOLD[31:0])) begin
                        period_index <= clamp_index(current_index_as_int() - SPEEDUP_STEP);
                        quiet_pass_count <= 32'd0;
                        high_activity_flag <= 1'b1;
                    end else if (corrected_count_in_pass <= CORRECTED_LOW_THRESHOLD[31:0]) begin
                        if ((quiet_pass_count + 32'd1) >= QUIET_PASS_THRESHOLD[31:0]) begin
                            period_index <= clamp_index(current_index_as_int() + RELAX_STEP);
                            quiet_pass_count <= 32'd0;
                            quiet_relax_flag <= 1'b1;
                        end else begin
                            quiet_pass_count <= quiet_pass_count + 32'd1;
                        end
                    end else begin
                        quiet_pass_count <= 32'd0;
                    end

                    corrected_count_in_pass <= 32'd0;
                    due_count_in_pass <= 32'd0;
                end
            end
        end
    end

endmodule
