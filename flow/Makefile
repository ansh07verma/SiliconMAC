# Flow Makefile for OpenMAC-PD
# Stage targets: syn, all
#
# Usage:
#   make -C flow syn WIDTH=8 ARRAY_SIZE=4 CLOCK_PERIOD=10
#   make -C flow all PDK_ROOT=/path/to/pdk

WIDTH         ?= 8
ARRAY_SIZE    ?= 4
CLOCK_PERIOD  ?= 10.0
UTILIZATION   ?= 60

TOP        = mac_core
DESIGN     = $(TOP)_W$(WIDTH)_A$(ARRAY_SIZE)
SYN_DIR    = runs/syn_W$(WIDTH)_A$(ARRAY_SIZE)
FLOW_DIR   = runs/$(DESIGN)

RTL_DIR    = ../rtl
RTL_FILE   = $(RTL_DIR)/$(TOP).sv

export WIDTH
export ARRAY_SIZE
export CLOCK_PERIOD
export UTILIZATION
export PDK_ROOT

.PHONY: help syn all clean clean-syn

help:
	@echo "OpenMAC-PD flow targets"
	@echo "  make syn        - Yosys synthesis only"
	@echo "  make all        - syn + OpenROAD flow (needs PDK_ROOT)"
	@echo ""
	@echo "Vars: WIDTH=$(WIDTH) ARRAY_SIZE=$(ARRAY_SIZE) CLOCK_PERIOD=$(CLOCK_PERIOD) UTILIZATION=$(UTILIZATION)"

# ---------------------------------------------------------------- synthesis
$(SYN_DIR):
	mkdir -p $(SYN_DIR)

syn: $(SYN_DIR) $(RTL_FILE)
	yosys -p "read_verilog -sv $(RTL_FILE); \
		hierarchy -top $(TOP) -chparam WIDTH $(WIDTH) -chparam ARRAY_SIZE $(ARRAY_SIZE); \
		proc; opt; fsm; opt; memory; opt; techmap; opt; \
		abc -D $(CLOCK_PERIOD) -dff; opt_clean -purge; \
		tee -o $(SYN_DIR)/stat.rpt stat -top $(TOP); \
		write_verilog -noexpr $(SYN_DIR)/$(TOP)_syn.v" \
		2>&1 | tee $(SYN_DIR)/syn.log

# ---------------------------------------------------------------- flow stages
all: syn
	@if [ -z "$$PDK_ROOT" ]; then \
		echo "PDK_ROOT not set — skipping openroad. Export PDK_ROOT to enable."; \
		exit 0; \
	fi
	openroad -script openroad_flow.tcl 2>&1 | tee $(FLOW_DIR)/openroad.log

# ---------------------------------------------------------------- housekeeping
clean:
	rm -rf runs

clean-syn:
	rm -rf runs/syn_*
