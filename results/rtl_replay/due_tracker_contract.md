# Limited DUE tracker contract

The diagnostic supervisor does not implement a full `DEPTH`-bit DUE-history
bitmap. Persistent-DUE detection is implemented with a bounded associative
tracker.

Contract:

- A tracked DUE address observed for the first time increments `new_due_word_count`.
- A tracked DUE address observed again raises `persistent_due_flag`.
- Persistent DUE can raise `out_of_envelope_flag` and therefore
  `force_conservative`.
- If the bounded tracker is exhausted, the supervisor raises
  `out_of_envelope_flag` conservatively rather than allocating an unbounded
  per-word bitmap.
- The tracker is diagnostic evidence, not part of the Chapter 2/3 exact-risk
  computation.

This keeps diagnostic state bounded when the protected memory depth is scaled
to the dissertation geometry.
