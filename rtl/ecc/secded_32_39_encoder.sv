// SEC-DED encoder for 32 data bits into a 39-bit codeword.
//
// Logical positions are 1-based:
//   parity positions: 1, 2, 4, 8, 16, 32
//   data positions: all other positions from 1..38
//   overall parity: position 39
//
// codeword[0] corresponds to logical position 1.
// codeword[38] corresponds to logical position 39.

`timescale 1ns/1ps

module secded_32_39_encoder (
    input  logic [31:0] data_in,
    output logic [38:0] codeword_out
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
    integer data_index;
    integer parity_index;
    logic parity_value;
    logic [38:0] temp_codeword;

    always_comb begin
        temp_codeword = '0;
        data_index = 0;

        // Place data bits into non-parity positions 1..38.
        for (pos = 1; pos <= 38; pos = pos + 1) begin
            if (!is_hamming_parity_position(pos)) begin
                temp_codeword[pos - 1] = data_in[data_index];
                data_index = data_index + 1;
            end
        end

        // Compute six Hamming parity bits.
        for (parity_index = 0; parity_index < 6; parity_index = parity_index + 1) begin
            parity_value = 1'b0;

            for (pos = 1; pos <= 38; pos = pos + 1) begin
                if ((pos & (1 << parity_index)) != 0) begin
                    parity_value = parity_value ^ temp_codeword[pos - 1];
                end
            end

            temp_codeword[(1 << parity_index) - 1] = parity_value;
        end

        // Overall even parity over positions 1..39.
        temp_codeword[38] = ^temp_codeword[37:0];

        codeword_out = temp_codeword;
    end

endmodule
