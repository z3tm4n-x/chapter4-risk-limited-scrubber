// Sequential full-pass SEC-DED scrub engine.
//
// This block performs one complete pass over the protected memory region:
//   read codeword -> SEC-DED decode -> write back if single-bit corrected
//
// It does not schedule passes by itself. A period scheduler provides pass_start.
// The engine reports pass_done when the complete address range has been scanned.

`timescale 1ns/1ps

module scrub_pass_engine #(
    parameter int ADDR_WIDTH = 4,
    parameter int DEPTH = 16
) (
    input  logic                   clk,
    input  logic                   reset_n,

    input  logic                   pass_start,
    output logic                   pass_active,
    output logic                   pass_done,

    output logic                   mem_read_en,
    output logic                   mem_write_en,
    output logic [ADDR_WIDTH-1:0]  mem_addr,
    input  logic [38:0]            mem_read_data,
    output logic [38:0]            mem_write_data,

    output logic                   corrected_pulse,
    output logic                   detected_uncorrectable_pulse,

    output logic [31:0]            pass_count,
    output logic [31:0]            read_count,
    output logic [31:0]            write_count,
    output logic [31:0]            corrected_count,
    output logic [31:0]            detected_uncorrectable_count
);

    typedef enum logic [2:0] {
        S_IDLE    = 3'd0,
        S_READ    = 3'd1,
        S_DECODE  = 3'd2,
        S_WRITE   = 3'd3,
        S_ADVANCE = 3'd4
    } state_t;

    state_t state;

    logic [ADDR_WIDTH-1:0] current_addr;

    logic [38:0] decoded_corrected_codeword;
    logic [31:0] decoded_data;
    logic        decoded_no_error;
    logic        decoded_corrected;
    logic        decoded_uncorrectable;
    logic [5:0]  decoded_syndrome;
    logic [5:0]  decoded_corrected_position;

    secded_32_39_decoder decoder (
        .codeword_in(mem_read_data),
        .codeword_corrected(decoded_corrected_codeword),
        .data_out(decoded_data),
        .no_error(decoded_no_error),
        .corrected(decoded_corrected),
        .detected_uncorrectable(decoded_uncorrectable),
        .syndrome(decoded_syndrome),
        .corrected_position(decoded_corrected_position)
    );

    always_comb begin
        mem_addr = current_addr;
        mem_read_en = (state == S_READ);
        mem_write_en = (state == S_WRITE);
        mem_write_data = decoded_corrected_codeword;
    end

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state <= S_IDLE;
            current_addr <= '0;
            pass_active <= 1'b0;
            pass_done <= 1'b0;
            corrected_pulse <= 1'b0;
            detected_uncorrectable_pulse <= 1'b0;

            pass_count <= 32'd0;
            read_count <= 32'd0;
            write_count <= 32'd0;
            corrected_count <= 32'd0;
            detected_uncorrectable_count <= 32'd0;
        end else begin
            pass_done <= 1'b0;
            corrected_pulse <= 1'b0;
            detected_uncorrectable_pulse <= 1'b0;

            case (state)
                S_IDLE: begin
                    pass_active <= 1'b0;

                    if (pass_start) begin
                        current_addr <= '0;
                        pass_active <= 1'b1;
                        pass_count <= pass_count + 32'd1;
                        state <= S_READ;
                    end
                end

                S_READ: begin
                    read_count <= read_count + 32'd1;
                    state <= S_DECODE;
                end

                S_DECODE: begin
                    if (decoded_corrected) begin
                        corrected_pulse <= 1'b1;
                        corrected_count <= corrected_count + 32'd1;
                        state <= S_WRITE;
                    end else begin
                        if (decoded_uncorrectable) begin
                            detected_uncorrectable_pulse <= 1'b1;
                            detected_uncorrectable_count <= detected_uncorrectable_count + 32'd1;
                        end

                        state <= S_ADVANCE;
                    end
                end

                S_WRITE: begin
                    write_count <= write_count + 32'd1;
                    state <= S_ADVANCE;
                end

                S_ADVANCE: begin
                    if (current_addr == DEPTH[ADDR_WIDTH-1:0] - 1'b1) begin
                        pass_done <= 1'b1;
                        pass_active <= 1'b0;
                        state <= S_IDLE;
                    end else begin
                        current_addr <= current_addr + 1'b1;
                        state <= S_READ;
                    end
                end

                default: begin
                    state <= S_IDLE;
                    pass_active <= 1'b0;
                end
            endcase
        end
    end

endmodule
