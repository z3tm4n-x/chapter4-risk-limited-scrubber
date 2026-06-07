// Integrated adaptive scrub controller verification.
//
// Scenario:
//   - initialize protected memory;
//   - inject one correctable single-bit error;
//   - inject one detected double-bit error;
//   - provide an external period index;
//   - verify that the top-level controller performs scrub passes, restores the
//     single-bit corruption, reports DUE, and enters/exits safe mode.

`timescale 1ns/1ps

module tb_adaptive_scrub_controller;

    localparam int ADDR_WIDTH = 3;
    localparam int DEPTH = 8;

    logic clk;
    logic reset_n;
    logic time_tick;

    logic period_update_valid;
    logic [2:0] period_index;

    logic mem_read_en;
    logic mem_write_en;
    logic [ADDR_WIDTH-1:0] mem_addr;
    logic [38:0] mem_read_data;
    logic [38:0] mem_write_data;

    logic pass_start;
    logic pass_active;
    logic pass_done;

    logic [2:0] applied_period_index;
    logic [31:0] selected_period_cycles;
    logic safe_mode_active;
    logic stale_control_flag;
    logic [31:0] last_pass_cycles;

    logic corrected_pulse;
    logic detected_uncorrectable_pulse;

    logic [31:0] pass_count;
    logic [31:0] read_count;
    logic [31:0] write_count;
    logic [31:0] corrected_count;
    logic [31:0] detected_uncorrectable_count;
    logic [31:0] safe_mode_entry_count;

    logic [38:0] memory [0:DEPTH-1];
    logic [38:0] golden_codeword [0:DEPTH-1];
    logic [31:0] golden_data [0:DEPTH-1];

    logic [31:0] encoder_data;
    logic [38:0] encoder_codeword;

    integer addr;
    integer failures;
    integer timeout_cycles;

    secded_32_39_encoder encoder (
        .data_in(encoder_data),
        .codeword_out(encoder_codeword)
    );

    adaptive_scrub_controller #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DEPTH(DEPTH),
        .PERIOD0_CYCLES(10),
        .PERIOD1_CYCLES(20),
        .PERIOD2_CYCLES(50),
        .PERIOD3_CYCLES(100),
        .PERIOD4_CYCLES(200),
        .PERIOD5_CYCLES(500),
        .PERIOD6_CYCLES(1000),
        .PERIOD7_CYCLES(2000),
        .SAFE_PERIOD_INDEX(0),
        .MAX_CONTROL_AGE_CYCLES(80)
    ) dut (
        .clk(clk),
        .reset_n(reset_n),
        .time_tick(time_tick),
        .period_update_valid(period_update_valid),
        .period_index(period_index),
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
        .safe_mode_entry_count(safe_mode_entry_count)
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

    task automatic pulse_period_update(input logic [2:0] index);
        begin
            @(posedge clk);
            period_index <= index;
            period_update_valid <= 1'b1;
            @(posedge clk);
            period_update_valid <= 1'b0;
        end
    endtask

    initial begin
        failures = 0;
        period_update_valid = 1'b0;
        period_index = 3'd0;

        reset_n = 1'b0;
        time_tick = 1'b1;

        // Initialize memory while reset is asserted.
        for (addr = 0; addr < DEPTH; addr = addr + 1) begin
            encoder_data = 32'h4000_0000 + addr[31:0];
            #1;
            golden_data[addr] = encoder_data;
            golden_codeword[addr] = encoder_codeword;
            memory[addr] = encoder_codeword;
        end

        // Inject one correctable single-bit error and one detected DUE.
        memory[2] = memory[2] ^ (39'd1 << 7);
        memory[5] = memory[5] ^ (39'd1 << 3) ^ (39'd1 << 10);

        repeat (5) @(posedge clk);
        reset_n = 1'b1;

        // Provide an external Chapter-3 schedule index.
        pulse_period_update(3'd2);
        repeat (2) @(posedge clk);

        check_condition(!safe_mode_active, "controller did not leave safe mode after period update");
        check_condition(applied_period_index == 3'd2, "applied period index mismatch");
        check_condition(selected_period_cycles == 32'd50, "selected period mismatch");

        // Wait for a complete first pass that has encountered both injected
        // events. Corrected/DUE counters can update before the pass reaches the
        // final address, so read_count/pass_done are part of the condition.
        timeout_cycles = 0;
        while (((read_count < DEPTH) ||
                (corrected_count < 1) ||
                (detected_uncorrectable_count < 1) ||
                pass_active) &&
               (timeout_cycles < 400)) begin
            @(posedge clk);
            timeout_cycles = timeout_cycles + 1;
        end

        check_condition(pass_count >= 1, "pass_count did not increment");
        check_condition(read_count >= DEPTH, "not all words were read in a pass");
        check_condition(corrected_count >= 1, "corrected_count did not increment");
        check_condition(detected_uncorrectable_count >= 1, "detected_uncorrectable_count did not increment");
        check_condition(write_count >= 1, "write_count did not increment");
        check_condition(memory[2] == golden_codeword[2], "single-bit word was not restored");
        check_condition(memory[5] != golden_codeword[5], "double-bit DUE word was unexpectedly restored");

        // Let the external control become stale.
        repeat (100) @(posedge clk);

        check_condition(stale_control_flag, "stale_control_flag did not assert");
        check_condition(safe_mode_active, "safe_mode_active did not assert");
        check_condition(applied_period_index == 3'd0, "safe mode did not use safe index");
        check_condition(selected_period_cycles == 32'd10, "safe mode selected period mismatch");

        // Fresh update exits safe mode.
        pulse_period_update(3'd1);
        repeat (2) @(posedge clk);

        check_condition(!safe_mode_active, "controller did not exit safe mode after fresh update");
        check_condition(applied_period_index == 3'd1, "fresh update period index mismatch");
        check_condition(selected_period_cycles == 32'd20, "fresh update selected period mismatch");

        $display("ADAPTIVE_CONTROLLER_SUMMARY passes=%0d reads=%0d writes=%0d corrected=%0d detected_due=%0d safe_entries=%0d last_pass_cycles=%0d failures=%0d",
                 pass_count,
                 read_count,
                 write_count,
                 corrected_count,
                 detected_uncorrectable_count,
                 safe_mode_entry_count,
                 last_pass_cycles,
                 failures);

        if (failures != 0) begin
            $fatal(1, "adaptive controller integration test failed with %0d failures", failures);
        end

        $display("ADAPTIVE_CONTROLLER_PASS");
        $finish;
    end

endmodule
