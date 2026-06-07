# RTL timebase contract

The Chapter 3 schedule compiler emits period indices for a table of
physical scrub periods. The RTL scheduler does not count long physical
periods in raw implementation-clock cycles.

The scheduler uses a coarse `time_tick` input:

- `clk` is the implementation clock.
- `time_tick` is the timebase event used by the period scheduler.
- Legacy `PERIOD*_CYCLES` parameter names are kept for compatibility, but
  are interpreted by the scheduler as period ticks.
- RTL replay compresses time by asserting `time_tick` every simulation clock.
- A real deployment may drive `time_tick` from a 1 Hz timer or another
  configured time quantum.
- The tau-min certificate separately checks that one full scrub pass fits
  inside the minimum physical period.

This contract avoids representing long physical periods, such as 3600 s, as
large raw system-clock counts.
