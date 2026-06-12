# SiliconNPU

RTL-to-GDS physical design of a parameterized Neural Processing Unit using open-source ASIC tools.

## What is this?

A complete chip design project — from SystemVerilog RTL to manufactured layout (GDSII) — built entirely with free, open-source tools. The design is a configurable NPU with MAC array, weight memory, activation memory, and controller FSM, implemented on SkyWater's 130nm open PDK.

## Results

### Physical Design Summary

| Variant | Clock | WNS | TNS | Setup Slack | Hold Slack | Power (typ) | Core Area | Cells | GDS | DRC | LVS |
|---------|-------|-----|-----|-------------|------------|-------------|-----------|-------|-----|-----|-----|
| MAC Basic (W8/A4) | 15 ns | 0.00 ns | 0.00 ns | +1.28 ns | +0.12 ns | 0.45 mW | 14,424 um² | 690 | 2.6 MB | Clean | Clean |
| MAC Pipelined (W8/A4) | 10 ns | -0.47 ns | -0.81 ns | -0.47 ns | +0.12 ns | 1.04 mW | 15,655 um² | 715 | 2.6 MB | Clean | Clean |
| **SiliconNPU (W8/A4/D4)** | **20 ns** | **0.00 ns** | **0.00 ns** | **+0.89 ns** | **+0.12 ns** | **12.3 mW** | **61,256 um²** | **2,856** | **8.4 MB** | **Clean** | **Clean** |

All three variants pass DRC (0 violations) and LVS (0 errors). The NPU and MAC Basic achieve timing closure (WNS >= 0).

### Simulation Results

| Design | Tests | Pass | Fail | Status |
|--------|-------|------|------|--------|
| SiliconNPU | 4 (identity, zeros, max, weighted sum) | 4 | 0 | ALL PASS |
| MAC Basic | 5 (accumulation, zeros, max, single, zero flag) | 5 | 0 | ALL PASS |
| MAC Pipelined | (testbench module mismatch — needs separate TB) | — | — | — |

### NPU PPA Breakdown

| Metric | Value |
|--------|-------|
| Clock period | 20 ns (50 MHz) |
| Die area | 0.070 mm² |
| Core utilization | 55.3% |
| Total cells | 2,856 |
| Wire length | 88,970 um |
| Vias | 23,904 |
| HPWL | 60.4 mm |
| Power (slowest) | 4.76 uW internal + 5.0 uW switching + 0.02 uW leakage |
| Power (typical) | 5.89 mW internal + 6.39 mW switching + 0.87 uW leakage |
| Critical path | 6.15 ns |
| Suggested clock | 20 ns |

## Project Structure

```
SiliconNPU/
├── rtl/                        RTL sources
│   ├── silicon_npu.sv          Neural Processing Unit (NPU)
│   ├── mac_core.sv             Basic MAC accelerator
│   └── mac_core_pipelined.sv   Pipelined MAC variant
├── verification/               Testbenches
│   ├── silicon_npu_tb.sv       NPU testbench (4 tests, all pass)
│   └── mac_core_tb.sv          MAC testbench (5 tests, all pass)
├── flow/                       Physical design flow
│   ├── Makefile                Yosys synthesis targets
│   ├── config.tcl              Active OpenLane config
│   ├── src/                    RTL copies for OpenLane
│   └── openlane_config/        Variant configs
├── openmac/                    Python tooling
│   ├── logger.py               Stage-aware logging
│   ├── tclgen.py               Config/TCL generation
│   └── analyze.py              Timing violation analyzer
├── scripts/                    Utility scripts
│   ├── explore.py              Design space explorer
│   ├── parse_reports.py        Report parser (OpenLane output)
│   └── dashboard.py            PPA dashboard generator
├── tests/                      Unit tests (34/34 passing)
├── docs/                       Documentation
├── openmac.py                  CLI orchestrator
├── run_tests.py                Test runner
└── Makefile                    Top-level targets
```

## NPU Architecture

- **MAC Array**: 4 parallel multiply-accumulate units (8-bit operands)
- **Weight Memory**: 4×4 array, single write port per (row, col), combinational read
- **Activation Memory**: 4×4 array, single write port per (row, col), combinational read
- **Controller FSM**: IDLE → COMPUTE → DONE_S, 3 states
- **Accumulator**: 26-bit to hold full-precision results

### Computation

For each row r: `result += Σ(act[r][i] * weight[r][i])` for i in 0..3

## Quick Start

### Prerequisites

- WSL2 (Ubuntu 22.04+) or Linux
- Docker (for OpenLane/PDK)
- iverilog (for simulation)

### Simulation

```bash
# NPU (4 tests)
iverilog -g2012 -o npu_tb.vvp verification/silicon_npu_tb.sv rtl/silicon_npu.sv
vvp npu_tb.vvp

# MAC Basic (5 tests)
iverilog -g2012 -o mac_tb.vvp verification/mac_core_tb.sv rtl/mac_core.sv
vvp mac_tb.vvp
```

### Full Backend (RTL → GDS)

```bash
# In Docker container with PDK
export PDK_ROOT=/opt/pdk
flow.tcl -design flow -tag silicon_npu
```

## Design Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| WIDTH | 8 | 4-16 | Operand bit width |
| ARRAY_SIZE | 4 | 2-8 | Number of parallel MAC units |
| DEPTH | 4 | 2-16 | Number of rows in memory |

## Tool Chain

| Stage | Tool | Purpose |
|-------|------|---------|
| Simulation | iverilog 12.0 | RTL verification |
| Synthesis | Yosys 0.38 | RTL → gate-level netlist |
| Backend | OpenLane 1.1.1 | Floorplan → Place → CTS → Route → STA |
| DRC | Magic | Design rule checking |
| LVS | Netgen | Layout vs schematic |
| PDK | SkyWater SKY130A | 130nm standard cell library |

## Running Tests

```bash
python3 run_tests.py    # 34/34 passing
```

## Documentation

- [User Guide](docs/user_guide.md) — usage, CLI reference
- [Installation Guide](docs/install_guide.md) — WSL2 + Docker setup
- [Developer Guide](docs/developer_guide.md) — architecture, conventions
- [Final Report](docs/final_report.md) — full project report with results

## License

MIT
