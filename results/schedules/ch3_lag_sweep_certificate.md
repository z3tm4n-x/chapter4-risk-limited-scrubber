# Chapter 3 estimate-update-rate sensitivity certificate

## Pre-registration

- Admissibility rule: A variant is admissible if P_mission <= 0.01 on the full five-year series evaluated against true nu(t).
- Threshold rule: For age sweeps, the threshold is the largest lag that remains admissible. For session sweeps, a cadence is admissible only if every phase is admissible; the reported limiting value is the worst phase.
- Edge rule: For unavailable history at the beginning of the series, clamp the source index to 0, identical to delayed_1h.
- Prediction recorded before inspecting results: With frozen one-hour calibration, sensitivity is expected between 3 and 6 hours of lag; U=6 h session-limited operation is expected to be borderline. Reoptimized variants may remain admissible by spending additional passes.

Two calibration modes are reported:

- `reoptimized`: each estimate stream receives its own exact-risk-calibrated C;
- `frozen_1h`: the C calibrated for delayed_1h is reused after degrading the estimate-update channel.

The `frozen_1h` mode is the operational degradation test. The `reoptimized`
mode is a design curve showing how many extra passes are required if the
communication cadence is known in advance.

## Control check

- Control variant: `age_L1` / `reoptimized`.
- Pass count: `2649330`.
- P_mission: `0.00999990177991`.
- max_q_per_pass: `1.5857615866e-06`.
- Control verdict: `pass`.

## Age-family results

| Mode | L, h | P mission | Risk util. | Passes | Fixed/gain | max q/pass | max hourly budget frac. | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reoptimized | 1 | 0.00999990177991 | 0.999990128469 | 2649330 | 11.9099092978 | 1.5857615866e-06 | 0.01893383397 | pass |
| frozen_1h | 1 | 0.00999990177991 | 0.999990128469 | 2649330 | 11.9099092978 | 1.5857615866e-06 | 0.01893383397 | pass |
| reoptimized | 3 | 0.00988148093586 | 0.988089048691 | 4883490 | 6.46121523746 | 1.6454089712e-05 | 0.0982300887363 | pass |
| frozen_1h | 3 | 0.0173765716147 | 1.74415228798 | 2649510 | 11.9091001732 | 6.58145605785e-05 | 0.196454809683 | fail |
| reoptimized | 6 | 0.00985881830598 | 0.985811657809 | 9462300 | 3.33463111506 | 7.0254007458e-06 | 0.0838825788297 | pass |
| frozen_1h | 6 | 0.028440516903 | 2.87082783717 | 2649780 | 11.9078866925 | 7.40518948145e-05 | 0.221043045408 | fail |
| reoptimized | 12 | 0.00983597450553 | 0.983516113664 | 10356360 | 3.04675387878 | 6.25216210712e-06 | 0.0746501871968 | pass |
| frozen_1h | 12 | 0.0371352617781 | 3.76528071825 | 2650320 | 11.9054604727 | 7.40518948145e-05 | 0.221043045408 | fail |
| reoptimized | 24 | 0.00999979598397 | 0.999979495534 | 18444600 | 1.71070557236 | 2.76819958185e-06 | 0.0991560743832 | pass |
| frozen_1h | 24 | 0.0664573340424 | 6.84241926667 | 2651400 | 11.900610998 | 9.9649817583e-05 | 0.594904403408 | fail |

## Session-family aggregate results

| Mode | U, h | Aggregate | Worst/median phase | P mission | Risk util. | Passes | Fixed/gain | max q/pass | Verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| reoptimized | 6 | worst_phase | 1 | 0.00999985290419 | 0.999985216253 | 5472960 | 5.76530433257 | 1.85135397007e-05 | pass |
| frozen_1h | 6 | worst_phase | 2 | 0.0226976474135 | 2.28442160982 | 2661120 | 11.8571428571 | 7.40518948145e-05 | fail |
| reoptimized | 12 | worst_phase | 3 | 0.00999983437873 | 0.999983354367 | 6002100 | 5.25704003599 | 1.02520566825e-05 | pass |
| frozen_1h | 12 | worst_phase | 10 | 0.0340329332742 | 3.44521200802 | 2652660 | 11.8949582683 | 7.40518948145e-05 | fail |
| reoptimized | 24 | worst_phase | 6 | 0.00999991520938 | 0.999991478187 | 14133600 | 2.23250127356 | 4.62842354348e-06 | pass |
| frozen_1h | 24 | worst_phase | 10 | 0.0622701248322 | 6.39713457863 | 2700180 | 11.6856209586 | 9.9649817583e-05 | fail |
| reoptimized | 6 | median_phase | - | 0.00999664122888 | 0.99966242997 | 5312640 | 5.94469800195 | 1.74838147063e-05 | pass |
| frozen_1h | 6 | median_phase | - | 0.0191254036182 | 1.92140276571 | 2653965 | 11.8891275288 | 6.99332276965e-05 | fail |
| reoptimized | 12 | median_phase | - | 0.00941778675981 | 0.941502322048 | 9372330 | 3.36666025086 | 8.63872871417e-06 | pass |
| frozen_1h | 12 | median_phase | - | 0.0265776338464 | 2.68022928973 | 2644065 | 11.9336706439 | 7.40518948145e-05 | fail |
| reoptimized | 24 | median_phase | - | 0.00929568001146 | 0.929238049734 | 9450810 | 3.33882705556 | 4.62842354348e-06 | pass |
| frozen_1h | 24 | median_phase | - | 0.0379694762097 | 3.85154190291 | 2642670 | 11.9399476739 | 7.40518948145e-05 | fail |

## Interpretation notes

- `max_q_per_pass` is the largest exact accumulated-risk probability for one scrub cycle.
- `max_hourly_budget_fraction` is the largest single-hour additive-risk contribution divided by the five-year target E.
- For session variants, `worst_phase` is selected by maximum risk utilization.
- A session cadence is considered admissible only if all phases pass.
