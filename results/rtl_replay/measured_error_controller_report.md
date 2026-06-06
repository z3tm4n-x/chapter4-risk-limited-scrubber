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
