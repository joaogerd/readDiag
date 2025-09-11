# Makefile for bench_readers.py

PY ?= python
BENCH := bench_readers.py

# Default config (override at invocation: make bench CONV=... RAD=...)
CONV ?= ../data/diag_conv_01.2024013018
RAD  ?= ../data/diag_amsua_metop-b_01.2024013018
REPEATS ?= 3
WARMUP  ?= 1
CONV_MODES ?= split,compact,raw
EXTRA ?=

RUN := $(PY) $(BENCH) --conv $(CONV) --rad $(RAD) \
       --repeats $(REPEATS) --warmup $(WARMUP) \
       --conv-modes $(CONV_MODES) $(EXTRA)

.PHONY: bench bench-cold bench-split bench-raw bench-compact bench-nomemmap verify fast matrix help

bench:
	$(RUN)

bench-cold:
	$(RUN) --cold

bench-split:
	$(PY) $(BENCH) --conv $(CONV) --rad $(RAD) \
	  --conv-modes split --repeats $(REPEATS) --warmup $(WARMUP) $(EXTRA)

bench-raw:
	$(PY) $(BENCH) --conv $(CONV) --rad $(RAD) \
	  --conv-modes raw --repeats $(REPEATS) --warmup $(WARMUP) $(EXTRA)

bench-compact:
	$(PY) $(BENCH) --conv $(CONV) --rad $(RAD) \
	  --conv-modes compact --repeats $(REPEATS) --warmup $(WARMUP) $(EXTRA)

bench-nomemmap:
	$(RUN) --skip_memmap

verify:
	$(RUN) --verify

fast:
	$(PY) $(BENCH) --conv $(CONV) --rad $(RAD) \
	  --repeats 1 --warmup 0 --conv-modes split --skip_memmap $(EXTRA)

matrix:
	@for m in split compact raw; do \
	  echo "\n== $$m =="; \
	  $(PY) $(BENCH) --conv $(CONV) --rad $(RAD) \
	    --conv-modes $$m --repeats $(REPEATS) --warmup $(WARMUP) $(EXTRA); \
	done

help:
	@echo "CONV=$(CONV)"; \
	echo "RAD=$(RAD)"; \
	echo "Use: make bench [CONV=...] [RAD=...] [REPEATS=...] [WARMUP=...] [CONV_MODES=...] [EXTRA='--cold --verify']";

