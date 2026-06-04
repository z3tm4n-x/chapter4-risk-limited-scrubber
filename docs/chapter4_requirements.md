# Chapter 4 hardware requirements

## Scope

The controller is an execution mechanism for the implementable schedule obtained
from the Chapter 3 procedure. It is not a radiation model and does not estimate
the physical environment inside RTL.

## Requirements

REQ-001. The controller shall perform a complete sequential pass over the
protected memory region.

REQ-002. The hardware period shall mean the interval between two checks of the
same codeword, not merely an idle delay after a pass.

REQ-003. The controller shall accept an external period index or level produced
by the model-side schedule compiler.

REQ-004. The controller shall not compute nu(t), g_D, E_inst, E_residual, or any
other radiation-risk quantity in RTL.

REQ-005. For each protected word, the controller shall read the SEC-DED codeword,
decode it, correct a detected single-bit error, and write back the corrected
codeword.

REQ-006. The controller shall report detected uncorrectable SEC-DED states.

REQ-007. The controller shall expose diagnostic counters for passes, reads,
writes, corrected errors, detected uncorrectable errors, and conservative-mode
activity.

REQ-008. The controller shall enter a conservative period mode when external
period updates become stale.

REQ-009. Silent data corruption is not claimed to be fully detectable online by
the SEC-DED controller. SDC shall be accounted for in the verification
environment by post-run golden-reference memory audit.

REQ-010. Every end-to-end RTL experiment shall have a model-side certificate
containing the period table, schedule, risk budget, exact accumulated risk,
expected pass count, and expected period-index events.
