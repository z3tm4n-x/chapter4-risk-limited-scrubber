# Measured-error policy model evaluation

This report evaluates autonomous counter-based scrub-period policies on
the five-year Chapter 3 total upset-rate series.

The policy receives only sampled corrected-event counts per completed pass.
Risk is evaluated separately with `q_acc_exact(lambda)` on the true series.

## Baselines

| Strategy | Pass count | P mission | Risk utilization |
|---|---:|---:|---:|
| fixed | 31553280 | 0.00553465940419 | 0.552223573568 |
| current adaptive | 2547210 | 0.00999993405782 | 0.999993372534 |
| delayed 1h adaptive | 2649330 | 0.00999990177991 | 0.999990128469 |

## Measured policies

| Policy | Target met | P mission | Risk utilization | Pass count | Fixed/policy gain | Current/policy pass ratio | Tau range, s | High events | Relax events |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| measured_q4_high1_max120 | false | 0.0162515825171 | 1.63030252406 | 2266206 | 13.923394431 | 1.12399755362 | 1..120 | 280399 | 408520 |
| measured_q8_high1_max120 | false | 0.0107610848326 | 1.07652164331 | 3587375 | 8.79564584132 | 0.710048433743 | 1..120 | 290205 | 309766 |
| measured_q16_high1_max120 | true | 0.00654730654389 | 0.653593498556 | 6558281 | 4.8112119624 | 0.388395983643 | 1..120 | 297643 | 282107 |
| measured_q32_high1_max120 | true | 0.00389547801346 | 0.388353703486 | 12723107 | 2.47999800678 | 0.200203456593 | 1..120 | 302953 | 276046 |
| measured_q64_high1_max120 | true | 0.00240315168259 | 0.239399351544 | 24650559 | 1.28002289928 | 0.103332747951 | 1..120 | 305837 | 266907 |
| measured_q16_high1_max3600 | true | 0.00682430929537 | 0.681340551979 | 6451890 | 4.89054835095 | 0.394800593315 | 1..600 | 296773 | 276460 |
| measured_q32_high1_max3600 | true | 0.003907015685 | 0.389506188269 | 12701669 | 2.48418377144 | 0.200541361927 | 1..300 | 302610 | 275381 |

## Interpretation

- This is a stochastic policy-level replay with a fixed seed.
- Passing `target_met=true` means the resulting measured schedule satisfies the exact accumulated-risk target for this replay.
- Failing policies are still useful as onboard fallback demonstrations, but not as certified replacements for the Chapter 3 schedule compiler.
- The current/delayed external schedules remain the risk-certified path because they are compiled against the full nu(t) estimate.
