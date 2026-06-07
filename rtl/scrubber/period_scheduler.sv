// Period scheduler for the adaptive scrub controller.
//
// This block is the hardware endpoint of the Chapter 3 schedule compiler.
// It does not compute the radiation/risk model. It consumes an external
// period_index and launches full scrub passes so that the interval between two
// checks of the same codeword tracks the selected full-pass period.
//
// Time representation:
//   - clk is the implementation clock.
//   - time_tick is a coarse timebase tick.
//   - PERIOD*_CYCLES are legacy parameter names kept for compatibility;
//     they are interpreted as PERIOD*_TICKS by the scheduler.
//   - RTL replay may compress time by asserting time_tick every clk.
//   - A deployment may drive time_tick from a 1 Hz or other configured timer.
//
// If external updates become stale, the scheduler falls back to a conservative
// safe period index.

`timescale 1ns/1ps

module period_scheduler #(
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
    input  logic                            time_tick,

    input  logic                            period_update_valid,
    input  logic [PERIOD_INDEX_WIDTH-1:0]   period_index,

    input  logic                            pass_done,

    output logic                            pass_start,
    output logic [PERIOD_INDEX_WIDTH-1:0]   applied_period_index,
    output logic [31:0]                     selected_period_cycles, // legacy name: selected period in time ticks
    output logic                            safe_mode_active,
    output logic                            stale_control_flag,
    output logic [31:0]                     last_pass_cycles,
    output logic [31:0]                     safe_mode_entry_count
);

    typedef enum logic [0:0] {
        S_WAIT   = 1'b0,
        S_INPASS = 1'b1
    } state_t;

    state_t state;

    logic [PERIOD_INDEX_WIDTH-1:0] commanded_period_index;
    logic [31:0]                   control_age_cycles; // legacy name: control age in time ticks
    logic [31:0]                   wait_counter;        // wait time in time ticks
    logic [31:0]                   pass_cycle_counter;  // legacy name: pass duration in time ticks
    logic                          safe_mode_active_d;

    function automatic logic [PERIOD_INDEX_WIDTH-1:0] clamp_period_index(
        input logic [PERIOD_INDEX_WIDTH-1:0] index
    );
        begin
            case (index)
                PERIOD_INDEX_WIDTH'(0),
                PERIOD_INDEX_WIDTH'(1),
                PERIOD_INDEX_WIDTH'(2),
                PERIOD_INDEX_WIDTH'(3),
                PERIOD_INDEX_WIDTH'(4),
                PERIOD_INDEX_WIDTH'(5),
                PERIOD_INDEX_WIDTH'(6),
                PERIOD_INDEX_WIDTH'(7),
                PERIOD_INDEX_WIDTH'(8),
                PERIOD_INDEX_WIDTH'(9),
                PERIOD_INDEX_WIDTH'(10),
                PERIOD_INDEX_WIDTH'(11): clamp_period_index = index;
                default: clamp_period_index = PERIOD_INDEX_WIDTH'(SAFE_PERIOD_INDEX);
            endcase
        end
    endfunction

    function automatic logic [31:0] lookup_period_cycles(
        input logic [PERIOD_INDEX_WIDTH-1:0] index
    );
        begin
            case (clamp_period_index(index))
                PERIOD_INDEX_WIDTH'(0):  lookup_period_cycles = PERIOD0_CYCLES;
                PERIOD_INDEX_WIDTH'(1):  lookup_period_cycles = PERIOD1_CYCLES;
                PERIOD_INDEX_WIDTH'(2):  lookup_period_cycles = PERIOD2_CYCLES;
                PERIOD_INDEX_WIDTH'(3):  lookup_period_cycles = PERIOD3_CYCLES;
                PERIOD_INDEX_WIDTH'(4):  lookup_period_cycles = PERIOD4_CYCLES;
                PERIOD_INDEX_WIDTH'(5):  lookup_period_cycles = PERIOD5_CYCLES;
                PERIOD_INDEX_WIDTH'(6):  lookup_period_cycles = PERIOD6_CYCLES;
                PERIOD_INDEX_WIDTH'(7):  lookup_period_cycles = PERIOD7_CYCLES;
                PERIOD_INDEX_WIDTH'(8):  lookup_period_cycles = PERIOD8_CYCLES;
                PERIOD_INDEX_WIDTH'(9):  lookup_period_cycles = PERIOD9_CYCLES;
                PERIOD_INDEX_WIDTH'(10): lookup_period_cycles = PERIOD10_CYCLES;
                PERIOD_INDEX_WIDTH'(11): lookup_period_cycles = PERIOD11_CYCLES;
                default:                 lookup_period_cycles = PERIOD0_CYCLES;
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
            applied_period_index = clamp_period_index(PERIOD_INDEX_WIDTH'(SAFE_PERIOD_INDEX));
        end else begin
            applied_period_index = clamp_period_index(commanded_period_index);
        end

        selected_period_cycles = lookup_period_cycles(applied_period_index);
    end

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state <= S_WAIT;
            commanded_period_index <= clamp_period_index(PERIOD_INDEX_WIDTH'(SAFE_PERIOD_INDEX));
            control_age_cycles <= MAX_CONTROL_AGE_CYCLES[31:0];
            wait_counter <= 32'd0;
            pass_cycle_counter <= 32'd0;
            last_pass_cycles <= 32'd0;
            pass_start <= 1'b0;
            safe_mode_active_d <= 1'b1;
            safe_mode_entry_count <= 32'd1;
        end else begin
            pass_start <= 1'b0;

            // External control update. Staleness is measured in coarse
            // timebase ticks, not raw implementation-clock cycles.
            if (period_update_valid) begin
                commanded_period_index <= clamp_period_index(period_index);
                control_age_cycles <= 32'd0;
            end else if (time_tick && control_age_cycles < MAX_CONTROL_AGE_CYCLES[31:0]) begin
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
                        // Preserve the legacy compressed-time accounting:
                        // a launched pass consumes at least one scheduler tick.
                        pass_cycle_counter <= 32'd1;
                        state <= S_INPASS;
                    end else if (time_tick) begin
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
                    end else if (time_tick) begin
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
