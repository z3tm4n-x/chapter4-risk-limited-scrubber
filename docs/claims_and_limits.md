# Claims and limits

## Claimed

- The Chapter 3 implementable schedule can be executed by a finite-state RTL
  scrub controller.
- The period index controls the interval between checks of the same codeword.
- SEC-DED single-bit errors are corrected and written back.
- Detected uncorrectable states are reported.
- Stale external control causes a conservative fallback period.
- Post-run verification accounts for final detected DUE and final SDC.

## Not claimed

- The RTL controller does not validate physical MBU probabilities p_m or mapping
  probabilities h_m^(D).
- The RTL controller does not compute the radiation model.
- SEC-DED does not guarantee online detection of all states with three or more
  corrupted bits.
- Post-run SDC audit is a verification metric, not an online hardware output.
- Yosys-only synthesis is not timing closure and does not establish Fmax.
