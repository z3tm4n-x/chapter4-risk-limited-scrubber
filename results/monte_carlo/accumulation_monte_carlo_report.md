# Accumulated-risk Monte Carlo validation

This report validates the accumulated dangerous-state kernel by direct
random placement of independent bit errors over the dissertation memory
geometry. The test uses accelerated lambda values where collisions are
observable in finite Monte Carlo time.

## Geometry

| Quantity | Value |
|---|---:|
| word_bits | 39 |
| codeword_count | 1935832 |
| physical_bits | 75497448 |
| alpha | 2.516641390536e-07 |
| seed | 20260605 |

## Results

| Lambda | Trials | Empirical q | Exact q | Quadratic q | Empirical/exact rel. err. | Quadratic/exact rel. err. | z-score | Pass |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 150000 | 0.000526666666667 | 0.000628952196389 | 0.000629160347634 | 0.16262846415 | 0.000330949229522 | -1.58011111243 | true |
| 100 | 120000 | 0.00248333333333 | 0.00251339528886 | 0.00251664139054 | 0.0119606954215 | 0.00129152055522 | -0.207981121863 | true |
| 200 | 80000 | 0.009775 | 0.0100154161226 | 0.0100665655621 | 0.0240046064622 | 0.00510707083366 | -0.68290433112 | true |
| 300 | 60000 | 0.0217333333333 | 0.0223930219985 | 0.0226497725148 | 0.0294595640184 | 0.0114656483783 | -1.09213455271 | true |

## Interpretation

- `q_acc_exact(lambda)` agrees with direct random placement within the configured 4-sigma statistical gate.
- The quadratic kernel is close in the low-lambda region and increasingly conservative as lambda grows.
- Working mission lambdas are much smaller than these accelerated validation cases; direct observation there would be impractical.
- Overall Monte Carlo pass: `true`.
