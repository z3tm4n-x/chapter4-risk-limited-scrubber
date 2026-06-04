# SEC-DED exhaustive RTL report

The SEC-DED encoder/decoder was checked over a representative data-pattern set.

| Check | Count |
|---|---:|
| no-error decode checks | 8 |
| single-bit corrections | 312 |
| double-bit DUE detections | 5928 |
| sampled triple-bit patterns | 24 |
| sampled triple-bit detected DUE | 8 |
| sampled triple-bit SDC outcomes | 16 |
| failures | 0 |

Interpretation:

- Every single-bit corruption in the 39-bit codeword is corrected.
- Every double-bit corruption is detected as uncorrectable.
- Triple-bit corruptions are outside the guaranteed SEC-DED correction
  capability. The testbench records whether they become detected DUE or SDC
  relative to the golden data; SDC accounting is a verification-audit function,
  not an online SEC-DED guarantee.
