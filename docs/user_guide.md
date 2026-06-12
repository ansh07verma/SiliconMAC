# OpenMAC-PD User Guide

## Overview

OpenMAC-PD is a complete RTL-to-GDS ASIC implementation of a parameterized Multiply-Accumulate (MAC) accelerator. It demonstrates a full physical design flow using open-source tools.

## Design

The MAC accelerator computes `result = sum(operand_a[i] * operand_b[i])` for i in 0..ARRAY_SIZE-1.

### Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| WIDTH | 8 | 4-16 | Operand bit width |
| ARRAY_SIZE | 4 | 2-8 | Number of parallel MAC units |
| PIPELINE_DEPTH | 2 | 1-4 | Pipeline stages (pipelined variant only) |

### Interfaces

| Port | Width | Direction | Description |
|------|-------|-----------|-------------|
| clk | 1 | input | Clock |
| rst_n | 1 | input | Active-low reset |
| start | 1 | input | Start computation |
| operand_a | WIDTH*ARRAY_SIZE | input | First operand vector |
| operand_b | WIDTH*ARRAY_SIZE | input | Second operand vector |
| result | WIDTH*2+clog2(ARRAY_SIZE) | output | Accumulated result |
| done | 1 | output | Computation complete |
| overflow | 1 | output | Result overflow indicator |
| zero | 1 | output | Result is zero |

### Variants

- **mac_core.sv** — Basic single-cycle MAC with sequential accumulator
- **mac_core_pipelined.sv** — Pipelined multiplier with configurable depth

## Quick Start

### Prerequisites

- WSL2 with Ubuntu 24.04+
- Docker installed
- iverilog (for simulation)

### Simulation

```bash
# Default: WIDTH=8, ARRAY_SIZE=4
cd verification
make sim

# Custom parameters
make sim WIDTH=16 ARRAY_SIZE=8

# View waveforms
gtkwave mac_core_tb.vcd
```

### Synthesis

```bash
# Requires Yosys (available in Docker)
make -C flow syn WIDTH=8 ARRAY_SIZE=4 CLOCK_PERIOD=10
```

### Full Backend (OpenLane)

```bash
# Run single variant through OpenLane
python3 openmac.py flow --width 8 --array-size 4

# Or via Makefile
make explore PRESET=timing_4x4 MODE=backend
```

## Design Space Exploration

### Presets

| Preset | Configurations | Description |
|--------|----------------|-------------|
| timing_4x4 | 3 variants | Sweep utilization at W8/A4 |
| width_sweep | 3 variants | Sweep width/array size |
| clock_sweep | 3 variants | Sweep clock period |
| pipelined_vs_basic | 2 variants | Compare basic vs pipelined |

```bash
# Run a preset sweep
python3 openmac.py explore --preset pipelined_vs_basic --mode backend

# Custom sweep
python3 openmac.py explore --params array_size clock_period --mode synthesis
```

## Reports and Analysis

```bash
# Parse all run reports
python3 openmac.py parse

# Timing violation analysis
python3 openmac.py analyze

# Generate PPA dashboard
python3 openmac.py dash
```

## CLI Reference

```
python openmac.py <command> [options]

Commands:
  sim       Run RTL simulation
  syn       Run Yosys synthesis
  flow      Run full backend flow
  explore   Design space exploration
  parse     Parse reports into JSON
  analyze   Timing violation analysis
  dash      Generate PPA dashboard
  all       Full flow: sim -> syn -> explore -> parse -> dash

Global Options:
  --width INT              Operand bit width (default: 8)
  --array-size INT         Number of MAC units (default: 4)
  --clock-period FLOAT     Target clock period in ns (default: 10.0)
  --utilization INT        Core utilization percent (default: 60)
```
