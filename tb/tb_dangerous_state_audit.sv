// Dangerous-state audit verification.
//
// This test connects the integrated adaptive controller to a protected memory
// and injects:
//   - one correctable single-bit corruption;
//   - one detected double-bit DUE;
//   - one triple-bit corruption that is outside SEC-DED guarantee and becomes
//     SDC after false correction.
//
// The final audit uses a golden data reference. It is deliberately a
// verification-only mechanism, not an online hardware output.

`timescale 1ns/1ps

module tb_dangerous_state_audit;

    localparam int ADDR_WIDTH = 3;
    localparam int DEPTH = 8;

    logic clk;
    logic reset_n;

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

    logic [38:0] audit_codeword;
    logic [38:0] audit_corrected_codeword;
    logic [31:0] audit_data;
    logic audit_no_error;
    logic audit_corrected;
    logic audit_detected_uncorrectable;
    logic [5:0] audit_syndrome;
    logic [5:0] audit_corrected_position;

    integer addr;
    integer failures;
    integer final_uncorrectable_words;
    integer final_sdc_words;
    integer final_dangerous_words;

    secded_32_39_encoder encoder (
        .data_in(encoder_data),
        .codeword_out(encoder_codeword)
    );

    secded_32_39_decoder audit_decoder (
        .codeword_in(audit_codeword),
        .codeword_corrected(audit_corrected_codeword),
        .data_out(audit_data),
        .no_error(audit_no_error),
        .corrected(audit_corrected),
        .detected_uncorrectable(audit_detected_uncorrectable),
        .syndrome(audit_syndrome),
        .corrected_position(audit_corrected_position)
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
        .MAX_CONTROL_AGE_CYCLES(1000)
    ) dut (
        .clk(clk),
        .reset_n(reset_n),
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

        for (addr = 0; addr < DEPTH; addr = addr + 1) begin
            encoder_data = 32'h4000_0000 + addr[31:0];
            #1;
            golden_data[addr] = encoder_data;
            golden_codeword[addr] = encoder_codeword;
            memory[addr] = encoder_codeword;
        end

        // Address 1: single-bit correctable corruption.
        memory[1] = memory[1] ^ (39'd1 << 7);

        // Address 2: double-bit detected DUE.
        memory[2] = memory[2] ^ (39'd1 << 3) ^ (39'd1 << 10);

        // Address 3: triple-bit outside guarantee. Positions 5,6,7 produce
        // syndrome 4, so the decoder will falsely correct parity position 4.
        // The resulting codeword has data corruption that becomes final SDC.
        memory[3] = memory[3] ^ (39'd1 << 4) ^ (39'd1 << 5) ^ (39'd1 << 6);

        repeat (5) @(posedge clk);
        reset_n = 1'b1;

        pulse_period_update(3'd2);

        // Run several full passes. The single-bit word should be repaired.
        // The DUE word remains persistent. The triple-bit word may be falsely
        // corrected into a silent data corruption relative to golden_data.
        repeat (220) @(posedge clk);

        final_uncorrectable_words = 0;
        final_sdc_words = 0;

        for (addr = 0; addr < DEPTH; addr = addr + 1) begin
            audit_codeword = memory[addr];
            #1;

            if (audit_detected_uncorrectable) begin
                final_uncorrectable_words = final_uncorrectable_words + 1;
            end else if (audit_data != golden_data[addr]) begin
                final_sdc_words = final_sdc_words + 1;
            end
        end

        final_dangerous_words = final_uncorrectable_words + final_sdc_words;

        check_condition(memory[1] == golden_codeword[1], "single-bit word was not restored");
        check_condition(final_uncorrectable_words == 1, "expected exactly one final uncorrectable word");
        check_condition(final_sdc_words == 1, "expected exactly one final SDC word");
        check_condition(final_dangerous_words == 2, "expected exactly two final dangerous words");
        check_condition(detected_uncorrectable_count >= 1, "detected DUE counter did not increment");
        check_condition(corrected_count >= 2, "corrected counter did not include single and false correction cases");

        $display("DANGEROUS_AUDIT_SUMMARY passes=%0d reads=%0d writes=%0d corrected_events=%0d detected_due_events=%0d final_uncorrectable_words=%0d final_sdc_words=%0d final_dangerous_words=%0d failures=%0d",
                 pass_count,
                 read_count,
                 write_count,
                 corrected_count,
                 detected_uncorrectable_count,
                 final_uncorrectable_words,
                 final_sdc_words,
                 final_dangerous_words,
                 failures);

        if (failures != 0) begin
            $fatal(1, "dangerous-state audit test failed with %0d failures", failures);
        end

        $display("DANGEROUS_AUDIT_PASS");
        $finish;
    end

endmodule
