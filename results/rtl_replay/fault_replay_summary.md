# Fault-event replay summary

| Strategy | Passes | Reads | Writes | Corrected | DUE events | Final DUE words | Final SDC words | Final dangerous | Failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed | 2160 | 17280 | 5 | 5 | 2090 | 1 | 1 | 2 | 0 |
| adaptive | 1098 | 8784 | 5 | 5 | 1096 | 1 | 1 | 2 | 0 |

The same external fault stream is replayed against fixed and adaptive
period-index schedules. Faults are supplied as data, not hardcoded in
the RTL controller.
