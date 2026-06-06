# Measured-error policy seed sweep

This report repeats selected measured-error policy simulations over
`30` Poisson seeds per policy.

## Baselines

| Strategy | Pass count | P mission | Risk utilization |
|---|---:|---:|---:|
| fixed | 31553280 | 0.00553465940419 | 0.552223573568 |
| current adaptive | 2547210 | 0.00999993405782 | 0.999993372534 |
| delayed 1h adaptive | 2649330 | 0.00999990177991 | 0.999990128469 |

## Seed sweep summary

| Policy | Target met fraction | Risk util. mean | Risk util. p95 | Risk util. max | Pass mean | Fixed/policy gain mean | Current/policy pass ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| measured_q8_high1_max120 | 0 | 1.0760312605 | 1.0786183649 | 1.08136574536 | 3586240.16667 | 8.79842914406 | 0.710273122162 |
| measured_q16_high1_max120 | 1 | 0.654492398768 | 0.65561856129 | 0.655868776125 | 6552740.4 | 4.81528003154 | 0.388724387739 |
| measured_q16_high1_max3600 | 1 | 0.681094456074 | 0.682998757103 | 0.68429515097 | 6456500.96667 | 4.88705572305 | 0.394518643016 |
| measured_q32_high1_max120 | 1 | 0.388949765982 | 0.389987527014 | 0.390752975896 | 12700080.3667 | 2.48449451413 | 0.200566447334 |

## Interpretation

- Policies with `target_met_fraction=1` satisfy the exact-risk target across all sampled seeds.
- Aggressive policies can be useful as demonstrations of adaptation but are not certified replacements if they exceed the target.
- The external Chapter 3 current/delayed schedules remain the primary risk-certified strategies.
