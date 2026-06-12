# Makefile for OpenMAC-PD Verification
#
# Run with custom parameters:
#   make sim WIDTH=16 ARRAY_SIZE=8
# (WIDTH / ARRAY_SIZE are baked in at compile time via iverilog -P flag.)

TOP        = mac_core_tb
SIM_DIR    = simulation
VCD        = $(SIM_DIR)/$(TOP).vcd

WIDTH       ?= 8
ARRAY_SIZE  ?= 4
SIM_TIME    ?= 500ns

RTL_FILES = ../rtl/mac_core.sv
TB_FILES  = $(TOP).sv

all: sim

$(SIM_DIR):
	mkdir -p $(SIM_DIR)

compile: $(SIM_DIR)
	iverilog -g2012 -o $(SIM_DIR)/$(TOP).vvp -s $(TOP) \
		-P$(TOP).WIDTH=$(WIDTH) -P$(TOP).ARRAY_SIZE=$(ARRAY_SIZE) \
		-DDUMPFILE='"$(VCD)"' \
		$(TB_FILES) $(RTL_FILES)

sim: compile
	vvp $(SIM_DIR)/$(TOP).vvp +DUMPFILE=$(VCD)

vcd: sim
	@test -f $(VCD) && echo "VCD: $(VCD)" || echo "No VCD generated"

waves: vcd
	@if command -v gtkwave &> /dev/null; then \
		gtkwave $(VCD); \
	else \
		echo "Install gtkwave to view waves: sudo apt install gtkwave"; \
	fi

run-%: ## make run-16-8  (WIDTH-ARRAY_SIZE)
	$(MAKE) sim WIDTH=$(word 1,$(subst -, ,$*)) ARRAY_SIZE=$(word 2,$(subst -, ,$*))

clean:
	rm -rf $(SIM_DIR)

.PHONY: all compile sim vcd waves clean
