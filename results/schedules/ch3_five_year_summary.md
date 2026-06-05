# Chapter 3 five-year schedule summary

This report is generated from `data/ch3_five_year_upsets.csv` and the
main Chapter 3 configuration.

## Series metrics

| Metric | Value |
|---|---:|
| hours | 43824 |
| mean_nu_per_hour | 7.07276729449 |
| cv2 | 6.24295991773 |
| eta_const = 1 + CV^2 | 7.24295991773 |
| max_nu_per_hour | 1193.96354958 |

## Strategies

| Strategy | E risk | P mission | Pass count | Fixed/strategy gain | Tau range, s | Eta shape |
|---|---:|---:|---:|---:|---:|---:|
| fixed | 0.00555003238058 | 0.00553465940419 | 31553280 | 1 | 5..5 | 7.24295991773 |
| current | 0.0100502692452 | 0.00999993405782 | 2547210 | 12.3873885545 | 1..120 | 1 |
| delayed_1h | 0.0100502366413 | 0.00999990177991 | 2649330 | 11.9099092978 | 1..120 | 1.04935369403 |
