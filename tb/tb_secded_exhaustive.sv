// Exhaustive SEC-DED checks over bit positions for a representative data set.
//
// This test is intentionally stronger than a simple smoke test:
//   - checks no-error decode;
//   - checks all 39 single-bit corruptions for each data pattern;
//   - checks all C(39,2) double-bit corruptions for each data pattern;
//   - samples selected triple-bit corruptions and verifies that the testbench
//     can distinguish detected DUE from SDC by using a golden data reference.

`timescale 1ns/1ps

module tb_secded_exhaustive;

    logic [31:0] data_in;
    logic [38:0] codeword;
    logic [38:0] corrupted;
    logic [38:0] corrected_codeword;
    logic [31:0] data_out;
    logic        no_error;
    logic        corrected;
    logic        detected_uncorrectable;
    logic [5:0]  syndrome;
    logic [5:0]  corrected_position;

    integer pattern_index;
    integer bit_i;
    integer bit_j;
    integer bit_k;

    integer no_error_checks;
    integer single_checks;
    integer double_checks;
    integer triple_samples;
    integer triple_detected_due;
    integer triple_sdc;
    integer failures;

    logic [31:0] patterns [0:7];

    secded_32_39_encoder encoder (
        .data_in(data_in),
        .codeword_out(codeword)
    );

    secded_32_39_decoder decoder (
        .codeword_in(corrupted),
        .codeword_corrected(corrected_codeword),
        .data_out(data_out),
        .no_error(no_error),
        .corrected(corrected),
        .detected_uncorrectable(detected_uncorrectable),
        .syndrome(syndrome),
        .corrected_position(corrected_position)
    );

    task automatic check_condition(input bit condition, input string message);
        begin
            if (!condition) begin
                $display("FAIL: %s", message);
                failures = failures + 1;
            end
        end
    endtask

    initial begin
        patterns[0] = 32'h0000_0000;
        patterns[1] = 32'hFFFF_FFFF;
        patterns[2] = 32'hA5A5_5A5A;
        patterns[3] = 32'h1234_5678;
        patterns[4] = 32'hDEAD_BEEF;
        patterns[5] = 32'h8000_0001;
        patterns[6] = 32'h0102_0408;
        patterns[7] = 32'h4000_0000;

        no_error_checks = 0;
        single_checks = 0;
        double_checks = 0;
        triple_samples = 0;
        triple_detected_due = 0;
        triple_sdc = 0;
        failures = 0;

        for (pattern_index = 0; pattern_index < 8; pattern_index = pattern_index + 1) begin
            data_in = patterns[pattern_index];
            #1;

            corrupted = codeword;
            #1;

            no_error_checks = no_error_checks + 1;
            check_condition(no_error, "no-error decode did not assert no_error");
            check_condition(!corrected, "no-error decode incorrectly asserted corrected");
            check_condition(!detected_uncorrectable, "no-error decode incorrectly asserted DUE");
            check_condition(data_out == data_in, "no-error decode changed data");

            // All single-bit errors must be corrected.
            for (bit_i = 0; bit_i < 39; bit_i = bit_i + 1) begin
                corrupted = codeword ^ (39'd1 << bit_i);
                #1;

                single_checks = single_checks + 1;

                check_condition(corrected, "single-bit error was not corrected");
                check_condition(!detected_uncorrectable, "single-bit error incorrectly marked DUE");
                check_condition(data_out == data_in, "single-bit correction produced wrong data");
                check_condition(corrected_codeword == codeword, "single-bit correction did not restore codeword");
                check_condition(corrected_position == (bit_i + 1), "single-bit corrected_position mismatch");
            end

            // All double-bit errors must be detected as uncorrectable.
            for (bit_i = 0; bit_i < 39; bit_i = bit_i + 1) begin
                for (bit_j = bit_i + 1; bit_j < 39; bit_j = bit_j + 1) begin
                    corrupted = codeword ^ (39'd1 << bit_i) ^ (39'd1 << bit_j);
                    #1;

                    double_checks = double_checks + 1;

                    check_condition(detected_uncorrectable, "double-bit error was not detected as DUE");
                    check_condition(!corrected, "double-bit error incorrectly asserted corrected");
                end
            end

            // Sample selected triple-bit errors. These are outside guarantee.
            // The test does not require online detection; it records whether the
            // outcome is detected DUE or SDC relative to the golden data.
            for (bit_i = 0; bit_i < 39; bit_i = bit_i + 13) begin
                bit_j = (bit_i + 5) % 39;
                bit_k = (bit_i + 17) % 39;

                corrupted = codeword ^ (39'd1 << bit_i) ^ (39'd1 << bit_j) ^ (39'd1 << bit_k);
                #1;

                triple_samples = triple_samples + 1;

                if (detected_uncorrectable) begin
                    triple_detected_due = triple_detected_due + 1;
                end else if (data_out != data_in) begin
                    triple_sdc = triple_sdc + 1;
                end
            end
        end

        $display("SECDED_EXHAUSTIVE_SUMMARY no_error=%0d single=%0d double=%0d triple_samples=%0d triple_detected_due=%0d triple_sdc=%0d failures=%0d",
                 no_error_checks,
                 single_checks,
                 double_checks,
                 triple_samples,
                 triple_detected_due,
                 triple_sdc,
                 failures);

        if (failures != 0) begin
            $fatal(1, "SECDED exhaustive test failed with %0d failures", failures);
        end

        check_condition(no_error_checks == 8, "unexpected no_error check count");
        check_condition(single_checks == 8 * 39, "unexpected single-bit check count");
        check_condition(double_checks == 8 * ((39 * 38) / 2), "unexpected double-bit check count");

        if (failures != 0) begin
            $fatal(1, "SECDED count checks failed with %0d failures", failures);
        end

        $display("SECDED_EXHAUSTIVE_PASS");
        $finish;
    end

endmodule
