// Full-pass scrub engine verification.
//
// Scenario:
//   - initialize protected memory with valid SEC-DED codewords;
//   - inject one single-bit error into one word;
//   - inject one double-bit error into another word;
//   - run one full pass;
//   - verify single-bit writeback, detected DUE accounting, and pass counters.

`timescale 1ns/1ps

module tb_scrub_pass_engine;

    localparam int ADDR_WIDTH = 3;
    localparam int DEPTH = 8;

    logic clk;
    logic reset_n;

    logic pass_start;
    logic pass_active;
    logic pass_done;

    logic mem_read_en;
    logic mem_write_en;
    logic [ADDR_WIDTH-1:0] mem_addr;
    logic [38:0] mem_read_data;
    logic [38:0] mem_write_data;

    logic corrected_pulse;
    logic detected_uncorrectable_pulse;

    logic [31:0] pass_count;
    logic [31:0] read_count;
    logic [31:0] write_count;
    logic [31:0] corrected_count;
    logic [31:0] detected_uncorrectable_count;

    logic [38:0] memory [0:DEPTH-1];
    logic [38:0] golden_codeword [0:DEPTH-1];
    logic [31:0] golden_data [0:DEPTH-1];

    logic [31:0] encoder_data;
    logic [38:0] encoder_codeword;

    integer addr;
    integer failures;
    integer wait_cycles;

    secded_32_39_encoder encoder (
        .data_in(encoder_data),
        .codeword_out(encoder_codeword)
    );

    scrub_pass_engine #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DEPTH(DEPTH)
    ) dut (
        .clk(clk),
        .reset_n(reset_n),
        .pass_start(pass_start),
        .pass_active(pass_active),
        .pass_done(pass_done),
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

    task automatic pulse_pass_start();
        begin
            @(posedge clk);
            pass_start <= 1'b1;
            @(posedge clk);
            pass_start <= 1'b0;
        end
    endtask

    initial begin
        failures = 0;
        pass_start = 1'b0;

        reset_n = 1'b0;
        repeat (4) @(posedge clk);
        reset_n = 1'b1;

        // Initialize protected memory.
        for (addr = 0; addr < DEPTH; addr = addr + 1) begin
            encoder_data = 32'h4000_0000 + addr[31:0];
            #1;
            golden_data[addr] = encoder_data;
            golden_codeword[addr] = encoder_codeword;
            memory[addr] = encoder_codeword;
        end

        // Inject one correctable single-bit error at address 2.
        memory[2] = memory[2] ^ (39'd1 << 7);

        // Inject one detected uncorrectable double-bit error at address 5.
        memory[5] = memory[5] ^ (39'd1 << 3) ^ (39'd1 << 10);

        pulse_pass_start();

        wait_cycles = 0;
        while (!pass_done && wait_cycles < 200) begin
            @(posedge clk);
            wait_cycles = wait_cycles + 1;
        end

        check_condition(pass_done, "pass_done did not assert");
        @(posedge clk);

        check_condition(pass_count == 32'd1, "pass_count mismatch");
        check_condition(read_count == DEPTH, "read_count mismatch");
        check_condition(write_count == 32'd1, "write_count mismatch");
        check_condition(corrected_count == 32'd1, "corrected_count mismatch");
        check_condition(detected_uncorrectable_count == 32'd1, "detected_uncorrectable_count mismatch");

        check_condition(memory[2] == golden_codeword[2], "single-bit corrupted word was not restored");
        check_condition(memory[5] != golden_codeword[5], "double-bit DUE word was unexpectedly restored");

        for (addr = 0; addr < DEPTH; addr = addr + 1) begin
            if ((addr != 2) && (addr != 5)) begin
                check_condition(memory[addr] == golden_codeword[addr], "uncorrupted word changed during scrub pass");
            end
        end

        $display("SCRUB_PASS_ENGINE_SUMMARY depth=%0d pass_count=%0d reads=%0d writes=%0d corrected=%0d detected_due=%0d wait_cycles=%0d failures=%0d",
                 DEPTH,
                 pass_count,
                 read_count,
                 write_count,
                 corrected_count,
                 detected_uncorrectable_count,
                 wait_cycles,
                 failures);

        if (failures != 0) begin
            $fatal(1, "scrub_pass_engine test failed with %0d failures", failures);
        end

        $display("SCRUB_PASS_ENGINE_PASS");
        $finish;
    end

endmodule
