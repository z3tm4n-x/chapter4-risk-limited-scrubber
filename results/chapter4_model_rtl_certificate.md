# Chapter 4 model-to-RTL certificate

This certificate aggregates the Chapter 3 five-year model schedules and
the Chapter 4 RTL window replay results.

## Series

| Metric | Value |
|---|---:|
| hours | 43824 |
| start | 2021-01-01T00:00:00Z |
| end | 2025-12-31T23:00:00Z |
| mean total nu, 1/hour | 7.07276729449 |
| CV^2 | 6.24295991773 |
| eta_const = 1 + CV^2 | 7.24295991773 |
| max total nu, 1/hour | 1193.96354958 |

## Five-year exact-risk schedules

| Strategy | P mission | E risk | Risk utilization | Pass count | Fixed/strategy gain | Tau range, s | Eta shape |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed | 0.00553465940419 | 0.00555003238058 | 0.552223573568 | 31553280 | 1 | 5..5 | 7.24295991773 |
| current | 0.00999993405782 | 0.0100502692452 | 0.999993372534 | 2547210 | 12.3873885545 | 1..120 | 1 |
| delayed_1h | 0.00999990177991 | 0.0100502366413 | 0.999990128469 | 2649330 | 11.9099092978 | 1..120 | 1.04935369403 |

## Fixed-candidate boundary

The best allowed fixed period is 5 s with risk utilization 0.552223573568.
The next fixed candidate, 10 s, is not allowed: risk utilization 1.10444650394.
Therefore fixed/adaptive gain is larger than the continuous 1+CV^2 bound because the fixed baseline is discretized.

## RTL window replay

| Strategy | Window | Model passes | RTL pass starts | Completed | Delta | Mismatches | Safe cycles | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| current | quiet_background | 1470 | 1470 | 1470 | 0 | 0 | 0 | 0 |
| delayed_1h | quiet_background | 1470 | 1470 | 1470 | 0 | 0 | 0 | 0 |
| current | storm_rise | 15270 | 15270 | 15270 | 0 | 0 | 0 | 0 |
| delayed_1h | storm_rise | 15300 | 15300 | 15300 | 0 | 0 | 0 | 0 |
| current | storm_peak | 105600 | 105600 | 105600 | 0 | 0 | 0 | 0 |
| delayed_1h | storm_peak | 105300 | 105300 | 105300 | 0 | 0 | 0 | 0 |
| current | storm_decay | 5340 | 5340 | 5340 | 0 | 0 | 0 | 0 |
| delayed_1h | storm_decay | 5490 | 5490 | 5490 | 0 | 0 | 0 | 0 |
| current | tau_min_saturation | 100260 | 100260 | 100260 | 0 | 0 | 0 | 0 |
| delayed_1h | tau_min_saturation | 98520 | 98520 | 98520 | 0 | 0 | 0 | 0 |
| current | delayed_sensitive | 31800 | 31800 | 31800 | 0 | 0 | 0 | 0 |
| delayed_1h | delayed_sensitive | 32790 | 32790 | 32790 | 0 | 0 | 0 | 0 |

## Verdict

- Five-year model schedules satisfy the mission-risk target: `true`.
- RTL window replay matches model pass counts with zero mismatches: `true`.
- The RTL controller receives only period indices; it does not receive nu(t), risk values, or the radiation model.
