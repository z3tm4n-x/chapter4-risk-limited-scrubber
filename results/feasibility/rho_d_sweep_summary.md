# rho_D residual-budget sweep

This sweep demonstrates the Chapter 2 feasibility handoff for the
Chapter 3 five-year series.

| Quantity | Value |
|---|---:|
| target probability | 0.01 |
| target risk E | 0.0100503358535 |
| tau_min, s | 1 |
| E_acc(tau_min) | 0.00111000681681 |
| P_acc(tau_min) | 0.00110939098712 |
| rho_crit = 1 - E_acc(tau_min)/E_target | 0.889555251388 |

## Sweep

| rho_D | Status | E_residual | Slack after tau_min | tau_min/residual utilization | Schedule passes | Tau range, s | Saturated tau_min |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | scrub_period_selectable | 0.0100503358535 | 0.00894032903669 | 0.110444748612 | 2547210 | 1..120 | true |
| 0.25 | scrub_period_selectable | 0.00753775189013 | 0.00642774507332 | 0.147259664817 | 3461040 | 1..120 | true |
| 0.5 | scrub_period_selectable | 0.00502516792675 | 0.00391516110994 | 0.220889497225 | 5715990 | 1..120 | true |
| 0.75 | scrub_period_selectable | 0.00251258396338 | 0.00140257714656 | 0.44177899445 | 13830480 | 1..30 | true |
| 0.85 | scrub_period_selectable | 0.00150755037803 | 0.000397543561214 | 0.736298324083 | 36906120 | 1..10 | true |
| 0.88 | scrub_period_selectable | 0.00120604030242 | 9.60334856091e-05 | 0.920372905104 | 79052400 | 1..5 | true |
| 0.889 | scrub_period_selectable | 0.00111558727974 | 5.58046292762e-06 | 0.994997735248 | 140815800 | 1..2 | true |
| 0.8895 | scrub_period_selectable | 0.00111056211181 | 5.55295000872e-07 | 0.999499987443 | 155694600 | 1..2 | true |
| 0.88955 | scrub_period_selectable | 0.00111005959502 | 5.27782081971e-08 | 0.999952454617 | 157554000 | 1..2 | true |
| 0.89 | bandwidth_or_tau_min_insufficient | 0.00110553694389 | -4.46987292588e-06 | 1.0040431692 | - | - | - |
| 0.9 | bandwidth_or_tau_min_insufficient | 0.00100503358535 | -0.000104973231461 | 1.10444748612 | - | - | - |
| 0.95 | bandwidth_or_tau_min_insufficient | 0.000502516792675 | -0.000607490024136 | 2.20889497225 | - | - | - |
| 0.99 | bandwidth_or_tau_min_insufficient | 0.000100503358535 | -0.00100950345828 | 11.0444748612 | - | - | - |
| 1 | architecture_change_required | 0 | -0.00111000681681 | inf | - | - | - |

Interpretation:

- Below rho_crit, a scrub schedule can be selected from the residual accumulated-risk budget.
- Near rho_crit, the schedule is forced toward tau_min saturation.
- Above rho_crit, even continuous operation at tau_min cannot satisfy the residual budget; the system must escalate.
- This computation is model-side evidence for the out-of-envelope flag implemented by the diagnostic supervisor.
