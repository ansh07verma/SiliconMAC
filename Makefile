# OpenMAC-PD Top-level Makefile
# Orchestrates full RTL-to-GDS flow
#
# Usage:
#   make sim WIDTH=8 ARRAY_SIZE=4
#   make syn WIDTH=16 ARRAY_SIZE=8 CLOCK_PERIOD=10
#   make explore PRESET=timing_4x4 MODE=backend
#   make parse
#   make dash
#   make analyze
#   make all WIDTH=8 ARRAY_SIZE=4

WIDTH         ?= 8
ARRAY_SIZE    ?= 4
CLOCK_PERIOD  ?= 10.0
UTILIZATION   ?= 60
PDK_ROOT      ?=
PRESET        ?= timing_4x4
MODE          ?= synthesis

.PHONY: help sim syn explore parse analyze dash all clean

help:
	@echo "OpenMAC-PD Targets:"
	@echo "  make sim                    - Run RTL simulation"
	@echo "  make syn                    - Run Yosys synthesis"
	@echo "  make explore PRESET=...     - Design space exploration"
	@echo "    PRESETS: timing_4x4, width_sweep, clock_sweep, pipelined_vs_basic"
	@echo "    MODE: synthesis (default) or backend (full OpenLane)"
	@echo "  make parse                  - Parse reports into JSON"
	@echo "  make analyze                - Timing violation analysis"
	@echo "  make dash                   - Generate PPA dashboard"
	@echo "  make all                    - Full flow: sim -> syn -> explore -> parse -> dash"
	@echo "  make clean                  - Remove all run artifacts"
	@echo ""
	@echo "Parameters: WIDTH=$(WIDTH) ARRAY_SIZE=$(ARRAY_SIZE)"
	@echo "            CLOCK_PERIOD=$(CLOCK_PERIOD) UTILIZATION=$(UTILIZATION)"
	@echo ""
	@echo "Example: make explore PRESET=width_sweep MODE=backend"

sim:
	python3 openmac.py sim --width $(WIDTH) --array-size $(ARRAY_SIZE)

syn:
	python3 openmac.py syn --width $(WIDTH) --array-size $(ARRAY_SIZE) --clock-period $(CLOCK_PERIOD)

explore:
	python3 openmac.py explore --preset $(PRESET) --mode $(MODE)

parse:
	python3 openmac.py parse

analyze:
	python3 openmac.py analyze

dash:
	python3 openmac.py dash

all:
	python3 openmac.py all --width $(WIDTH) --array-size $(ARRAY_SIZE) --clock-period $(CLOCK_PERIOD) --utilization $(UTILIZATION)

clean:
	$(MAKE) -C verification clean
	$(MAKE) -C flow clean
	rm -rf flow/runs runs
	rm -f metrics.json exploration_results.json
	rm -f reports/dashboard.html reports/ppa_charts.png
