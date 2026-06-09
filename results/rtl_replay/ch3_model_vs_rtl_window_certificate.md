# Chapter 3 model-to-RTL window replay certificate

The RTL controller receives only `period_index` updates. It does not receive
`nu(t)`, risk values, or the radiation model.

| Strategy | Window | Expected passes | RTL pass starts | Completed passes | Reads | Safe cycles | Mismatches | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| current | quiet_background | 1470 | 1470 | 1470 | 5880 | 0 | 0 | 0 |
| delayed_1h | quiet_background | 1470 | 1470 | 1470 | 5880 | 0 | 0 | 0 |
| forecast | quiet_background | 1470 | 1470 | 1470 | 5880 | 0 | 0 | 0 |
| current | storm_rise | 15270 | 15270 | 15270 | 61080 | 0 | 0 | 0 |
| delayed_1h | storm_rise | 15300 | 15300 | 15300 | 61200 | 0 | 0 | 0 |
| forecast | storm_rise | 17340 | 17340 | 17340 | 69360 | 0 | 0 | 0 |
| current | storm_peak | 105600 | 105600 | 105600 | 422400 | 0 | 0 | 0 |
| delayed_1h | storm_peak | 105300 | 105300 | 105300 | 421200 | 0 | 0 | 0 |
| forecast | storm_peak | 107460 | 107460 | 107460 | 429840 | 0 | 0 | 0 |
| current | storm_decay | 5340 | 5340 | 5340 | 21360 | 0 | 0 | 0 |
| delayed_1h | storm_decay | 5490 | 5490 | 5490 | 21960 | 0 | 0 | 0 |
| forecast | storm_decay | 5430 | 5430 | 5430 | 21720 | 0 | 0 | 0 |
| current | tau_min_saturation | 100260 | 100260 | 100260 | 401040 | 0 | 0 | 0 |
| delayed_1h | tau_min_saturation | 98520 | 98520 | 98520 | 394080 | 0 | 0 | 0 |
| forecast | tau_min_saturation | 100680 | 100680 | 100680 | 402720 | 0 | 0 | 0 |
| current | delayed_sensitive | 31800 | 31800 | 31800 | 127200 | 0 | 0 | 0 |
| delayed_1h | delayed_sensitive | 32790 | 32790 | 32790 | 131160 | 0 | 0 | 0 |
| forecast | delayed_sensitive | 32790 | 32790 | 32790 | 131160 | 0 | 0 | 0 |
