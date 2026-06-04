# Adaptive scrub controller RTL report

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
