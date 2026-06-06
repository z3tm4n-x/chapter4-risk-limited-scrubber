# RTL synthesis/resource summary

This report gives reproducible flattened Yosys resource estimates for the Chapter 4 RTL.

Important limitation: these are synthesis estimates only. They are not
place-and-route timing closure and do not establish Fmax.

| Flow | Top | Cells | FF estimate | LUT estimate | MUX estimate | Wire bits |
|---|---|---:|---:|---:|---:|---:|
| generic_yosys | secded_32_39_encoder | 117 | 0 | 0 | 0 | 321 |
| generic_yosys | secded_32_39_decoder | 879 | 0 | 0 | 516 | 5294 |
| generic_yosys | period_scheduler | 1442 | 167 | 0 | 233 | 1866 |
| generic_yosys | scrub_pass_engine | 1543 | 171 | 0 | 517 | 6273 |
| generic_yosys | diagnostic_supervisor | 1822 | 212 | 0 | 655 | 2243 |
| generic_yosys | adaptive_scrub_controller | 4291 | 550 | 0 | 900 | 10421 |
| generic_yosys | measured_error_period_estimator | 1302 | 104 | 0 | 540 | 2170 |
| generic_yosys | measured_error_scrub_controller | 5593 | 654 | 0 | 1440 | 13252 |
| xilinx_xc7 | secded_32_39_encoder | 104 | 0 | 32 | 1 | 248 |
| xilinx_xc7 | secded_32_39_decoder | 324 | 0 | 143 | 33 | 834 |
| xilinx_xc7 | period_scheduler | 720 | 167 | 162 | 3 | 1243 |
| xilinx_xc7 | scrub_pass_engine | 861 | 171 | 168 | 28 | 1720 |
| xilinx_xc7 | diagnostic_supervisor | 962 | 212 | 247 | 1 | 1401 |
| xilinx_xc7 | adaptive_scrub_controller | 2385 | 550 | 444 | 22 | 4612 |
| xilinx_xc7 | measured_error_period_estimator | 511 | 104 | 139 | 1 | 833 |
| xilinx_xc7 | measured_error_scrub_controller | 2853 | 654 | 603 | 29 | 6185 |

Interpretation:

- `secded_32_39_encoder` and `secded_32_39_decoder` represent the ECC datapath.
- `period_scheduler` is the hardware endpoint of the Chapter 3 period-index schedule.
- `scrub_pass_engine` performs the full sequential memory pass and correction writeback.
- `diagnostic_supervisor` implements hardware symptom flags for alert, DUE persistence, and out-of-envelope escalation.
- `adaptive_scrub_controller` is the external-period endpoint proposed for Chapter 4.
- `measured_error_period_estimator` and `measured_error_scrub_controller` represent the onboard fallback mode.
- The Xilinx XC7 flow reports LUT/FF-style estimates but still does not replace
  implementation, placement, routing, and timing analysis.
