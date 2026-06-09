# Vivado out-of-context implementation report

This report implements selected Chapter 4 RTL tops on a commercial
AMD/Xilinx FPGA in out-of-context mode.

It is a device-specific implementation/timing demonstrator. It is not a
claim of radiation-qualified deployment and does not replace a final
platform-specific FPGA or ASIC implementation flow.

## Configuration

- FPGA part: `xc7a200tfbg484-2`
- Address width: `21`
- Codeword count: `1935832`
- Protected SEC-DED bits: `75497448`
- Bounded DUE tracker entries: `16`
- Memory service-rate assumption: `100000000` words/s
- Tau-min target: `1.0` s

The pass-time estimate uses:

`pass_time = pass_cycles / min(Fmax_core, memory_service_rate)`

with `pass_cycles = 1935836`.

## Highest passing frequency per top

| Top | Highest passing MHz | WNS, ns | LUT | FF | BRAM | DSP | Power, W | pass time, s | tau-min margin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| period_scheduler | 200.000000 | 0.419 | 196 | 148 | 0 | 0 | 0.126 | 0.01935836 | 51.6572684876 |
| scrub_pass_engine | 300.030003 | 0.445 | 119 | 188 | 0 | 0 | 0.134 | 0.01935836 | 51.6572684876 |
| adaptive_scrub_controller | 133.333333 | 0.837 | 533 | 884 | 0 | 0 | 0.142 | 0.01935836 | 51.6572684876 |
| measured_error_scrub_controller | 133.333333 | 0.533 | 604 | 957 | 0 | 0 | 0.145 | 0.01935836 | 51.6572684876 |

## Sweep detail

| Top | Target MHz | Period, ns | Timing met | WNS, ns | LUT | FF | BRAM | DSP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| period_scheduler | 100.000000 | 10.000000 | true | 4.600 | 195 | 148 | 0 | 0 |
| period_scheduler | 133.333333 | 7.500000 | true | 2.366 | 195 | 148 | 0 | 0 |
| period_scheduler | 200.000000 | 5.000000 | true | 0.419 | 196 | 148 | 0 | 0 |
| period_scheduler | 250.000000 | 4.000000 | false | -0.273 | 199 | 148 | 0 | 0 |
| period_scheduler | 300.030003 | 3.333000 | false | -0.963 | 199 | 148 | 0 | 0 |
| scrub_pass_engine | 100.000000 | 10.000000 | true | 5.367 | 116 | 188 | 0 | 0 |
| scrub_pass_engine | 133.333333 | 7.500000 | true | 3.165 | 116 | 188 | 0 | 0 |
| scrub_pass_engine | 200.000000 | 5.000000 | true | 1.011 | 116 | 188 | 0 | 0 |
| scrub_pass_engine | 250.000000 | 4.000000 | true | 0.749 | 117 | 188 | 0 | 0 |
| scrub_pass_engine | 300.030003 | 3.333000 | true | 0.445 | 119 | 188 | 0 | 0 |
| adaptive_scrub_controller | 100.000000 | 10.000000 | true | 3.049 | 534 | 884 | 0 | 0 |
| adaptive_scrub_controller | 133.333333 | 7.500000 | true | 0.837 | 533 | 884 | 0 | 0 |
| adaptive_scrub_controller | 200.000000 | 5.000000 | false | -0.578 | 551 | 884 | 0 | 0 |
| adaptive_scrub_controller | 250.000000 | 4.000000 | false | -1.697 | 565 | 884 | 0 | 0 |
| adaptive_scrub_controller | 300.030003 | 3.333000 | false | -2.508 | 567 | 884 | 0 | 0 |
| measured_error_scrub_controller | 100.000000 | 10.000000 | true | 2.760 | 603 | 957 | 0 | 0 |
| measured_error_scrub_controller | 133.333333 | 7.500000 | true | 0.533 | 604 | 957 | 0 | 0 |
| measured_error_scrub_controller | 200.000000 | 5.000000 | false | -0.523 | 627 | 957 | 0 | 0 |
| measured_error_scrub_controller | 250.000000 | 4.000000 | false | -1.769 | 638 | 957 | 0 | 0 |
| measured_error_scrub_controller | 300.030003 | 3.333000 | false | -2.553 | 639 | 957 | 0 | 0 |

## Interpretation

- Out-of-context mode is used because the scrub-control core connects to
  an external memory subsystem and does not require package pin assignment
  for this core-level timing check.
- Timing closure here demonstrates the commercial-FPGA implementation
  feasibility of the core at the reported clock constraints.
- The protected memory array itself is external to these controller tops.
- Radiation-qualified deployment would require migration to the selected
  qualified platform and its tool flow.
