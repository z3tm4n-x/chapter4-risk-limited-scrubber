# Constant-VMR negative-binomial counterexample

This artifact explains why pass-level `NB(mean=lambda, var=phi*lambda)`
is not used as the primary burst-stress model for the scrub-period controller.

For this model, the rare-regime accumulated-risk penalty is

`Delta E_NB = alpha * (phi - 1) * integral_nu_dt`,

which is independent of scrub period. Therefore, within this constant-VMR model, even an always-`tau_min`
schedule cannot remove the overdispersion term.

## Constants

- alpha: `2.51664139054e-07`
- integral nu dt: `309956.953914`
- target E: `0.0100503358535`
- Delta E per `(phi-1)`: `0.0780050499504`
- Delta utilization per `(phi-1)`: `7.76143713876`

## Budget crossing thresholds

| Scenario | Baseline utilization | phi at budget | Interpretation |
|---|---:|---:|---|
| external_current_adaptive | 0.999993372534 | 1.0000008539 | Current exact-risk external adaptive schedule; already near full budget. |
| measured_q16_high1_max3600_seed_mean | 0.681094456074 | 1.04108846573 | Canonical measured-error fallback policy, seed-sweep mean. |
| always_tau_min_1s | 0.110444748612 | 1.1146121827 | Always run at tau_min=1 s; analytic conservative floor within the Poisson model. |

## Phi grid diagnostic

| Scenario | phi | Baseline util. | NB penalty util. | Total util. | Verdict |
|---|---:|---:|---:|---:|---|
| external_current_adaptive | 1 | 0.999993372534 | 0 | 0.999993372534 | pass |
| external_current_adaptive | 1.04 | 0.999993372534 | 0.31045748555 | 1.31045085808 | fail |
| external_current_adaptive | 1.13 | 0.999993372534 | 1.00898682804 | 2.00898020057 | fail |
| external_current_adaptive | 2 | 0.999993372534 | 7.76143713876 | 8.76143051129 | fail |
| external_current_adaptive | 4 | 0.999993372534 | 23.2843114163 | 24.2843047888 | fail |
| external_current_adaptive | 8 | 0.999993372534 | 54.3300599713 | 55.3300533439 | fail |
| external_current_adaptive | 16 | 0.999993372534 | 116.421557081 | 117.421550454 | fail |
| measured_q16_high1_max3600_seed_mean | 1 | 0.681094456074 | 0 | 0.681094456074 | pass |
| measured_q16_high1_max3600_seed_mean | 1.04 | 0.681094456074 | 0.31045748555 | 0.991551941624 | pass |
| measured_q16_high1_max3600_seed_mean | 1.13 | 0.681094456074 | 1.00898682804 | 1.69008128411 | fail |
| measured_q16_high1_max3600_seed_mean | 2 | 0.681094456074 | 7.76143713876 | 8.44253159483 | fail |
| measured_q16_high1_max3600_seed_mean | 4 | 0.681094456074 | 23.2843114163 | 23.9654058724 | fail |
| measured_q16_high1_max3600_seed_mean | 8 | 0.681094456074 | 54.3300599713 | 55.0111544274 | fail |
| measured_q16_high1_max3600_seed_mean | 16 | 0.681094456074 | 116.421557081 | 117.102651537 | fail |
| always_tau_min_1s | 1 | 0.110444748612 | 0 | 0.110444748612 | pass |
| always_tau_min_1s | 1.04 | 0.110444748612 | 0.31045748555 | 0.420902234162 | pass |
| always_tau_min_1s | 1.13 | 0.110444748612 | 1.00898682804 | 1.11943157665 | fail |
| always_tau_min_1s | 2 | 0.110444748612 | 7.76143713876 | 7.87188188737 | fail |
| always_tau_min_1s | 4 | 0.110444748612 | 23.2843114163 | 23.3947561649 | fail |
| always_tau_min_1s | 8 | 0.110444748612 | 54.3300599713 | 54.4405047199 | fail |
| always_tau_min_1s | 16 | 0.110444748612 | 116.421557081 | 116.53200183 | fail |

## Interpretation

- The constant-VMR NB model imposes overdispersion at arbitrarily small time scales.
- Its accumulated-risk penalty is independent of the scrub period.
- This makes the model unsuitable as the primary robustness test for a scrub-period controller.
- The primary burst-stress model should instead use a finite-correlation rate process,
  such as shot-noise or piecewise-gamma rate bursts normalized to the hourly Chapter 3 series.
