# Model/RTL contract

The model side produces:

- period_table.csv: period_index -> period_seconds -> period_model_cycles
- schedule.csv: time_index -> period_index and risk accounting
- fault_events.csv: model-cycle fault injections
- schedule_certificate.json: risk and schedule certificate

The RTL side consumes:

- period_table entries as compile-time or testbench-loaded constants
- period_index update events
- fault injection events in the verification memory model

The RTL side produces:

- pass_trace.csv
- diagnostic_trace.csv
- final_memory_audit.csv
- rtl_run_summary.csv

The comparison script checks that RTL execution matches the model schedule within
the documented cycle-level latency rules.
