.PHONY: help check-env test schedule-demo feasibility-demo secded-rtl scheduler-rtl pass-engine-rtl controller-rtl dangerous-audit-rtl rtl synthesis evidence clean

help:
	@echo "Targets:"
	@echo "  check-env           - show tool versions"
	@echo "  test                - run Python unit tests"
	@echo "  schedule-demo       - generate schedule evidence pack"
	@echo "  feasibility-demo    - generate protection-envelope evidence pack"
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

schedule-demo:
	python3 scripts/run_schedule_demo.py

feasibility-demo:
	python3 scripts/run_feasibility_demo.py

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

rtl: secded-rtl scheduler-rtl pass-engine-rtl controller-rtl dangerous-audit-rtl

synthesis:
	python3 scripts/run_synthesis.py

evidence: test schedule-demo feasibility-demo rtl synthesis
	python3 scripts/build_chapter4_evidence_pack.py

clean:
	rm -f *.vcd *.fst *.out *.vvp
	rm -rf __pycache__ .pytest_cache generated/rtl
