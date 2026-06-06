# Chapter 4 overhead/gain certificate

This certificate combines the Chapter 3 five-year schedule gain with
the Chapter 4 RTL resource estimates.

## Schedule benefit

| Strategy | Pass count | P mission | Risk utilization | Fixed/strategy gain | Pass reduction vs fixed |
|---|---:|---:|---:|---:|---:|
| fixed | 31553280 | 0.00553465940419 | 0.552223573568 | 1 | 0 |
| current adaptive | 2547210 | 0.00999993405782 | 0.999993372534 | 12.3873885545 | 0.919272734879 |
| delayed 1h adaptive | 2649330 | 0.00999990177991 | 0.999990128469 | 11.9099092978 | 0.916036304308 |

## XC7 resource estimates

| Component | LUT | FF | Cells | Meaning |
|---|---:|---:|---:|---|
| SEC-DED encoder | 32 | 0 | 104 | ECC encode datapath |
| SEC-DED decoder | 143 | 0 | 324 | ECC decode/correction datapath |
| Period scheduler | 162 | 167 | 720 | External period-index endpoint |
| Scrub pass engine | 168 | 171 | 861 | Full memory pass and writeback |
| Diagnostic supervisor | 247 | 212 | 962 | Alert/DUE/out-of-envelope flags |
| External adaptive controller | 444 | 550 | 2385 | Chapter 3 schedule endpoint |
| Measured-error estimator | 139 | 104 | 511 | Onboard period estimator only |
| Measured-error controller | 603 | 654 | 2853 | Integrated onboard fallback |

## Incremental measured-mode cost

| Comparison | Delta LUT | Delta FF | Delta LUT % | Delta FF % |
|---|---:|---:|---:|---:|
| measured_error_scrub_controller - adaptive_scrub_controller | 159 | 104 | 35.8108 | 18.9091 |

## Interpretation

- The external current adaptive schedule reduces pass count by `12.3874x` relative to the best allowed fixed schedule.
- The delayed one-hour adaptive schedule reduces pass count by `11.9099x`.
- The measured-error onboard fallback costs `+159` LUT and `+104` FF over the external-period endpoint.
- These are synthesis estimates only; they do not establish timing closure or Fmax.
