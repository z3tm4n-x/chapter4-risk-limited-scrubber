# Chapter 4 evidence pack

This aggregate file collects reproducible model, RTL, fault-replay,
diagnostic, measured-mode, feasibility, Monte Carlo, and synthesis
artifacts for the Chapter 4 implementation.

It is an evidence pack, not dissertation prose.

## Build metadata

- Git commit: `095e36bbd4c70eb39e858a574dc430071860cc07`

## Claim matrix

| Claim | Evidence artifact |
|---|---|
| The five-year upset series is imported and transformed into the total upset-rate series used by Chapter 3. | `results/schedules/ch3_series_import_summary.csv` |
| The fixed/current/delayed schedules are compiled on the dissertation geometry and target probability. | `results/schedules/ch3_five_year_summary.md` |
| The RTL controller executes model-generated period indices with zero pass-count mismatch on representative windows. | `results/chapter4_model_rtl_certificate.md` |
| The selected radiation windows are replayed with fault streams and separated DUE/persistent/SDC-audit metrics. | `results/rtl_replay/ch3_fault_replay_summary.md` |
| The same physical MBU is dangerous without interleaving and correctable when split across codewords. | `results/rtl_replay/interleaving_mbu_summary.md` |
| The diagnostic block raises alert, persistent-DUE, out-of-envelope, and force-conservative flags from SEC-DED symptoms. | `results/rtl_replay/diagnostic_supervisor_report.md` |
| The top-level external-period controller exposes diagnostic flags from real scrub events. | `results/rtl_replay/integrated_diagnostic_controller_report.md` |
| The residual-budget boundary is reproduced numerically; above rho_crit, tau_min is insufficient. | `results/feasibility/rho_d_sweep_summary.md` |
| The exact accumulated-risk kernel is validated by direct random placement at accelerated lambda values. | `results/monte_carlo/accumulation_monte_carlo_report.md` |
| The onboard estimator relaxes on quiet passes, speeds up on corrections, and forces safe period on DUE. | `results/rtl_replay/measured_error_estimator_report.md` |
| The measured-error estimator is integrated into a complete autonomous scrub controller. | `results/rtl_replay/measured_error_controller_report.md` |
| Flattened Yosys/XC7 synthesis estimates quantify the hardware cost of the blocks. | `results/synthesis/rtl_synthesis_summary.md` |
| Schedule benefit and RTL resource cost are combined in one certificate. | `results/chapter4_overhead_gain_certificate.md` |

## Compact key numbers

- Fixed pass count: `31553280`.
- Current adaptive pass count: `2547210`; fixed/current gain: `12.3873885545`.
- Delayed 1h adaptive pass count: `2649330`; fixed/delayed gain: `11.9099092978`.
- Current adaptive mission probability: `0.00999993405782`.
- Delayed 1h mission probability: `0.00999990177991`.
- External adaptive controller XC7 estimate: `444` LUT, `550` FF.
- Measured-error controller XC7 estimate: `603` LUT, `654` FF.
- Measured-error increment over external endpoint: `+159` LUT, `+104` FF.
- Last sampled selectable rho_D: `0.88955`.
- First sampled tau_min-insufficient rho_D: `0.89`.
- Monte Carlo accumulated-risk validation 4-sigma pass: `true`.

## Aggregated artifact contents

## Chapter 3 five-year series import

Source artifact: `results/schedules/ch3_series_import_summary.csv`.

metric,value
input_xlsx_sha256,06e042e70dd305e83ba78bfe291551ee32644bd3fd04d15c2e3d6fadbe2145dd
hour_count,43824
valid_proton_count,43676
missing_proton_count,148
missing_interval_count,8
start_timestamp_utc,2021-01-01T00:00:00Z
end_timestamp_utc,2025-12-31T23:00:00Z
proton_filled_sum,36885.4393475
proton_filled_mean,0.841672128228
proton_filled_median,0.487968781583
proton_filled_max,298.004011907
proton_filled_cv2,26.957396267
proton_filled_eta_const,27.957396267
background_gp_mean,0.468836172538
event_sp_mean,0.39684601895
total_nu_sum,309956.953914
total_nu_mean,7.07276729449
total_nu_median,5.17307697509
total_nu_max,1193.96354958
total_nu_cv2,6.24295991773
total_nu_eta_const,7.24295991773
positive_log_growth_q99,0.102066047052
positive_growth_factor_q99,1.26492870188
max_growth_factor,23.9692217536
max_log_growth,1.37965393334
missing_interval_0_start,2021-03-10T16:00:00Z
missing_interval_0_end,2021-03-15T18:00:00Z
missing_interval_0_length_hours,123
missing_interval_1_start,2021-03-23T14:00:00Z
missing_interval_1_end,2021-03-23T19:00:00Z
missing_interval_1_length_hours,6
missing_interval_2_start,2021-04-29T21:00:00Z
missing_interval_2_end,2021-04-29T22:00:00Z
missing_interval_2_length_hours,2
missing_interval_3_start,2021-06-11T19:00:00Z
missing_interval_3_end,2021-06-11T21:00:00Z
missing_interval_3_length_hours,3
missing_interval_4_start,2021-06-29T13:00:00Z
missing_interval_4_end,2021-06-29T18:00:00Z
missing_interval_4_length_hours,6
missing_interval_5_start,2021-11-24T03:00:00Z
missing_interval_5_end,2021-11-24T06:00:00Z
missing_interval_5_length_hours,4
missing_interval_6_start,2025-11-25T02:00:00Z
missing_interval_6_end,2025-11-25T03:00:00Z
missing_interval_6_length_hours,2
missing_interval_7_start,2025-12-23T20:00:00Z
missing_interval_7_end,2025-12-23T21:00:00Z
missing_interval_7_length_hours,2
check_mean_total_relative_error,0.000391413647726
check_mean_total_within_tolerance,true
check_cv2_total_relative_error,0.000474345790182
check_cv2_total_within_tolerance,true
check_eta_const_relative_error,0.000408828415847
check_eta_const_within_tolerance,true

## Chapter 3 five-year exact-risk schedules

Source artifact: `results/schedules/ch3_five_year_summary.md`.

# Chapter 3 five-year schedule summary

This report is generated from `data/ch3_five_year_upsets.csv` and the
main Chapter 3 configuration.

## Series metrics

| Metric | Value |
|---|---:|
| hours | 43824 |
| mean_nu_per_hour | 7.07276729449 |
| cv2 | 6.24295991773 |
| eta_const = 1 + CV^2 | 7.24295991773 |
| max_nu_per_hour | 1193.96354958 |

## Strategies

| Strategy | E risk | P mission | Pass count | Fixed/strategy gain | Tau range, s | Eta shape |
|---|---:|---:|---:|---:|---:|---:|
| fixed | 0.00555003238058 | 0.00553465940419 | 31553280 | 1 | 5..5 | 7.24295991773 |
| current | 0.0100502692452 | 0.00999993405782 | 2547210 | 12.3873885545 | 1..120 | 1 |
| delayed_1h | 0.0100502366413 | 0.00999990177991 | 2649330 | 11.9099092978 | 1..120 | 1.04935369403 |

## Model-to-RTL schedule replay certificate

Source artifact: `results/chapter4_model_rtl_certificate.md`.

# Chapter 4 model-to-RTL certificate

This certificate aggregates the Chapter 3 five-year model schedules and
the Chapter 4 RTL window replay results.

## Series

| Metric | Value |
|---|---:|
| hours | 43824 |
| start | 2021-01-01T00:00:00Z |
| end | 2025-12-31T23:00:00Z |
| mean total nu, 1/hour | 7.07276729449 |
| CV^2 | 6.24295991773 |
| eta_const = 1 + CV^2 | 7.24295991773 |
| max total nu, 1/hour | 1193.96354958 |

## Five-year exact-risk schedules

| Strategy | P mission | E risk | Risk utilization | Pass count | Fixed/strategy gain | Tau range, s | Eta shape |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed | 0.00553465940419 | 0.00555003238058 | 0.552223573568 | 31553280 | 1 | 5..5 | 7.24295991773 |
| current | 0.00999993405782 | 0.0100502692452 | 0.999993372534 | 2547210 | 12.3873885545 | 1..120 | 1 |
| delayed_1h | 0.00999990177991 | 0.0100502366413 | 0.999990128469 | 2649330 | 11.9099092978 | 1..120 | 1.04935369403 |

## Fixed-candidate boundary

The best allowed fixed period is 5 s with risk utilization 0.552223573568.
The next fixed candidate, 10 s, is not allowed: risk utilization 1.10444650394.
Therefore fixed/adaptive gain is larger than the continuous 1+CV^2 bound because the fixed baseline is discretized.

## RTL window replay

| Strategy | Window | Model passes | RTL pass starts | Completed | Delta | Mismatches | Safe cycles | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| current | quiet_background | 1470 | 1470 | 1470 | 0 | 0 | 0 | 0 |
| delayed_1h | quiet_background | 1470 | 1470 | 1470 | 0 | 0 | 0 | 0 |
| current | storm_rise | 15270 | 15270 | 15270 | 0 | 0 | 0 | 0 |
| delayed_1h | storm_rise | 15300 | 15300 | 15300 | 0 | 0 | 0 | 0 |
| current | storm_peak | 105600 | 105600 | 105600 | 0 | 0 | 0 | 0 |
| delayed_1h | storm_peak | 105300 | 105300 | 105300 | 0 | 0 | 0 | 0 |
| current | storm_decay | 5340 | 5340 | 5340 | 0 | 0 | 0 | 0 |
| delayed_1h | storm_decay | 5490 | 5490 | 5490 | 0 | 0 | 0 | 0 |
| current | tau_min_saturation | 100260 | 100260 | 100260 | 0 | 0 | 0 | 0 |
| delayed_1h | tau_min_saturation | 98520 | 98520 | 98520 | 0 | 0 | 0 | 0 |
| current | delayed_sensitive | 31800 | 31800 | 31800 | 0 | 0 | 0 | 0 |
| delayed_1h | delayed_sensitive | 32790 | 32790 | 32790 | 0 | 0 | 0 | 0 |

## Verdict

- Five-year model schedules satisfy the mission-risk target: `true`.
- RTL window replay matches model pass counts with zero mismatches: `true`.
- The RTL controller receives only period indices; it does not receive nu(t), risk values, or the radiation model.

## Radiation-window fault replay

Source artifact: `results/rtl_replay/ch3_fault_replay_summary.md`.

# Chapter 3 radiation-window fault replay summary

The same external fault stream is replayed against current and delayed
period-index schedules for each selected radiation window.

`detected_due_events` counts every online DUE pulse. `new_due_words` and
`persistent_due_detections` separate first observations from repeated
diagnostic load. `final_sdc_words` is a verification-only golden-reference
audit metric, not an online SEC-DED output.

| Strategy | Window | Passes | Reads | Writes | Corrected | DUE events | New DUE words | Persistent DUE | Final DUE | Final SDC | Final dangerous | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| current | quiet_background | 1470 | 11760 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| delayed_1h | quiet_background | 1470 | 11760 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| current | storm_rise | 15270 | 122160 | 5 | 5 | 14909 | 1 | 14908 | 1 | 1 | 2 | 0 |
| delayed_1h | storm_rise | 15300 | 122400 | 5 | 5 | 14939 | 1 | 14938 | 1 | 1 | 2 | 0 |
| current | storm_peak | 105600 | 844800 | 5 | 5 | 95757 | 1 | 95756 | 1 | 1 | 2 | 0 |
| delayed_1h | storm_peak | 105300 | 842400 | 5 | 5 | 98997 | 1 | 98996 | 1 | 1 | 2 | 0 |
| current | storm_decay | 5340 | 42720 | 5 | 5 | 4319 | 1 | 4318 | 1 | 1 | 2 | 0 |
| delayed_1h | storm_decay | 5490 | 43920 | 5 | 5 | 4529 | 1 | 4528 | 1 | 1 | 2 | 0 |
| current | tau_min_saturation | 100260 | 802080 | 5 | 5 | 99539 | 1 | 99538 | 1 | 1 | 2 | 0 |
| delayed_1h | tau_min_saturation | 98520 | 788160 | 5 | 5 | 97799 | 1 | 97798 | 1 | 1 | 2 | 0 |
| current | delayed_sensitive | 31800 | 254400 | 5 | 5 | 31439 | 1 | 31438 | 1 | 1 | 2 | 0 |
| delayed_1h | delayed_sensitive | 32790 | 262320 | 5 | 5 | 32429 | 1 | 32428 | 1 | 1 | 2 | 0 |

## Interleaving MBU experiment

Source artifact: `results/rtl_replay/interleaving_mbu_summary.md`.

# Interleaving MBU RTL experiment

The same physical 3-bit MBU is replayed with two logical mappings.

| Scenario | Physical multiplicity | Interleave depth | Corrected | DUE | Writes | Final DUE | Final SDC | Final dangerous | Failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D1_same_word | 3 | 1 | 1 | 0 | 1 | 0 | 1 | 1 | 0 |
| D3_split | 3 | 3 | 3 | 0 | 3 | 0 | 0 | 0 | 0 |

Interpretation:

- Without interleaving, the physical MBU maps into one SEC-DED codeword and leaves the guaranteed correction envelope.
- With interleaving depth 3, the same physical multiplicity maps to three single-bit codeword errors and is repaired by scrub writeback.
- SDC is reported only by golden-reference verification audit, not by online SEC-DED hardware.

## Diagnostic supervisor RTL

Source artifact: `results/rtl_replay/diagnostic_supervisor_report.md`.

# Diagnostic supervisor RTL report

This unit test verifies the hardware diagnostic layer used to escalate
from ordinary SEC-DED scrubbing to conservative/out-of-envelope modes.

| Metric | Value |
|---|---:|
| alert_path_alert_events | 2 |
| alert_path_out_of_envelope | 1 |
| clear_path_verified | 1 |
| danger_events | 2 |
| new_due_words | 1 |
| persistent_due | 1 |
| out_of_envelope | 1 |
| force_conservative | 1 |
| failures | 0 |

Interpretation:

- A high corrected-event count raises `alert_flag`.
- Consecutive alert passes raise `out_of_envelope_flag`.
- A new DUE raises `danger_detected_flag` and `force_conservative`.
- Repeated DUE at the same word raises `persistent_due_flag` and `out_of_envelope_flag`.
- The block observes SEC-DED symptoms; it does not compute the radiation model.

## Integrated diagnostic controller RTL

Source artifact: `results/rtl_replay/integrated_diagnostic_controller_report.md`.

# Integrated diagnostic controller RTL report

This report verifies that the top-level adaptive scrub controller exposes
diagnostic-supervisor flags from actual SEC-DED scrub events.

| Metric | Value |
|---|---:|
| passes | 5 |
| reads | 32 |
| writes | 1 |
| corrected | 1 |
| due | 3 |
| diag_alert | 1 |
| diag_danger | 1 |
| diag_persistent | 1 |
| diag_out_of_envelope | 1 |
| diag_force_conservative | 1 |
| diag_alert_events | 1 |
| diag_new_due_words | 1 |
| diag_persistent_due | 2 |
| failures | 0 |

Interpretation:

- Corrected SEC-DED events are visible to the integrated diagnostic path.
- Same-word persistent DUE raises danger and persistent-DUE diagnostics.
- `diag_force_conservative` is a system-level request; the controller still does not compute the radiation model.

## rho_D residual-budget sweep

Source artifact: `results/feasibility/rho_d_sweep_summary.md`.

# rho_D residual-budget sweep

This sweep demonstrates the Chapter 2 feasibility handoff for the
Chapter 3 five-year series.

| Quantity | Value |
|---|---:|
| target probability | 0.01 |
| target risk E | 0.0100503358535 |
| tau_min, s | 1 |
| E_acc(tau_min) | 0.00111000681681 |
| P_acc(tau_min) | 0.00110939098712 |
| rho_crit = 1 - E_acc(tau_min)/E_target | 0.889555251388 |

## Sweep

| rho_D | Status | E_residual | Slack after tau_min | tau_min/residual utilization | Schedule passes | Tau range, s | Saturated tau_min |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | scrub_period_selectable | 0.0100503358535 | 0.00894032903669 | 0.110444748612 | 2547210 | 1..120 | true |
| 0.25 | scrub_period_selectable | 0.00753775189013 | 0.00642774507332 | 0.147259664817 | 3461040 | 1..120 | true |
| 0.5 | scrub_period_selectable | 0.00502516792675 | 0.00391516110994 | 0.220889497225 | 5715990 | 1..120 | true |
| 0.75 | scrub_period_selectable | 0.00251258396338 | 0.00140257714656 | 0.44177899445 | 13830480 | 1..30 | true |
| 0.85 | scrub_period_selectable | 0.00150755037803 | 0.000397543561214 | 0.736298324083 | 36906120 | 1..10 | true |
| 0.88 | scrub_period_selectable | 0.00120604030242 | 9.60334856091e-05 | 0.920372905104 | 79052400 | 1..5 | true |
| 0.889 | scrub_period_selectable | 0.00111558727974 | 5.58046292762e-06 | 0.994997735248 | 140815800 | 1..2 | true |
| 0.8895 | scrub_period_selectable | 0.00111056211181 | 5.55295000872e-07 | 0.999499987443 | 155694600 | 1..2 | true |
| 0.88955 | scrub_period_selectable | 0.00111005959502 | 5.27782081971e-08 | 0.999952454617 | 157554000 | 1..2 | true |
| 0.89 | bandwidth_or_tau_min_insufficient | 0.00110553694389 | -4.46987292588e-06 | 1.0040431692 | - | - | - |
| 0.9 | bandwidth_or_tau_min_insufficient | 0.00100503358535 | -0.000104973231461 | 1.10444748612 | - | - | - |
| 0.95 | bandwidth_or_tau_min_insufficient | 0.000502516792675 | -0.000607490024136 | 2.20889497225 | - | - | - |
| 0.99 | bandwidth_or_tau_min_insufficient | 0.000100503358535 | -0.00100950345828 | 11.0444748612 | - | - | - |
| 1 | architecture_change_required | 0 | -0.00111000681681 | inf | - | - | - |

Interpretation:

- Below rho_crit, a scrub schedule can be selected from the residual accumulated-risk budget.
- Near rho_crit, the schedule is forced toward tau_min saturation.
- Above rho_crit, even continuous operation at tau_min cannot satisfy the residual budget; the system must escalate.
- This computation is model-side evidence for the out-of-envelope flag implemented by the diagnostic supervisor.

## Accumulated-risk Monte Carlo validation

Source artifact: `results/monte_carlo/accumulation_monte_carlo_report.md`.

# Accumulated-risk Monte Carlo validation

This report validates the accumulated dangerous-state kernel by direct
random placement of independent bit errors over the dissertation memory
geometry. The test uses accelerated lambda values where collisions are
observable in finite Monte Carlo time.

## Geometry

| Quantity | Value |
|---|---:|
| word_bits | 39 |
| codeword_count | 1935832 |
| physical_bits | 75497448 |
| alpha | 2.516641390536e-07 |
| seed | 20260605 |

## Results

| Lambda | Trials | Empirical q | Exact q | Quadratic q | Empirical/exact rel. err. | Quadratic/exact rel. err. | z-score | Pass |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 150000 | 0.000526666666667 | 0.000628952196389 | 0.000629160347634 | 0.16262846415 | 0.000330949229522 | -1.58011111243 | true |
| 100 | 120000 | 0.00248333333333 | 0.00251339528886 | 0.00251664139054 | 0.0119606954215 | 0.00129152055522 | -0.207981121863 | true |
| 200 | 80000 | 0.009775 | 0.0100154161226 | 0.0100665655621 | 0.0240046064622 | 0.00510707083366 | -0.68290433112 | true |
| 300 | 60000 | 0.0217333333333 | 0.0223930219985 | 0.0226497725148 | 0.0294595640184 | 0.0114656483783 | -1.09213455271 | true |

## Interpretation

- `q_acc_exact(lambda)` agrees with direct random placement within the configured 4-sigma statistical gate.
- The quadratic kernel is close in the low-lambda region and increasingly conservative as lambda grows.
- Working mission lambdas are much smaller than these accelerated validation cases; direct observation there would be impractical.
- Overall Monte Carlo pass: `true`.

## Measured-error period estimator RTL

Source artifact: `results/rtl_replay/measured_error_estimator_report.md`.

# Measured-error period estimator RTL report

This unit test verifies an autonomous onboard period-index estimator
driven only by SEC-DED corrected/DUE observations.

| Metric | Value |
|---|---:|
| final_period_index | 6 |
| updates | 6 |
| high_activity_events | 2 |
| quiet_relax_events | 1 |
| forced_safe_events | 1 |
| failures | 0 |

Interpretation:

- Quiet passes relax the scrub period toward larger period indices.
- High corrected-event activity accelerates scrubbing by lowering the period index.
- Any DUE forces the conservative safe period index.
- This is an onboard fallback strategy; it is not the exact-risk schedule compiler.

## Integrated measured-error controller RTL

Source artifact: `results/rtl_replay/measured_error_controller_report.md`.

# Integrated measured-error scrub controller RTL report

This report verifies a complete onboard measured-error mode: SEC-DED
observations drive an autonomous period estimator, which drives the same
`period_index` interface used by the external Chapter 3 schedule path.

| Metric | Value |
|---|---:|
| passes | 8 |
| reads | 56 |
| writes | 3 |
| corrected | 3 |
| due | 3 |
| updates | 7 |
| high_activity | 1 |
| quiet_relax | 1 |
| forced_safe | 1 |
| final_period_index | 0 |
| diag_danger | 1 |
| diag_force | 1 |
| failures | 0 |

Interpretation:

- Quiet operation emits measured period updates without speeding up.
- Multiple corrected single-bit events speed up the measured period.
- DUE forces the measured safe period index.
- The integrated diagnostic path raises danger and conservative-mode request.
- This mode is a practical onboard fallback, not the exact-risk schedule compiler.

## RTL synthesis/resource summary

Source artifact: `results/synthesis/rtl_synthesis_summary.md`.

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

## Overhead/gain certificate

Source artifact: `results/chapter4_overhead_gain_certificate.md`.

# Chapter 4 overhead/gain certificate

This certificate combines the Chapter 3 five-year schedule gain with
the Chapter 4 RTL resource estimates.

## Schedule benefit

| Strategy | Pass count | P mission | Risk utilization | Fixed/strategy gain | Pass reduction vs fixed |
|---|---:|---:|---:|---:|---:|
| fixed | 31553280 | 0.00553465940419 | 0.552223573568 | 1 | 0 |
| current adaptive | 2547210 | 0.00999993405782 | 0.999993372534 | 12.3873885545 | 0.919272734879 |
| delayed 1h adaptive | 2649330 | 0.00999990177991 | 0.999990128469 | 11.9099092978 | 0.916036304308 |

## XC7 resource estimates

| Component | LUT | FF | Cells | Meaning |
|---|---:|---:|---:|---|
| SEC-DED encoder | 32 | 0 | 104 | ECC encode datapath |
| SEC-DED decoder | 143 | 0 | 324 | ECC decode/correction datapath |
| Period scheduler | 162 | 167 | 720 | External period-index endpoint |
| Scrub pass engine | 168 | 171 | 861 | Full memory pass and writeback |
| Diagnostic supervisor | 247 | 212 | 962 | Alert/DUE/out-of-envelope flags |
| External adaptive controller | 444 | 550 | 2385 | Chapter 3 schedule endpoint |
| Measured-error estimator | 139 | 104 | 511 | Onboard period estimator only |
| Measured-error controller | 603 | 654 | 2853 | Integrated onboard fallback |

## Incremental measured-mode cost

| Comparison | Delta LUT | Delta FF | Delta LUT % | Delta FF % |
|---|---:|---:|---:|---:|
| measured_error_scrub_controller - adaptive_scrub_controller | 159 | 104 | 35.8108 | 18.9091 |

## Interpretation

- The external current adaptive schedule reduces pass count by `12.3874x` relative to the best allowed fixed schedule.
- The delayed one-hour adaptive schedule reduces pass count by `11.9099x`.
- The measured-error onboard fallback costs `+159` LUT and `+104` FF over the external-period endpoint.
- These are synthesis estimates only; they do not establish timing closure or Fmax.
