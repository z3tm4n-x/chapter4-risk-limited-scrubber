# Measured-error period estimator RTL report

This unit test verifies an autonomous onboard period-index estimator
driven only by SEC-DED corrected/DUE observations.

| Metric | Value |
|---|---:|
| final_period_index | 6 |
| updates | 6 |
| high_activity_events | 2 |
| quiet_relax_events | 1 |
| forced_safe_events | 2 |
| failures | 0 |

Interpretation:

- Quiet passes relax the scrub period toward larger period indices.
- High corrected-event activity accelerates scrubbing by lowering the period index.
- Any DUE forces the conservative safe period index.
- This is an onboard fallback strategy; it is not the exact-risk schedule compiler.
