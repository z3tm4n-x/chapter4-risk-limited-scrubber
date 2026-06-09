# Interleaving g(D) feasibility case

This report instantiates the Chapter-2 interleaving handoff for the
Chapter-3 five-year upset-rate series.

The dangerous instantaneous budget share is computed rather than swept:

`p_m = (1 - s) s^(m-1)`, `s = (mean_m - 1) / mean_m`, `g_D = s^D`,
and `rho_D = g_D N_events / E_target`.

This is a Chapter-2-consistent limiting design model. It is not a
universal upper bound for arbitrary physical placement; a concrete memory
macro should refine `h_m(D)` from topology or test data.

## Parameters

| Quantity | Value |
|---|---:|
| target probability | 0.01 |
| target risk E | 0.0100503358535 |
| codeword count | 1935832 |
| word/codeword bits | 39 |
| total nu integral | 309956.953914 |
| tau_min, s | 1 |
| E_acc(tau_min) | 0.00111000681681 |
| rho_crit = 1 - E_acc(tau_min)/E_target | 0.889555251388 |
| figure | skipped: matplotlib unavailable: No module named 'matplotlib' |

## Minimum selectable interleaving depth

| Mean multiplicity | Minimum selectable D | rho_D at minimum | Pass count at minimum |
|---:|---:|---:|---:|
| 1.5 | 16 | 0.477627665953 | 5434830 |
| 2 | 25 | 0.459558625776 | 5222760 |
| 3 | 41 | 0.61980907876 | 7903980 |

## Main case: mean multiplicity = 2

| D | g_D | rho_D | Status | Schedule passes | Mean tau, s | Tau range, s |
|---:|---:|---:|---|---:|---:|---:|
| 1 | 0.5 | 7710114.32931 | architecture_change_required | - | - | - |
| 2 | 0.25 | 3855057.16465 | architecture_change_required | - | - | - |
| 4 | 0.0625 | 963764.291163 | architecture_change_required | - | - | - |
| 8 | 0.00390625 | 60235.2681977 | architecture_change_required | - | - | - |
| 12 | 0.000244140625 | 3764.70426236 | architecture_change_required | - | - | - |
| 16 | 1.52587890625e-05 | 235.294016397 | architecture_change_required | - | - | - |
| 20 | 9.53674316406e-07 | 14.7058760248 | architecture_change_required | - | - | - |
| 24 | 5.96046447754e-08 | 0.919117251552 | bandwidth_or_tau_min_insufficient | - | - | - |
| 25 | 2.98023223877e-08 | 0.459558625776 | scrub_period_selectable | 5222760 | 48.4648594378 | 1..120 |
| 28 | 3.72529029846e-09 | 0.057444828222 | scrub_period_selectable | 2699940 | 84.325894487 | 1..120 |
| 32 | 2.32830643654e-10 | 0.00359030176387 | scrub_period_selectable | 2556180 | 87.224968054 | 1..120 |
| 36 | 1.45519152284e-11 | 0.000224393860242 | scrub_period_selectable | 2547780 | 87.406375502 | 1..120 |
| 40 | 9.09494701773e-13 | 1.40246162651e-05 | scrub_period_selectable | 2547270 | 87.4173284045 | 1..120 |
| 41 | 4.54747350886e-13 | 7.01230813257e-06 | scrub_period_selectable | 2547270 | 87.4173284045 | 1..120 |
| 44 | 5.68434188608e-14 | 8.76538516571e-07 | scrub_period_selectable | 2547210 | 87.4180129609 | 1..120 |
| 48 | 3.5527136788e-15 | 5.47836572857e-08 | scrub_period_selectable | 2547210 | 87.4180129609 | 1..120 |
| 64 | 5.42101086243e-20 | 8.35932270595e-13 | scrub_period_selectable | 2547210 | 87.4180129609 | 1..120 |

## Interpretation

- `rho_D >= 1` means the instantaneous component alone consumes or exceeds
  the full mission-risk budget; architectural mitigation is required.
- `rho_D > rho_crit` means a residual accumulated-risk budget remains, but
  even continuous operation at `tau_min` is insufficient.
- `rho_D < rho_crit` means a scrub-period schedule can be selected for the
  residual accumulated-risk budget.
- Thus the minimum interleaving depth is set by the stricter realizability
  gate `rho_D < rho_crit`, not merely by `rho_D < 1`.
