# Chapter 3 C-transfer train/test certificate

## Purpose

This certificate checks whether the adaptive-schedule coefficient `C`,
calibrated on one disjoint part of the five-year series, remains safe on
another part without reoptimization.

The check is not a proof of a future mission. It is a transferability
test on held-out portions of the reconstructed Chapter 3 series.

## Rules

- Budget rule: Train and test windows are compared to proportional shares of the full five-year additive risk budget. This is a transferability criterion based on uniform budget consumption, not a claim that the optimal schedule must spend risk uniformly in time.
- Edge rule: For unavailable history at the beginning of each train/test window, clamp the source index to 0, identical to delayed_1h.

## Results

| Direction | Strategy | Train | Test | Test risk util. | Test passes | Gain vs 5 s | C_train/C_required_test | Verdict |
|---|---|---|---|---:|---:|---:|---:|---:|
| early_to_late | current | early_2021_2023 | late_2024_2025 | 0.723146675373 | 863160 | 14.6342277214 | 0.630260835518 | pass |
| early_to_late | delayed_1h | early_2021_2023 | late_2024_2025 | 0.800976032248 | 867090 | 14.567899526 | 0.696094448818 | pass |
| early_to_late | forecast | early_2021_2023 | late_2024_2025 | 0.746919901511 | 873630 | 14.4588441331 | 0.637809979526 | pass |
| late_to_early | current | late_2024_2025 | early_2021_2023 | 1.60065793737 | 1250286 | 15.1338173826 | 1.58664467732 | fail |
| late_to_early | delayed_1h | late_2024_2025 | early_2021_2023 | 1.48354365458 | 1370262 | 13.8087460646 | 1.43658666105 | fail |
| late_to_early | forecast | late_2024_2025 | early_2021_2023 | 1.58630984183 | 1271688 | 14.8791212939 | 1.56786508851 | fail |

## Interpretation

- The transfer check shows that the early 2021--2023 window is more
  restrictive for adaptive-C calibration under the proportional-budget
  criterion, although the later 2024--2025 window contains the largest
  individual event peaks.
- This is consistent with the fact that the early window has a higher mean
  upset rate, while the late window has much higher variability. The late
  window is difficult for fixed-period operation, but its high variability
  is precisely where adaptive scheduling gains leverage.
- A value `C_train/C_required_test < 1` means that the train-calibrated
  coefficient is more conservative than required on the test window.
- A value `C_train/C_required_test > 1` means that the train-calibrated
  coefficient is too permissive on the test window and must be reduced by
  that factor or replaced by a qualification-scenario calibration.
- Therefore `C` must be selected over a qualification envelope of
  representative scenarios using the most restrictive exact-risk-calibrated
  value, rather than by visual inspection of the largest event peak.
