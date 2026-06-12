# OpenMAC-PD Developer Guide

## Architecture

```
OpenMAC-PD/
├── rtl/                          # RTL sources
│   ├── mac_core.sv               # Basic MAC accelerator
│   └── mac_core_pipelined.sv     # Pipelined variant
├── verification/                 # Testbenches
│   ├── mac_core_tb.sv            # Parameterized testbench
│   └── Makefile                  # Simulation targets
├── flow/                         # Physical design flow
│   ├── Makefile                  # Synthesis targets
│   ├── openlane_config/          # OpenLane configs per variant
│   ├── openroad_flow.tcl         # Direct OpenROAD script
│   └── runs/                     # Run output directories
├── openmac/                      # Python tooling
│   ├── __init__.py
│   ├── logger.py                 # Module 11: Logging framework
│   ├── tclgen.py                 # Module 10: TCL generator
│   └── analyze.py                # Module 9: Timing analyzer
├── scripts/                      # Utility scripts
│   ├── explore.py                # Module 7: Design space explorer
│   ├── parse_reports.py          # Module 6: Report parser
│   ├── dashboard.py              # Module 5: PPA dashboard
│   └── gen_constraints.py        # Constraint generator
├── tests/                        # Unit tests
│   ├── test_logger.py
│   ├── test_tclgen.py
│   └── test_analyze.py
├── docs/                         # Documentation
├── openmac.py                    # CLI orchestrator
├── run_tests.py                  # Test runner
└── Makefile                      # Top-level targets
```

## Tool Chain

| Stage | Tool | Version | Purpose |
|-------|------|---------|---------|
| Simulation | iverilog | 12.0 | RTL verification |
| Synthesis | Yosys | 0.38 | RTL to gate-level |
| P&R | OpenLane | 1.1.1 | Full backend flow |
| P&R | OpenROAD | b16bda7e | Place and route |
| DRC | Magic | - | Design rule check |
| LVS | Netgen | - | Layout vs schematic |
| PDK | Sky130A | 0fe599b | SkyWater 130nm |

## Module Implementation Status

### Module 1: MAC Accelerator RTL — DONE
- Parameterized WIDTH/ARRAY_SIZE
- Control FSM (IDLE/ACCUM/DONE)
- Status flags (overflow, zero)
- Pipelined variant

### Module 2: Verification Engine — DONE
- 5 test cases including corner cases
- Parameterized testbench
- VCD waveform dump
- Pass/fail counting

### Module 3: Flow Manager — DONE
- OpenLane integration via Docker
- Per-variant config generation
- Run directory management

### Module 4: Constraint Manager — DONE
- `tclgen.py` generates OpenLane config.tcl
- Variant-specific configs
- SDC constraint generation

### Module 5: Report Collection Engine — DONE
- OpenLane metrics.csv parsing
- Multi-corner STA parsing
- DRC/LVS result extraction

### Module 6: Report Parsing Engine — DONE
- `parse_reports.py` handles OpenLane output
- JSON/CSV export
- Comparison tables

### Module 7: Design Space Exploration Engine — DONE
- Preset sweep configurations
- Synthesis-only and full backend modes
- Best-config recommendation

### Module 8: Run Comparison Engine — DONE
- `compare_runs()` in parse_reports.py
- Multi-metric comparison table
- Automatic best-config selection

### Module 9: Timing Violation Analyzer — DONE
- Setup/hold violation detection
- Critical path analysis
- Actionable suggestions

### Module 10: TCL Generator — DONE
- OpenLane config.tcl generation
- SDC constraint generation
- OpenROAD flow script generation

### Module 11: Logging Framework — DONE
- Timestamped stage logging
- Per-stage log files
- JSON summary output

## Running Tests

```bash
# All tests
python3 run_tests.py

# Specific test file
python3 -m pytest tests/test_logger.py -v
```

## Code Conventions

- RTL: SystemVerilog-2012, lowercase_snake_case
- Python: PEP 8, type hints, dataclasses
- TCL: OpenLane conventions, `::env()` for variables
- Tests: Descriptive names, assert-based

## Adding a New Variant

1. Create RTL in `rtl/` (or reuse existing)
2. Add config in `flow/openlane_config/`
3. Add to VARIANT_PRESETS in `scripts/explore.py`
4. Run: `python3 openmac.py explore --preset <name> --mode backend`

## Adding a New Sweep Parameter

1. Add to CONFIGS dict in `scripts/explore.py`
2. Update FlowConfig in `openmac/tclgen.py` if needed
3. Run: `python3 openmac.py explore --params <param1> <param2>`
