// SEC-DED decoder/corrector for a 39-bit codeword carrying 32 data bits.
//
// Guarantees:
//   - no-error codeword is passed through;
//   - every single-bit error in positions 1..39 is corrected;
//   - every double-bit error is detected as uncorrectable.
//
// Important dissertation boundary:
//   Three or more corrupted bits are outside the guaranteed correction capability.
//   They may be detected as uncorrectable or may become SDC depending on the
//   exact error pattern. Full SDC accounting belongs to the verification audit,
//   not to the online SEC-DED decoder output.

`timescale 1ns/1ps

module secded_32_39_decoder (
    input  logic [38:0] codeword_in,
    output logic [38:0] codeword_corrected,
    output logic [31:0] data_out,
    output logic        no_error,
    output logic        corrected,
    output logic        detected_uncorrectable,
    output logic [5:0]  syndrome,
    output logic [5:0]  corrected_position
);

    function automatic bit is_hamming_parity_position(input int position);
        begin
            is_hamming_parity_position =
                (position == 1)  ||
                (position == 2)  ||
                (position == 4)  ||
                (position == 8)  ||
                (position == 16) ||
                (position == 32);
        end
    endfunction

    integer pos;
    integer parity_index;
    integer data_index;
    logic overall_parity_error;
    logic parity_value;
    logic [38:0] temp_corrected;

    always_comb begin
        syndrome = 6'd0;

        // Recompute Hamming syndrome over positions 1..38.
        for (parity_index = 0; parity_index < 6; parity_index = parity_index + 1) begin
            parity_value = 1'b0;

            for (pos = 1; pos <= 38; pos = pos + 1) begin
                if ((pos & (1 << parity_index)) != 0) begin
                    parity_value = parity_value ^ codeword_in[pos - 1];
                end
            end

            syndrome[parity_index] = parity_value;
        end

        overall_parity_error = ^codeword_in;

        temp_corrected = codeword_in;
        no_error = 1'b0;
        corrected = 1'b0;
        detected_uncorrectable = 1'b0;
        corrected_position = 6'd0;

        if ((syndrome == 6'd0) && !overall_parity_error) begin
            // No error.
            no_error = 1'b1;
        end else if ((syndrome != 6'd0) && overall_parity_error) begin
            // Single-bit error in positions 1..38, if syndrome maps to a real
            // protected bit. Other odd-weight patterns are outside guarantee.
            if (syndrome <= 6'd38) begin
                temp_corrected[syndrome - 1] = ~temp_corrected[syndrome - 1];
                corrected = 1'b1;
                corrected_position = syndrome;
            end else begin
                detected_uncorrectable = 1'b1;
            end
        end else if ((syndrome == 6'd0) && overall_parity_error) begin
            // Single-bit error in the overall parity bit, position 39.
            temp_corrected[38] = ~temp_corrected[38];
            corrected = 1'b1;
            corrected_position = 6'd39;
        end else begin
            // syndrome != 0 and overall parity is even: detected double-bit error.
            detected_uncorrectable = 1'b1;
        end

        codeword_corrected = temp_corrected;

        data_index = 0;
        data_out = '0;

        for (pos = 1; pos <= 38; pos = pos + 1) begin
            if (!is_hamming_parity_position(pos)) begin
                data_out[data_index] = temp_corrected[pos - 1];
                data_index = data_index + 1;
            end
        end
    end

endmodule
