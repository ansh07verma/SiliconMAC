# SiliconNPU

RTL-to-GDS physical design of a parameterized Neural Processing Unit using open-source ASIC tools.

## What is this?

A complete chip design project — from SystemVerilog RTL to manufactured layout (GDSII) — built entirely with free, open-source tools. The design is a configurable NPU with MAC array, weight memory, activation memory, and controller FSM, implemented on SkyWater's 130nm open PDK.

## Results

| Variant | Setup WNS | TNS | Power | Core Area | DRC | LVS |
|---------|-----------|-----|-------|-----------|-----|-----|
| NPU W8/A4/D4 (20 ns) | 0.00 ns | 0.00 ns | ~9.6 mW | 61,256 um² | Clean | Clean |

**WNS = 0.00 ns, TNS = 0.00 ns** — timing closed at 20 ns clock period (50 MHz).

## Project Structure

```
SiliconNPU/
├── rtl/                        RTL sources
│   ├── silicon_npu.sv          Neural Processing Unit (NPU)
│   ├── mac_core.sv             Basic MAC accelerator
│   └── mac_core_pipelined.sv   Pipelined MAC variant
├── verification/               Testbenches
│   ├── silicon_npu_tb.sv       NPU testbench (4 tests, all pass)
│   └── mac_core_tb.sv          MAC testbench (6 tests, all pass)
├── flow/                       Physical design flow
│   └── Makefile                Yosys synthesis targets
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
- **Weight Memory**: 4×4 array, single write port, combinational read
- **Activation Memory**: 4×4 array, single write port, combinational read
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
iverilog -g2012 -o npu_tb.vvp verification/silicon_npu_tb.sv rtl/silicon_npu.sv
vvp npu_tb.vvp
```

### Synthesis

```bash
# In Docker container
export PDK_ROOT=/opt/pdk
cd /path/to/SiliconNPU
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
