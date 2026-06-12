# SiliconMAC

RTL-to-GDS physical design of a parameterized Multiply-Accumulate (MAC) accelerator using open-source ASIC tools.

## What is this?

A complete chip design project — from SystemVerilog RTL to manufactured layout (GDSII) — built entirely with free, open-source tools. The design is a configurable MAC accelerator that computes dot products, implemented on SkyWater's 130nm open PDK.

**3 design variants** were implemented through the full physical design flow, with automated design space exploration and PPA comparison.

## Results

| Variant | Setup WNS | TNS | Power | Core Area | DRC | LVS |
|---------|-----------|-----|-------|-----------|-----|-----|
| MAC Basic (W8/A4) | -1.50 ns | -7.58 ns | 697 uW | 14,424 um² | Clean | Clean |
| MAC Pipelined (W8/A4) | -0.47 ns | -0.81 ns | 1,041 uW | 15,655 um² | Clean | Clean |

The pipelined variant achieves **68% better WNS** and **89% better TNS** compared to the basic version, at the cost of 8.5% more area and 49% more power.

## Project Structure

```
SiliconMAC/
├── rtl/                        RTL sources
│   ├── mac_core.sv             Basic MAC accelerator
│   └── mac_core_pipelined.sv   Pipelined variant
├── verification/               Testbenches
│   ├── mac_core_tb.sv          Parameterized testbench
│   └── Makefile
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

## Quick Start

### Prerequisites

- WSL2 (Ubuntu 22.04+) or Linux
- Docker (for OpenLane/PDK)
- iverilog (for simulation)

### Simulation

```bash
cd verification
make sim                                    # default: W=8, A=4
make sim WIDTH=16 ARRAY_SIZE=8              # custom
```

### Synthesis

```bash
# In Docker container
cd /path/to/SiliconMAC
make -C flow syn WIDTH=8 ARRAY_SIZE=4 CLOCK_PERIOD=10
```

### Full Backend (RTL → GDS)

```bash
python3 openmac.py flow --width 8 --array-size 4
```

### Design Space Exploration

```bash
# Run predefined sweep
python3 openmac.py explore --preset pipelined_vs_basic --mode backend

# Custom sweep
python3 openmac.py explore --params array_size clock_period --mode synthesis
```

### Parse Results & Generate Dashboard

```bash
python3 openmac.py parse      # parse all run reports
python3 openmac.py analyze    # timing violation analysis
python3 openmac.py dash       # generate HTML + chart dashboard
```

## Design Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| WIDTH | 8 | 4-16 | Operand bit width |
| ARRAY_SIZE | 4 | 2-8 | Number of parallel MAC units |
| PIPELINE_DEPTH | 2 | 1-4 | Pipeline stages (pipelined variant) |

## Tool Chain

| Stage | Tool | Purpose |
|-------|------|---------|
| Simulation | iverilog 12.0 | RTL verification |
| Synthesis | Yosys 0.38 | RTL → gate-level netlist |
| Backend | OpenLane 1.1.1 | Floorplan → Place → CTS → Route → STA |
| DRC | Magic | Design rule checking |
| LVS | Netgen | Layout vs schematic |
| PDK | SkyWater SKY130A | 130nm standard cell library |

## Exploration Presets

| Preset | Variants | Description |
|--------|----------|-------------|
| `timing_4x4` | 3 | Sweep utilization at W8/A4 |
| `width_sweep` | 3 | Sweep width and array size |
| `clock_sweep` | 3 | Sweep clock period |
| `pipelined_vs_basic` | 2 | Compare basic vs pipelined |

## Running Tests

```bash
python3 run_tests.py    # 34/34 passing
```

## Documentation

- [User Guide](docs/user_guide.md) — usage, CLI reference
- [Installation Guide](docs/install_guide.md) — WSL2 + Docker setup
- [Developer Guide](docs/developer_guide.md) — architecture, conventions
- [Final Report](docs/final_report.md) — full project report with results
- [Interview Notes](docs/interview_notes.md) — pitch, Q&A prep

## License

MIT
