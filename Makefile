# Basic test/bench workflow for readDiag

.PHONY: help test test-fast test-slow bench clean

PYTEST ?= pytest
PYTEST_OPTS ?=
DATA ?= $(PWD)/data
DATATEST ?= $(PWD)/dataTest/exp20

export READDIAG_DATA := $(DATA)
export READDIAG_DATA_TEST := $(DATATEST)
export MPLBACKEND := Agg
export PYTHONWARNINGS := default

help:
	@echo "Targets:"
	@echo "  make test        - run full test suite"
	@echo "  make test-fast   - run fast tests (exclude benchmark)"
	@echo "  make bench       - run only benchmark tests"
	@echo "  make clean       - remove caches"

test:
	$(PYTEST) $(PYTEST_OPTS)

test-fast:
	$(PYTEST) -m "not benchmark" $(PYTEST_OPTS)

bench:
	$(PYTEST) -m benchmark $(PYTEST_OPTS)

clean:
	rm -rf .pytest_cache .benchmarks

