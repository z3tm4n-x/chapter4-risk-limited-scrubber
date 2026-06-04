# Period scheduler RTL report

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
