# Model-to-RTL schedule replay certificate

| Strategy | Expected passes | Observed pass starts | Completed passes | Reads | Safe cycles | Mismatches | Failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed | 2160 | 2160 | 2160 | 17280 | 0 | 0 | 0 |
| adaptive | 1098 | 1098 | 1098 | 8784 | 0 | 0 | 0 |

The replay uses the model-generated schedule CSV files and converts their
period indices into RTL period update events. The controller is not given
the radiation/risk model; it only receives period indices.
