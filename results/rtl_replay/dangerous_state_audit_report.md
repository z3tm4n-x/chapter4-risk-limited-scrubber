# Dangerous-state audit RTL report

The integrated controller was run against a memory containing a correctable
single-bit corruption, a detected double-bit DUE, and a triple-bit corruption
outside the SEC-DED correction guarantee.

| Metric | Value |
|---|---:|
| completed passes | 5 |
| memory reads | 39 |
| correction writes | 2 |
| online corrected events | 2 |
| online detected DUE events | 5 |
| final uncorrectable words | 1 |
| final SDC words | 1 |
| final dangerous words | 2 |
| failures | 0 |

Interpretation:

- Single-bit accumulated errors are corrected by the scrub pass.
- Detected double-bit states are reported as DUE but are not repaired.
- A triple-bit state can be outside the SEC-DED guarantee and become SDC.
- `final_sdc_words` is obtained by a verification-only golden-reference audit,
  not by an online SEC-DED hardware flag.
- This is the Chapter 4 distinction between online diagnostics and the broader
  dangerous-state class used in Chapter 2.
