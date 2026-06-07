# Chapter 4 dissertation-geometry synthesis summary

This report complements the default small-test-geometry synthesis summary.
The selected RTL tops are parameterized with the dissertation memory geometry
`ADDR_WIDTH=21`, `DEPTH=1935832`, and `75497448` protected SEC-DED bits.

Important limitation: this is still a Yosys synthesis estimate, not Vivado
place-and-route timing closure and not an Fmax claim.

The diagnostic persistent-DUE state is bounded by
`DUE_TRACKER_ENTRIES=16` and is not a full depth-wide bitmap.

| Flow | Run | Top | Cells | FF estimate | LUT estimate | MUX estimate | Wire bits |
|---|---|---|---:|---:|---:|---:|---:|
| generic_yosys | period_scheduler_ch3_period_table | period_scheduler | 1528 | 167 | 0 | 308 | 1960 |
| generic_yosys | scrub_pass_engine_ch4_geometry | scrub_pass_engine | 1702 | 188 | 0 | 551 | 6500 |
| generic_yosys | diagnostic_supervisor_ch4_geometry | diagnostic_supervisor | 4775 | 548 | 0 | 2444 | 5339 |
| generic_yosys | adaptive_scrub_controller_ch4_geometry | adaptive_scrub_controller | 5743 | 903 | 0 | 1070 | 12013 |
| generic_yosys | measured_error_scrub_controller_ch4_geometry | measured_error_scrub_controller | 7046 | 1007 | 0 | 1610 | 14850 |
| xilinx_xc7 | period_scheduler_ch3_period_table | period_scheduler | 731 | 167 | 169 | 10 | 1257 |
| xilinx_xc7 | scrub_pass_engine_ch4_geometry | scrub_pass_engine | 943 | 188 | 188 | 34 | 1910 |
| xilinx_xc7 | diagnostic_supervisor_ch4_geometry | diagnostic_supervisor | 2253 | 548 | 659 | 195 | 2999 |
| xilinx_xc7 | adaptive_scrub_controller_ch4_geometry | adaptive_scrub_controller | 3636 | 903 | 850 | 145 | 6273 |
| xilinx_xc7 | measured_error_scrub_controller_ch4_geometry | measured_error_scrub_controller | 4113 | 1007 | 979 | 190 | 7837 |

## Interpretation

- These rows use the Chapter 4 memory address width and codeword count.
- The protected memory array itself is external to these controllers; the
  synthesis estimate covers the controller/address/ECC/diagnostic logic.
- The bounded DUE tracker prevents diagnostic state from scaling as one
  flip-flop per protected codeword.
- Vivado implementation can later provide device-specific utilization,
  routing, and timing closure evidence.
