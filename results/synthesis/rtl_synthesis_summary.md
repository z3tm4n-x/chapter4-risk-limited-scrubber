# RTL synthesis/resource summary

This report gives reproducible Yosys resource estimates for the Chapter 4 RTL.

Important limitation: these are synthesis estimates only. They are not
place-and-route timing closure and do not establish Fmax.

| Flow | Top | Cells | FF estimate | LUT estimate | MUX estimate | Wire bits |
|---|---|---:|---:|---:|---:|---:|
| generic_yosys | secded_32_39_encoder | 0 | 0 | 0 | 0 | 0 |
| generic_yosys | secded_32_39_decoder | 0 | 0 | 0 | 0 | 0 |
| generic_yosys | period_scheduler | 0 | 0 | 0 | 0 | 0 |
| generic_yosys | scrub_pass_engine | 0 | 0 | 0 | 0 | 0 |
| generic_yosys | adaptive_scrub_controller | 0 | 0 | 0 | 0 | 0 |
| xilinx_xc7 | secded_32_39_encoder | 0 | 0 | 0 | 0 | 0 |
| xilinx_xc7 | secded_32_39_decoder | 0 | 0 | 0 | 0 | 0 |
| xilinx_xc7 | period_scheduler | 0 | 0 | 0 | 0 | 0 |
| xilinx_xc7 | scrub_pass_engine | 0 | 0 | 0 | 0 | 0 |
| xilinx_xc7 | adaptive_scrub_controller | 0 | 0 | 0 | 0 | 0 |

Interpretation:

- `secded_32_39_encoder` and `secded_32_39_decoder` represent the ECC datapath.
- `period_scheduler` is the hardware endpoint of the Chapter 3 period-index schedule.
- `scrub_pass_engine` performs the full sequential memory pass and correction writeback.
- `adaptive_scrub_controller` is the integrated controller proposed for Chapter 4.
- The Xilinx XC7 flow reports LUT/FF-style estimates but still does not replace
  implementation, placement, routing, and timing analysis.
