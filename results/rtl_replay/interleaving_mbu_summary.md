# Interleaving MBU RTL experiment

The same physical 3-bit MBU is replayed with two logical mappings.

| Scenario | Physical multiplicity | Interleave depth | Corrected | DUE | Writes | Final DUE | Final SDC | Final dangerous | Failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D1_same_word | 3 | 1 | 1 | 0 | 1 | 0 | 1 | 1 | 0 |
| D3_split | 3 | 3 | 3 | 0 | 3 | 0 | 0 | 0 | 0 |

Interpretation:

- Without interleaving, the physical MBU maps into one SEC-DED codeword and leaves the guaranteed correction envelope.
- With interleaving depth 3, the same physical multiplicity maps to three single-bit codeword errors and is repaired by scrub writeback.
- SDC is reported only by golden-reference verification audit, not by online SEC-DED hardware.
