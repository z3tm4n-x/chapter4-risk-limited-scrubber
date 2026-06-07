# Tau-min hardware feasibility certificate

This certificate connects the Chapter 3 minimum scrub period to an
explicit hardware service-rate model.

It is not a place-and-route timing report. It only checks whether one
complete scrub pass can fit inside the configured minimum period.

## Parameters and results

| Metric | Value |
|---|---:|
| codeword_count | 1935832 |
| codeword_bits | 39 |
| protected_bits | 75497448 |
| scrub_clock_hz | 100000000.0 |
| cycles_per_word | 1.0 |
| pipeline_overhead_cycles | 4.0 |
| pass_cycles | 1935836.0 |
| pass_time_seconds | 0.01935836 |
| effective_words_per_second | 100000000.0 |
| effective_bits_per_second | 3900000000.0 |
| target_tau_min_seconds | 1.0 |
| tau_min_margin | 51.65726848761982 |
| tau_min_feasible | true |

## Interpretation

- One complete pass over `1935832` SEC-DED codewords takes `0.01935836` s under the configured service-rate model.
- The Chapter 3 minimum period is `1` s.
- The resulting tau-min margin is `51.6572684876`.
- Tau-min feasibility verdict: `true`.

If the memory subsystem provides a lower effective scrub bandwidth,
the configuration must be updated and the residual-risk boundary
must be recomputed.
