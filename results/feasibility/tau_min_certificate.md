# Tau-min hardware feasibility certificate

This certificate connects the Chapter 3 minimum scrub period to two
explicit service-rate models:

- a controller-core model, used to show that the RTL scrub core is not
  the bottleneck;
- a memory-interface-limited model, used as the binding design constraint
  for the Chapter 3/4 choice `tau_min = 1 s`.

It is not a place-and-route timing report. Vivado OOC timing evidence is
reported separately.

## Scenario results

| Scenario | Service model | Effective words/s | Effective bits/s | Pass time, s | Tau-min margin | Feasible |
|---|---|---:|---:|---:|---:|---:|
| controller_core_ooc | clocked_codeword_service | 100000000 | 3900000000 | 0.01935836 | 51.6572684876 | true |
| memory_interface_limited | memory_interface_bandwidth | 6564102.5641 | 256000000 | 0.294912515625 | 3.39083608534 | true |

## Binding interpretation

- The primary binding scenario is `memory_interface_limited`.
- Under the binding scenario, one complete pass over `1935832`
  SEC-DED codewords takes `0.294912515625` s.
- The Chapter 3 minimum period is `1` s.
- The binding tau-min margin is `3.39083608534`.
- Tau-min feasibility verdict: `true`.

## Design conclusion

- The controller-core service model gives a pass time of `0.01935836` s
  and a margin of `51.6572684876`.
- The memory-interface-limited model gives a pass time of `0.294912515625` s
  and a margin of `3.39083608534`.
- Therefore the scrub controller logic is not the limiting factor for
  `tau_min`; the binding constraint is the sustained memory-interface
  service bandwidth reserved for scrub traffic.
