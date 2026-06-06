# Chapter 3 radiation-window fault replay summary

The same external fault stream is replayed against current and delayed
period-index schedules for each selected radiation window.

`detected_due_events` counts every online DUE pulse. `new_due_words` and
`persistent_due_detections` separate first observations from repeated
diagnostic load. `final_sdc_words` is a verification-only golden-reference
audit metric, not an online SEC-DED output.

| Strategy | Window | Passes | Reads | Writes | Corrected | DUE events | New DUE words | Persistent DUE | Final DUE | Final SDC | Final dangerous | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| current | quiet_background | 1470 | 11760 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| delayed_1h | quiet_background | 1470 | 11760 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| current | storm_rise | 15270 | 122160 | 5 | 5 | 14909 | 1 | 14908 | 1 | 1 | 2 | 0 |
| delayed_1h | storm_rise | 15300 | 122400 | 5 | 5 | 14939 | 1 | 14938 | 1 | 1 | 2 | 0 |
| current | storm_peak | 105600 | 844800 | 5 | 5 | 95757 | 1 | 95756 | 1 | 1 | 2 | 0 |
| delayed_1h | storm_peak | 105300 | 842400 | 5 | 5 | 98997 | 1 | 98996 | 1 | 1 | 2 | 0 |
| current | storm_decay | 5340 | 42720 | 5 | 5 | 4319 | 1 | 4318 | 1 | 1 | 2 | 0 |
| delayed_1h | storm_decay | 5490 | 43920 | 5 | 5 | 4529 | 1 | 4528 | 1 | 1 | 2 | 0 |
| current | tau_min_saturation | 100260 | 802080 | 5 | 5 | 99539 | 1 | 99538 | 1 | 1 | 2 | 0 |
| delayed_1h | tau_min_saturation | 98520 | 788160 | 5 | 5 | 97799 | 1 | 97798 | 1 | 1 | 2 | 0 |
| current | delayed_sensitive | 31800 | 254400 | 5 | 5 | 31439 | 1 | 31438 | 1 | 1 | 2 | 0 |
| delayed_1h | delayed_sensitive | 32790 | 262320 | 5 | 5 | 32429 | 1 | 32428 | 1 | 1 | 2 | 0 |
