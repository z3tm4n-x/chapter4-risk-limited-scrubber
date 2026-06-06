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
