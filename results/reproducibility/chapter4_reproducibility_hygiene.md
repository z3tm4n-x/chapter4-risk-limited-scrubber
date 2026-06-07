# Chapter 4 reproducibility hygiene audit

This audit checks that transient runtime logs are not tracked as durable
evidence artifacts.

Tracked evidence remains in summary/certificate `csv`, `md`, and `json`
files. Runtime `.log` files are regenerated locally and ignored.

## Metrics

| Metric | Value |
|---|---:|
| tracked_transient_log_count | 0 |
| rtl_replay_log_ignored | true |
| synthesis_log_ignored | true |
| summary_csv_tracked_allowed | true |
| summary_md_tracked_allowed | true |
| summary_json_tracked_allowed | true |
| hygiene_pass | true |

## Tracked transient logs

- none

## Interpretation

- Full Chapter 4 reproduction may regenerate raw logs.
- Regenerated logs should not by themselves dirty the git worktree.
- Durable evidence is carried by committed summary/certificate artifacts.
