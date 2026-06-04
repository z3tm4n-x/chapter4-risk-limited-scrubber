.PHONY: help check-env test clean

help:
	@echo "Targets:"
	@echo "  check-env  - show tool versions"
	@echo "  test       - run Python unit tests"
	@echo "  clean      - remove generated simulation outputs"

check-env:
	@echo "Python:" && python3 --version
	@echo "Git:" && git --version
	@echo "Make:" && make --version | head -n 1
	@echo "Icarus Verilog:" && (iverilog -V 2>&1 | head -n 1 || true)
	@echo "vvp:" && (vvp -V 2>&1 | head -n 1 || true)
	@echo "Yosys:" && yosys -V

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

clean:
	rm -f *.vcd *.fst *.out *.vvp
	rm -rf __pycache__ .pytest_cache
