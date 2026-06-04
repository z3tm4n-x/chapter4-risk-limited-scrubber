# Protection-envelope feasibility evidence pack

This report demonstrates the Chapter 2 go/no-go handoff before the
Chapter 3 scrub-period scheduler is used.

The cases are illustrative. Their purpose is to verify the logic:

1. instant MBU risk can consume the budget;
2. residual budget can remain positive while tau_min is still insufficient;
3. if both checks pass, scrub-period selection is meaningful.

| Case | Status | g_D | E_inst | E_residual | E_acc(tau_min) | Slack |
|---|---|---:|---:|---:|---:|---:|
| scrub_period_selectable_D3 | scrub_period_selectable | 0 | 0 | 0.00100050033358 | 8.93047891737e-05 | 0.00091119554441 |
| architecture_change_required_D1 | architecture_change_required | 0.009 | 0.009 | -0.00799949966642 | 8.93047891737e-05 | -0.00808880445559 |
| bandwidth_or_tau_min_insufficient | bandwidth_or_tau_min_insufficient | 1e-07 | 0.0001 | 0.000900500333584 | 0.00396466689616 | -0.00306416656258 |

Interpretation:

- `architecture_change_required`: decreasing the scrub period does not solve
  the problem because the instant component already exceeds the budget.
- `bandwidth_or_tau_min_insufficient`: instant risk is acceptable, but even
  continuous operation at tau_min cannot fit the accumulated-risk residual.
- `scrub_period_selectable`: the design point can be handed to the Chapter 3
  schedule compiler.
