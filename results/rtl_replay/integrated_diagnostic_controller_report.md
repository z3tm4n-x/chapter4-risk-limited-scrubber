# Integrated diagnostic controller RTL report

This report verifies that the top-level adaptive scrub controller exposes
diagnostic-supervisor flags from actual SEC-DED scrub events.

| Metric | Value |
|---|---:|
| passes | 5 |
| reads | 32 |
| writes | 1 |
| corrected | 1 |
| due | 3 |
| diag_alert | 1 |
| diag_danger | 1 |
| diag_persistent | 1 |
| diag_out_of_envelope | 1 |
| diag_force_conservative | 1 |
| diag_alert_events | 1 |
| diag_new_due_words | 1 |
| diag_persistent_due | 2 |
| failures | 0 |

Interpretation:

- Corrected SEC-DED events are visible to the integrated diagnostic path.
- Same-word persistent DUE raises danger and persistent-DUE diagnostics.
- `diag_force_conservative` is a system-level request; the controller still does not compute the radiation model.
