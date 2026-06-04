# Schedule evidence pack

This evidence pack demonstrates the model-side schedule output that the Chapter 4
RTL controller will consume as an external `period_index` stream.

## Geometry and target

| Quantity | Value |
|---|---:|
| word_bits | 39 |
| codeword_count | 4096 |
| physical_bits | 159744 |
| alpha | 1.189410490601e-04 |
| target_probability | 0.001 |
| target_e | 0.00100050033358 |

The geometry is intentionally small enough for later RTL replay experiments. The
mathematical functions are parameterized and also support the full dissertation
geometry.

## Allowed period set

`[2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]` seconds.

The adaptive schedule uses conservative floor-down rounding:

`tau_impl = max{tau in T : tau <= tau_calc}`

with clamping to the minimum and maximum allowed period.

## Strategy comparison

| Strategy | Exact E_acc | P_mission | Pass count | Risk utilization | Tau range, s |
|---|---:|---:|---:|---:|---:|
| fixed_allowed_10s | 0.000893037195719 | 0.000892638556677 | 2160.000000 | 0.892591 | 10..10 |
| adaptive_current_exact_floor_down | 0.000951514916541 | 0.000951062369769 | 1098.000000 | 0.951039 | 10..600 |

## Main result

The implementable adaptive schedule reduces the full-pass count by a factor of:

**1.967213**

relative to the largest fixed allowed period satisfying the same exact-risk
target.

## Generated files

- `period_table.csv`
- `schedule_fixed.csv`
- `schedule_adaptive.csv`
- `schedule_summary.csv`
- `schedule_demo_certificate.json`
