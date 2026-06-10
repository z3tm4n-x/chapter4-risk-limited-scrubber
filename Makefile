.PHONY: ch3-lag-sweep interleaving-gd-case vivado-ooc-impl reproducibility-hygiene ch4-geometry-synthesis tau-min-certificate measured-policy-seed-sweep measured-policy-model reproduce-chapter4 chapter4-evidence-pack-full help check-env test import-ch3-upsets period-table ch3-five-year-schedule select-ch3-windows ch3-window-replay-rtl ch3-model-rtl-certificate ch3-fault-replay-rtl interleaving-mbu-rtl diagnostic-supervisor-rtl rho-d-sweep mc-accumulation integrated-diagnostic-rtl measured-error-estimator-rtl measured-error-controller-rtl overhead-gain-certificate schedule-demo feasibility-demo schedule-replay-rtl fault-replay-rtl secded-rtl scheduler-rtl pass-engine-rtl controller-rtl dangerous-audit-rtl rtl synthesis evidence clean chapter4-evidence-pack

help:
	@echo "  ch3-lag-sweep - evaluate sensitivity to estimate lag and session-limited updates"
	@echo "  interleaving-gd-case - compute g(D), rho_D, and residual-budget feasibility"
	@echo "  vivado-ooc-impl - run Vivado OOC implementation/timing sweep"
	@echo "  reproducibility-hygiene - check transient log tracking policy"
	@echo "  ch4-geometry-synthesis - synthesize key RTL tops at dissertation memory geometry"
	@echo "  tau-min-certificate - compute hardware feasibility margin for tau_min"
	@echo "  measured-policy-seed-sweep - evaluate measured-error policy robustness across seeds"
	@echo "  measured-policy-model - evaluate measured-error policies on five-year series"
	@echo "  reproduce-chapter4 - rebuild all Chapter 4 evidence from sources"
	@echo "  chapter4-evidence-pack - quickly rebuild aggregate Chapter 4 evidence pack only"
	@echo "  chapter4-evidence-pack-full - rebuild dependencies and aggregate Chapter 4 evidence pack"
	@echo "Targets:"
	@echo "  check-env           - show tool versions"
	@echo "  test                - run Python unit tests"
	@echo "  schedule-demo       - generate schedule evidence pack"
	@echo "  feasibility-demo    - generate protection-envelope evidence pack"
	@echo "  schedule-replay-rtl - replay model schedules on RTL controller"
	@echo "  fault-replay-rtl    - replay external fault stream on RTL controller"
	@echo "  secded-rtl          - run SEC-DED RTL exhaustive test"
	@echo "  scheduler-rtl       - run period scheduler RTL test"
	@echo "  pass-engine-rtl     - run scrub pass engine RTL test"
	@echo "  controller-rtl      - run integrated adaptive controller RTL test"
	@echo "  dangerous-audit-rtl - run dangerous-state audit RTL test"
	@echo "  rtl                 - run all RTL tests"
	@echo "  synthesis           - run Yosys resource estimates"
	@echo "  evidence            - regenerate all Chapter 4 evidence artifacts"
	@echo "  clean               - remove generated simulation outputs"

check-env:
	@echo "Python:" && python3 --version
	@echo "Git:" && git --version
	@echo "Make:" && make --version | head -n 1
	@echo "Icarus Verilog:" && (iverilog -V 2>&1 | head -n 1 || true)
	@echo "vvp:" && (vvp -V 2>&1 | head -n 1 || true)
	@echo "Yosys:" && yosys -V

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

import-ch3-upsets:
	python3 scripts/import_ch3_upsets.py

period-table:
	python3 scripts/generate_ch3_period_table.py

ch3-five-year-schedule: import-ch3-upsets period-table
	python3 scripts/run_ch3_five_year_schedule.py

select-ch3-windows: ch3-five-year-schedule
	python3 scripts/select_ch3_replay_windows.py

ch3-window-replay-rtl: select-ch3-windows
	python3 scripts/run_ch3_window_replay_rtl.py

ch3-model-rtl-certificate: ch3-window-replay-rtl
	python3 scripts/build_ch3_model_rtl_certificate.py

ch3-fault-replay-rtl: select-ch3-windows
	python3 scripts/run_ch3_fault_replay_rtl.py

interleaving-mbu-rtl:
	python3 scripts/run_interleaving_mbu_rtl.py

diagnostic-supervisor-rtl:
	python3 scripts/run_diagnostic_supervisor_rtl.py

rho-d-sweep: ch3-five-year-schedule
	python3 scripts/run_rho_d_sweep.py

mc-accumulation:
	python3 scripts/run_accumulation_monte_carlo.py

integrated-diagnostic-rtl:
	python3 scripts/run_integrated_diagnostic_controller_rtl.py

measured-error-estimator-rtl:
	python3 scripts/run_measured_error_estimator_rtl.py

measured-error-controller-rtl:
	python3 scripts/run_measured_error_controller_rtl.py

overhead-gain-certificate: ch3-five-year-schedule synthesis
	python3 scripts/build_overhead_gain_certificate.py

schedule-demo:
	python3 scripts/run_schedule_demo.py

feasibility-demo:
	python3 scripts/run_feasibility_demo.py


schedule-replay-rtl:
	python3 scripts/run_schedule_replay_rtl.py


fault-replay-rtl:
	python3 scripts/run_fault_replay_rtl.py

secded-rtl:
	python3 scripts/run_secded_rtl.py

scheduler-rtl:
	python3 scripts/run_period_scheduler_rtl.py

pass-engine-rtl:
	python3 scripts/run_scrub_pass_engine_rtl.py

controller-rtl:
	python3 scripts/run_adaptive_controller_rtl.py

dangerous-audit-rtl:
	python3 scripts/run_dangerous_audit_rtl.py

rtl: secded-rtl scheduler-rtl pass-engine-rtl controller-rtl dangerous-audit-rtl schedule-replay-rtl fault-replay-rtl

synthesis:
	python3 scripts/run_synthesis.py

evidence: test schedule-demo feasibility-demo rtl synthesis
	python3 scripts/build_chapter4_evidence_pack.py

clean:
	rm -f *.vcd *.fst *.out *.vvp
	rm -rf __pycache__ .pytest_cache generated/rtl


measured-policy-model: ch3-five-year-schedule
	python3 scripts/run_measured_policy_model.py


measured-policy-seed-sweep: ch3-five-year-schedule
	python3 scripts/run_measured_policy_seed_sweep.py


tau-min-certificate:
	python3 scripts/build_tau_min_certificate.py

chapter4-evidence-pack:
	python3 scripts/build_chapter4_evidence_pack.py

chapter4-evidence-pack-full: ch3-lag-sweep overhead-gain-certificate ch3-model-rtl-certificate ch3-fault-replay-rtl interleaving-mbu-rtl diagnostic-supervisor-rtl integrated-diagnostic-rtl interleaving-gd-case rho-d-sweep mc-accumulation measured-error-estimator-rtl measured-error-controller-rtl measured-policy-model measured-policy-seed-sweep tau-min-certificate
	python3 scripts/build_chapter4_evidence_pack.py

reproduce-chapter4: test tau-min-certificate import-ch3-upsets period-table ch3-five-year-schedule ch3-lag-sweep select-ch3-windows ch3-window-replay-rtl ch3-model-rtl-certificate ch3-fault-replay-rtl interleaving-mbu-rtl diagnostic-supervisor-rtl integrated-diagnostic-rtl interleaving-gd-case rho-d-sweep mc-accumulation measured-error-estimator-rtl measured-error-controller-rtl measured-policy-model measured-policy-seed-sweep synthesis overhead-gain-certificate chapter4-evidence-pack-full
	@echo "Chapter 4 reproduction complete."


ch4-geometry-synthesis:
	python3 scripts/run_ch4_geometry_synthesis.py


reproducibility-hygiene:
	python3 scripts/check_reproducibility_hygiene.py


vivado-ooc-impl:
	python3 scripts/run_vivado_ooc_impl.py --part xc7a200tfbg484-2 --vivado $(HOME)/bin/vivado-wsl


interleaving-gd-case: ch3-five-year-schedule rho-d-sweep
	python3 scripts/run_interleaving_gd_case.py


ch3-lag-sweep: ch3-five-year-schedule
	python3 scripts/run_ch3_lag_sweep.py
