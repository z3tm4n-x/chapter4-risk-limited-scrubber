# Rate-burst stress boundary summary

This file summarizes the finite-correlation rate-burst stress certificate in
`rate_burst_stress_report.md`.

## Model

The stress model applies a piecewise-gamma sub-hourly rate multiplier to the
Chapter 3 hourly upset-rate series. The multiplier is normalized inside each
hour, so the hourly mean rate is preserved exactly.

The table reports both:

- requested CV^2: the gamma-generator dispersion parameter before per-hour normalization;
- achieved CV^2 mean: the mean normalized within-hour multiplier CV^2 over the sampled mission paths.

## Measured autonomous policy boundary

Policy: `measured_q16_high1_max3600`.

Admissibility rule:

`target_met_fraction >= 0.99 and risk_utilization_p99 <= 1.0`.

| Burst duration | Last sampled-admissible case | First sampled-non-admissible case |
|---:|---|---|
| 300 s | requested CV^2 = 0.50, achieved CV^2 mean = 0.44016832606, p99 utilization = 0.967135542104 | requested CV^2 = 0.60, achieved CV^2 mean = 0.524087347576, p99 utilization = 1.01230638604 |
| 600 s | requested CV^2 = 0.70, achieved CV^2 mean = 0.522748302902, p99 utilization = 0.997473473498 | requested CV^2 = 0.75, achieved CV^2 mean = 0.555316361014, p99 utilization = 1.03539863846 |
| 900 s | requested CV^2 = 0.75, achieved CV^2 mean = 0.47398297239, p99 utilization = 0.974468904803 | requested CV^2 = 0.85, achieved CV^2 mean = 0.525870123946, p99 utilization = 1.01317229864 |
| 1800 s | requested CV^2 = 1.00, achieved CV^2 mean = 0.333103141457, p99 utilization = 0.910691024065 | requested CV^2 = 2.00, achieved CV^2 mean = 0.499761247497, p99 utilization = 1.2489793072 |

## Safety-floor baseline

The `always_tau_min_1s` expected-risk baseline remains sampled-admissible for
the entire tested finite-correlation grid. Its maximum utilization over the
final grid is:

`0.207125140825`.

## Interpretation

The measured autonomous fallback has a finite robustness region against
finite-correlation rate bursts. The admissible boundary shifts toward lower
requested burst dispersion as burst duration decreases.

The `tau_min=1 s` baseline remains safe on the tested finite-correlation grid,
which supports interpreting the lower period bound as a safety floor for
temporally resolvable accumulated-error bursts.

These results do not claim safety against arbitrary unbounded burstiness or
instantaneous MBU/MCU mechanisms.
