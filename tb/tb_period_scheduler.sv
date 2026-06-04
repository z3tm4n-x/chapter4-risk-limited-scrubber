// Period scheduler verification.
//
// Checks:
//   - external period_index selects the expected table period;
//   - pass_start intervals include pass duration compensation;
//   - stale control activates safe conservative period;
//   - a fresh update exits safe mode.

`timescale 1ns/1ps

module tb_period_scheduler;

    logic clk;
    logic reset_n;

    logic period_update_valid;
    logic [2:0] period_index;
    logic pass_done;

    logic pass_start;
    logic [2:0] applied_period_index;
    logic [31:0] selected_period_cycles;
    logic safe_mode_active;
    logic stale_control_flag;
    logic [31:0] last_pass_cycles;
    logic [31:0] safe_mode_entry_count;

    integer cycle_counter;
    integer failures;
    integer first_start_cycle;
    integer second_start_cycle;
    integer measured_interval;

    localparam integer PASS_CYCLES = 7;

    logic fake_pass_active;
    integer fake_pass_remaining;

    period_scheduler #(
        .PERIOD0_CYCLES(10),
        .PERIOD1_CYCLES(20),
        .PERIOD2_CYCLES(50),
        .PERIOD3_CYCLES(100),
        .PERIOD4_CYCLES(200),
        .PERIOD5_CYCLES(500),
        .PERIOD6_CYCLES(1000),
        .PERIOD7_CYCLES(2000),
        .SAFE_PERIOD_INDEX(0),
        .MAX_CONTROL_AGE_CYCLES(200)
    ) dut (
        .clk(clk),
        .reset_n(reset_n),
        .period_update_valid(period_update_valid),
        .period_index(period_index),
        .pass_done(pass_done),
        .pass_start(pass_start),
        .applied_period_index(applied_period_index),
        .selected_period_cycles(selected_period_cycles),
        .safe_mode_active(safe_mode_active),
        .stale_control_flag(stale_control_flag),
        .last_pass_cycles(last_pass_cycles),
        .safe_mode_entry_count(safe_mode_entry_count)
    );

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            cycle_counter <= 0;
        end else begin
            cycle_counter <= cycle_counter + 1;
        end
    end

    // Fake pass engine: pass_done comes PASS_CYCLES after pass_start.
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            fake_pass_active <= 1'b0;
            fake_pass_remaining <= 0;
            pass_done <= 1'b0;
        end else begin
            pass_done <= 1'b0;

            if (pass_start && !fake_pass_active) begin
                fake_pass_active <= 1'b1;
                fake_pass_remaining <= PASS_CYCLES;
            end else if (fake_pass_active) begin
                if (fake_pass_remaining <= 1) begin
                    fake_pass_active <= 1'b0;
                    fake_pass_remaining <= 0;
                    pass_done <= 1'b1;
                end else begin
                    fake_pass_remaining <= fake_pass_remaining - 1;
                end
            end
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

    task automatic wait_for_pass_start(output integer start_cycle);
        begin
            @(posedge clk);
            while (!pass_start) begin
                @(posedge clk);
            end
            start_cycle = cycle_counter;
        end
    endtask

    initial begin
        failures = 0;
        period_update_valid = 1'b0;
        period_index = 3'd0;

        reset_n = 1'b0;
        repeat (5) @(posedge clk);
        reset_n = 1'b1;

        // Leave reset safe mode by providing a fresh period index.
        pulse_period_update(3'd2);
        repeat (2) @(posedge clk);

        check_condition(!safe_mode_active, "scheduler did not leave safe mode after fresh update");
        check_condition(applied_period_index == 3'd2, "applied index mismatch after update");
        check_condition(selected_period_cycles == 32'd50, "selected period mismatch for index 2");

        wait_for_pass_start(first_start_cycle);
        wait_for_pass_start(second_start_cycle);

        measured_interval = second_start_cycle - first_start_cycle;
        check_condition(measured_interval == 50, "pass_start interval does not match selected full-pass period");

        // Wait long enough for stale-control safe mode.
        repeat (210) @(posedge clk);

        check_condition(stale_control_flag, "stale_control_flag did not assert");
        check_condition(safe_mode_active, "safe_mode_active did not assert");
        check_condition(applied_period_index == 3'd0, "safe mode did not apply safe period index");
        check_condition(selected_period_cycles == 32'd10, "safe mode selected period mismatch");
        check_condition(safe_mode_entry_count >= 1, "safe mode entry count did not increment");

        // Fresh update exits safe mode and selects new period.
        pulse_period_update(3'd1);
        repeat (2) @(posedge clk);

        check_condition(!safe_mode_active, "scheduler did not exit safe mode after fresh update");
        check_condition(applied_period_index == 3'd1, "applied index mismatch after safe-mode recovery");
        check_condition(selected_period_cycles == 32'd20, "selected period mismatch for index 1");

        $display("PERIOD_SCHEDULER_SUMMARY measured_interval=%0d last_pass_cycles=%0d safe_entries=%0d failures=%0d",
                 measured_interval,
                 last_pass_cycles,
                 safe_mode_entry_count,
                 failures);

        if (failures != 0) begin
            $fatal(1, "period_scheduler test failed with %0d failures", failures);
        end

        $display("PERIOD_SCHEDULER_PASS");
        $finish;
    end

endmodule
