# OpenMAC-PD Final Project Report

## 1. Executive Summary

OpenMAC-PD is a complete RTL-to-GDS ASIC physical design project implementing a parameterized Multiply-Accumulate (MAC) accelerator. The project demonstrates the full ASIC implementation flow from RTL design through synthesis, floorplanning, placement, clock tree synthesis, routing, static timing analysis, and GDSII generation using entirely open-source tools.

**Key Results:**
- 3 design variants successfully implemented through full backend
- DRC clean, LVS clean across all variants
- Pipelined variant achieves WNS = -0.47 ns (closest to timing closure at 100 MHz)
- Total power: 0.66 mW (typical corner) for basic variant
- Core area: 14,424 um^2 (basic) to 15,655 um^2 (pipelined)

## 2. Design Architecture

### 2.1 MAC Accelerator
The MAC accelerator computes the dot product of two operand vectors:
```
result = SUM(operand_a[i] * operand_b[i]) for i = 0 to ARRAY_SIZE-1
```

**Interface:**
- Inputs: clk, rst_n, start, operand_a[WIDTH*ARRAY_SIZE-1:0], operand_b[WIDTH*ARRAY_SIZE-1:0]
- Outputs: result[WIDTH*2+clog2(ARRAY_SIZE)-1:0], done, overflow, zero

**Control FSM:** IDLE -> ACCUM -> DONE_S

### 2.2 Variants
| Variant | Description | Pipeline Stages |
|---------|-------------|-----------------|
| mac_core | Single-cycle multiplier, sequential accumulator | 0 |
| mac_core_pipelined | Pipelined multiplier, configurable depth | 2 |

## 3. Implementation Flow

### 3.1 Tool Chain
| Stage | Tool | Purpose |
|-------|------|---------|
| RTL Simulation | iverilog 12.0 | Functional verification |
| Logic Synthesis | Yosys 0.38 | RTL to generic netlist |
| Floorplanning | OpenROAD | Die area, power grid |
| Placement | RePlAce/OpenROAD | Global + detailed placement |
| CTS | TritonCTS/OpenROAD | Clock tree insertion |
| Routing | TritonRoute | Detailed metal routing |
| Signoff STA | OpenSTA | Multi-corner timing |
| DRC | Magic | Design rule checking |
| LVS | Netgen | Layout vs schematic |
| GDS Export | Magic | Final layout stream |

### 3.2 PDK
- SkyWater SKY130A (130nm)
- Standard cell library: sky130_fd_sc_hd
- PDK version: 0fe599b (2024.08.17)

### 3.3 OpenLane Configuration
- Target utilization: 50%
- PL_TARGET_DENSITY: 0.6
- Clock: 10 ns (100 MHz)
- Aspect ratio: 1:1

## 4. Results

### 4.1 Timing

| Variant | Setup WNS (ns) | TNS (ns) | Hold WNS (ns) | Critical Path (ns) |
|---------|----------------|----------|---------------|---------------------|
| mac_core W8_A4 | -1.50 | -7.58 | +0.12 | 3.13 |
| mac_core_pipelined W8_A4 | -0.47 | -0.81 | +0.12 | 2.79 |

**Analysis:** The pipelined variant reduces setup WNS by 68% and TNS by 89% compared to the basic variant. The pipeline stages break the critical path through the multiplier, enabling higher clock frequencies.

### 4.2 Power (Typical Corner)

| Variant | Internal (uW) | Switching (uW) | Leakage (uW) | Total (uW) |
|---------|---------------|----------------|--------------|------------|
| mac_core W8_A4 | 453 | 244 | 0.025 | 697 |
| mac_core_pipelined W8_A4 | 733 | 308 | 0.151 | 1,041 |

**Analysis:** The pipelined variant uses ~49% more power due to additional pipeline registers, but achieves significantly better timing.

### 4.3 Area

| Variant | Core Area (um^2) | Utilization | Cells | Vias |
|---------|------------------|-------------|-------|------|
| mac_core W8_A4 | 14,424 | 53.6% | 823 | 5,957 |
| mac_core_pipelined W8_A4 | 15,655 | 54.2% | 883 | 5,921 |

### 4.4 Signoff

| Check | W8_A4 | Pipelined W8_A4 |
|-------|-------|-----------------|
| DRC | Clean | Clean |
| LVS | Clean | Clean |
| Antenna | Clean | Clean |
| Routing | 0 violations | 0 violations |

## 5. Design Space Exploration

Three variants were implemented through the full OpenLane backend:

1. **mac_core W8_A4** — Baseline configuration (WIDTH=8, ARRAY_SIZE=4)
2. **mac_core W8_A8** — Larger array (WIDTH=8, ARRAY_SIZE=8)
3. **mac_core_pipelined W8_A4** — Pipelined multiplier (WIDTH=8, ARRAY_SIZE=4, PIPELINE_DEPTH=2)

### Best Configuration
The **pipelined variant** (mac_core_pipelined W8_A4) is the recommended configuration:
- Best timing: WNS = -0.47 ns (closest to closure)
- Lowest TNS: -0.81 ns
- Moderate area overhead: +8.5% vs basic
- Power overhead: +49% vs basic

## 6. Python Tooling

### 6.1 CLI Orchestrator (openmac.py)
Unified CLI with subcommands: sim, syn, flow, explore, parse, analyze, dash, all.

### 6.2 Report Parser (parse_reports.py)
Parses OpenLane's metrics.csv, multi-corner STA reports, DRC/LVS results into structured JSON.

### 6.3 Design Space Explorer (explore.py)
Sweeps parameters across multiple configurations with preset and custom sweep modes.

### 6.4 Timing Analyzer (analyze.py)
Identifies setup/hold violations, analyzes critical paths, generates fix suggestions.

### 6.5 TCL Generator (tclgen.py)
Generates OpenLane config.tcl, SDC constraints, and OpenROAD flow scripts from configuration objects.

### 6.6 Logger (logger.py)
Timestamped stage-aware logging with per-stage log files and JSON summary output.

### 6.7 Dashboard (dashboard.py)
Generates HTML + PNG PPA comparison dashboard from parsed metrics.

## 7. Testing

- 34/34 unit tests passing (logger, tclgen, analyze modules)
- RTL simulation: 6/6 tests passing (basic, zeros, max values, single element, zero flag)
- All 3 backend variants: DRC clean, LVS clean

## 8. Future Work

1. **Timing closure** — Increase clock period to 12.5 ns or add deeper pipelining
2. **Larger sweeps** — Sweep ARRAY_SIZE=2,4,8 with full backend
3. **Floorplan optimization** — Custom pin placement, higher utilization
4. **Multi-PDK** — Port to ASAP7 or other open PDKs
5. **CNN extension** — Extend to small convolution blocks
6. **Automated CI** — GitHub Actions for regression testing
