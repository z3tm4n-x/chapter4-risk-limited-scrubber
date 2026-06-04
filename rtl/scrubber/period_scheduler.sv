// Period scheduler for the adaptive scrub controller.
//
// This block is the hardware endpoint of the Chapter 3 schedule compiler.
// It does not compute the radiation/risk model. It consumes an external
// period_index and launches full scrub passes so that the interval between two
// checks of the same codeword tracks the selected full-pass period.
//
// If external updates become stale, the scheduler falls back to a conservative
// safe period index.

`timescale 1ns/1ps

module period_scheduler #(
    parameter int PERIOD0_CYCLES = 10,
    parameter int PERIOD1_CYCLES = 20,
    parameter int PERIOD2_CYCLES = 50,
    parameter int PERIOD3_CYCLES = 100,
    parameter int PERIOD4_CYCLES = 200,
    parameter int PERIOD5_CYCLES = 500,
    parameter int PERIOD6_CYCLES = 1000,
    parameter int PERIOD7_CYCLES = 2000,
    parameter int SAFE_PERIOD_INDEX = 0,
    parameter int MAX_CONTROL_AGE_CYCLES = 200
) (
    input  logic        clk,
    input  logic        reset_n,

    input  logic        period_update_valid,
    input  logic [2:0]  period_index,

    input  logic        pass_done,

    output logic        pass_start,
    output logic [2:0]  applied_period_index,
    output logic [31:0] selected_period_cycles,
    output logic        safe_mode_active,
    output logic        stale_control_flag,
    output logic [31:0] last_pass_cycles,
    output logic [31:0] safe_mode_entry_count
);

    typedef enum logic [0:0] {
        S_WAIT   = 1'b0,
        S_INPASS = 1'b1
    } state_t;

    state_t state;

    logic [2:0]  commanded_period_index;
    logic [31:0] control_age_cycles;
    logic [31:0] wait_counter;
    logic [31:0] pass_cycle_counter;
    logic        safe_mode_active_d;

    function automatic logic [31:0] lookup_period_cycles(input logic [2:0] index);
        begin
            case (index)
                3'd0: lookup_period_cycles = PERIOD0_CYCLES;
                3'd1: lookup_period_cycles = PERIOD1_CYCLES;
                3'd2: lookup_period_cycles = PERIOD2_CYCLES;
                3'd3: lookup_period_cycles = PERIOD3_CYCLES;
                3'd4: lookup_period_cycles = PERIOD4_CYCLES;
                3'd5: lookup_period_cycles = PERIOD5_CYCLES;
                3'd6: lookup_period_cycles = PERIOD6_CYCLES;
                3'd7: lookup_period_cycles = PERIOD7_CYCLES;
                default: lookup_period_cycles = PERIOD0_CYCLES;
            endcase
        end
    endfunction

    function automatic logic [31:0] compensated_wait_cycles(
        input logic [31:0] period_cycles,
        input logic [31:0] completed_pass_cycles
    );
        begin
            if (period_cycles > completed_pass_cycles) begin
                compensated_wait_cycles = period_cycles - completed_pass_cycles;
            end else begin
                // Minimum one idle cycle prevents immediate combinational retriggering
                // and represents continuous scrubbing when the requested period is
                // shorter than the pass duration.
                compensated_wait_cycles = 32'd1;
            end
        end
    endfunction

    always_comb begin
        stale_control_flag = (control_age_cycles >= MAX_CONTROL_AGE_CYCLES);
        safe_mode_active = stale_control_flag;

        if (safe_mode_active) begin
            applied_period_index = SAFE_PERIOD_INDEX[2:0];
        end else begin
            applied_period_index = commanded_period_index;
        end

        selected_period_cycles = lookup_period_cycles(applied_period_index);
    end

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state <= S_WAIT;
            commanded_period_index <= SAFE_PERIOD_INDEX[2:0];
            control_age_cycles <= MAX_CONTROL_AGE_CYCLES[31:0];
            wait_counter <= 32'd0;
            pass_cycle_counter <= 32'd0;
            last_pass_cycles <= 32'd0;
            pass_start <= 1'b0;
            safe_mode_active_d <= 1'b1;
            safe_mode_entry_count <= 32'd1;
        end else begin
            pass_start <= 1'b0;

            // External control update.
            if (period_update_valid) begin
                commanded_period_index <= period_index;
                control_age_cycles <= 32'd0;
            end else if (control_age_cycles < MAX_CONTROL_AGE_CYCLES[31:0]) begin
                control_age_cycles <= control_age_cycles + 32'd1;
            end

            // Count entries into safe mode.
            safe_mode_active_d <= safe_mode_active;
            if (safe_mode_active && !safe_mode_active_d) begin
                safe_mode_entry_count <= safe_mode_entry_count + 32'd1;
            end

            case (state)
                S_WAIT: begin
                    pass_cycle_counter <= 32'd0;

                    if (wait_counter == 32'd0) begin
                        pass_start <= 1'b1;
                        pass_cycle_counter <= 32'd1;
                        state <= S_INPASS;
                    end else begin
                        wait_counter <= wait_counter - 32'd1;
                    end
                end

                S_INPASS: begin
                    if (pass_done) begin
                        last_pass_cycles <= pass_cycle_counter + 32'd1;
                        wait_counter <= compensated_wait_cycles(
                            selected_period_cycles,
                            pass_cycle_counter + 32'd1
                        );
                        state <= S_WAIT;
                    end else begin
                        pass_cycle_counter <= pass_cycle_counter + 32'd1;
                    end
                end

                default: begin
                    state <= S_WAIT;
                    wait_counter <= 32'd0;
                end
            endcase
        end
    end

endmodule
