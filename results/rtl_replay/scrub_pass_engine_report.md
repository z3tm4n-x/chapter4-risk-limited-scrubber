# Scrub pass engine RTL report

One complete SEC-DED scrub pass was executed over a protected memory model.

| Check | Value |
|---|---:|
| protected depth | 8 |
| completed passes | 1 |
| memory reads | 8 |
| correction writes | 1 |
| corrected single-bit errors | 1 |
| detected uncorrectable errors | 1 |
| wait cycles until pass_done | 26 |
| failures | 0 |

Interpretation:

- The pass engine reads every protected codeword exactly once per pass.
- A correctable single-bit corruption is written back as the restored codeword.
- A detected double-bit error is reported as DUE and is not falsely repaired.
- This block implements the Chapter 4 per-word scrub operation; period
  scheduling is handled separately by the period scheduler.
