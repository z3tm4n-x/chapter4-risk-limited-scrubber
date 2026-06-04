# Chapter 4 evidence pack

This report aggregates the reproducible artifacts for the Chapter 4
hardware implementation of the risk-limited adaptive SEC-DED scrubber.

The controller is treated as the hardware endpoint of the Chapter 3
schedule compiler. It consumes an external `period_index` and does not
compute the radiation-risk model inside RTL.


## Claim matrix

| Claim | Evidence artifact |
|---|---|
| Chapter 2 feasibility handoff distinguishes instant-risk, bandwidth-limited, and selectable regions | `results/feasibility/feasibility_summary.md` |
| Chapter 3 schedule compiler emits an implementable exact-risk period-index schedule | `results/schedules/schedule_summary.md` |
| SEC-DED datapath corrects all single-bit errors and detects all double-bit errors in the tested 39-bit codeword space | `results/rtl_replay/secded_exhaustive_report.md` |
| Period scheduler applies external period indices and enters conservative mode when updates are stale | `results/rtl_replay/period_scheduler_report.md` |
| Scrub pass engine performs a complete memory pass, correction writeback, and DUE reporting | `results/rtl_replay/scrub_pass_engine_report.md` |
| Integrated controller combines scheduler and scrub engine without computing the risk model in RTL | `results/rtl_replay/adaptive_controller_report.md` |
| Dangerous-state accounting distinguishes online DUE diagnostics from verification-only SDC audit | `results/rtl_replay/dangerous_state_audit_report.md` |
| Flattened synthesis gives hardware resource estimates for the controller | `results/synthesis/rtl_synthesis_summary.md` |


## Feasibility handoff from Chapter 2

| Case | Status | g_D | E_inst | E_residual | E_acc(tau_min) | Slack |
|---|---|---:|---:|---:|---:|---:|
| scrub_period_selectable_D3 | scrub_period_selectable | 0 | 0 | 0.00100050033358 | 8.93047891737e-05 | 0.00091119554441 |
| architecture_change_required_D1 | architecture_change_required | 0.009 | 0.009 | -0.00799949966642 | 8.93047891737e-05 | -0.00808880445559 |
| bandwidth_or_tau_min_insufficient | bandwidth_or_tau_min_insufficient | 1e-07 | 0.0001 | 0.000900500333584 | 0.00396466689616 | -0.00306416656258 |

Interpretation: Chapter 4 only proceeds to hardware period scheduling for
cases classified as `scrub_period_selectable`. The other two regions require
architectural changes or a lower achievable minimum period before the
scheduler can satisfy the risk budget.


## Implementable schedule result from Chapter 3

| Strategy | Exact E_acc | P_mission | Pass count | Risk utilization | Tau range, s |
|---|---:|---:|---:|---:|---:|
| fixed_allowed_10s | 0.000893037195719 | 0.000892638556677 | 2160 | 0.892590602664 | 10..10 |
| adaptive_current_exact_floor_down | 0.000951514916541 | 0.000951062369769 | 1098 | 0.95103907975 | 10..600 |

The adaptive exact-risk floor-down schedule reduces full-pass count from `2160` to `1098`, giving a fixed/adaptive gain of `1.96721311475`.


## RTL verification reports

### SEC-DED exhaustive verification

Source artifact: `results/rtl_replay/secded_exhaustive_report.md`.


The SEC-DED encoder/decoder was checked over a representative data-pattern set.

| Check | Count |
|---|---:|
| no-error decode checks | 8 |
| single-bit corrections | 312 |
| double-bit DUE detections | 5928 |
| sampled triple-bit patterns | 24 |
| sampled triple-bit detected DUE | 8 |
| sampled triple-bit SDC outcomes | 16 |
| failures | 0 |

Interpretation:

- Every single-bit corruption in the 39-bit codeword is corrected.
- Every double-bit corruption is detected as uncorrectable.
- Triple-bit corruptions are outside the guaranteed SEC-DED correction
  capability. The testbench records whether they become detected DUE or SDC
  relative to the golden data; SDC accounting is a verification-audit function,
  not an online SEC-DED guarantee.

### Period scheduler verification

Source artifact: `results/rtl_replay/period_scheduler_report.md`.


The scheduler was checked as the hardware endpoint of the Chapter 3
implementable schedule.

| Check | Value |
|---|---:|
| measured pass_start interval | 50 cycles |
| last pass duration | 10 cycles |
| safe-mode entries | 2 |
| failures | 0 |

Interpretation:

- The selected period index controls the interval between full-pass starts.
- The scheduler compensates for the pass duration when computing the idle wait.
- If control updates become stale, the safe conservative period index is applied.
- A fresh period update exits safe mode.

### Scrub pass engine verification

Source artifact: `results/rtl_replay/scrub_pass_engine_report.md`.


One complete SEC-DED scrub pass was executed over a protected memory model.

| Check | Value |
|---|---:|
| protected depth | 8 |
| completed passes | 1 |
| memory reads | 8 |
| correction writes | 1 |
| corrected single-bit errors | 1 |
| detected uncorrectable errors | 1 |
| wait cycles until pass_done | 26 |
| failures | 0 |

Interpretation:

- The pass engine reads every protected codeword exactly once per pass.
- A correctable single-bit corruption is written back as the restored codeword.
- A detected double-bit error is reported as DUE and is not falsely repaired.
- This block implements the Chapter 4 per-word scrub operation; period
  scheduling is handled separately by the period scheduler.

### Integrated adaptive controller verification

Source artifact: `results/rtl_replay/adaptive_controller_report.md`.


The integrated controller combines the Chapter 3 period scheduler with the
full-pass SEC-DED scrub engine.

| Check | Value |
|---|---:|
| completed passes | 4 |
| memory reads | 25 |
| correction writes | 1 |
| corrected single-bit errors | 1 |
| detected uncorrectable errors | 3 |
| safe-mode entries | 2 |
| last pass duration | 27 cycles |
| failures | 0 |

Interpretation:

- The controller consumes an external period index and does not compute the
  radiation-risk model in RTL.
- Full sequential passes are launched by the scheduler.
- Single-bit SEC-DED corruptions are corrected and written back.
- Detected double-bit corruptions are reported as DUE and are not falsely
  repaired.
- Stale external period updates force the conservative safe period.

### Dangerous-state audit verification

Source artifact: `results/rtl_replay/dangerous_state_audit_report.md`.


The integrated controller was run against a memory containing a correctable
single-bit corruption, a detected double-bit DUE, and a triple-bit corruption
outside the SEC-DED correction guarantee.

| Metric | Value |
|---|---:|
| completed passes | 5 |
| memory reads | 39 |
| correction writes | 2 |
| online corrected events | 2 |
| online detected DUE events | 5 |
| final uncorrectable words | 1 |
| final SDC words | 1 |
| final dangerous words | 2 |
| failures | 0 |

Interpretation:

- Single-bit accumulated errors are corrected by the scrub pass.
- Detected double-bit states are reported as DUE but are not repaired.
- A triple-bit state can be outside the SEC-DED guarantee and become SDC.
- `final_sdc_words` is obtained by a verification-only golden-reference audit,
  not by an online SEC-DED hardware flag.
- This is the Chapter 4 distinction between online diagnostics and the broader
  dangerous-state class used in Chapter 2.


## Synthesis/resource estimate

| Flow | Top | Cells | FF estimate | LUT estimate | MUX estimate | Wire bits |
|---|---|---:|---:|---:|---:|---:|
| generic_yosys | secded_32_39_encoder | 117 | 0 | 0 | 0 | 321 |
| generic_yosys | secded_32_39_decoder | 879 | 0 | 0 | 516 | 5294 |
| generic_yosys | period_scheduler | 1279 | 166 | 0 | 210 | 1671 |
| generic_yosys | scrub_pass_engine | 1543 | 171 | 0 | 517 | 6273 |
| generic_yosys | adaptive_scrub_controller | 2824 | 337 | 0 | 727 | 8302 |
| xilinx_xc7 | secded_32_39_encoder | 104 | 0 | 32 | 1 | 248 |
| xilinx_xc7 | secded_32_39_decoder | 324 | 0 | 143 | 33 | 834 |
| xilinx_xc7 | period_scheduler | 720 | 166 | 157 | 12 | 1245 |
| xilinx_xc7 | scrub_pass_engine | 861 | 171 | 168 | 28 | 1720 |
| xilinx_xc7 | adaptive_scrub_controller | 1561 | 337 | 318 | 31 | 3205 |

For the integrated `adaptive_scrub_controller`, the flattened XC7 estimate is:

- cells: `1561`;
- FF estimate: `337`;
- LUT estimate: `318`;
- MUX estimate: `31`.

This is a synthesis/resource estimate only. It does not establish Fmax
because no target-specific placement and routing has been performed.


## Explicit limits

- The RTL controller does not compute `nu(t)`, `g_D`, `E_inst`, or `E_residual`.
- The RTL controller consumes an externally generated `period_index` stream.
- SEC-DED online logic does not guarantee detection of every 3+ bit corruption.
- `final_sdc_words` is a verification-audit metric based on a golden reference.
- The MBU feasibility cases are illustrative unless technology-specific `p_m` and `h_m^(D)` values are supplied.
- Yosys estimates are not timing closure and do not claim maximum frequency.
