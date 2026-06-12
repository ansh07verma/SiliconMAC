# OpenMAC-PD Interview Summary Notes

## Project Pitch (30 seconds)

"I implemented a parameterized MAC accelerator from RTL to GDS using open-source ASIC tools — Yosys for synthesis, OpenLane/OpenROAD for physical design, Magic for DRC, and Netgen for LVS. I built a Python-based design space exploration framework that sweeps configurations and compares PPA metrics. The pipelined variant achieved near-timing-closure at 100 MHz on Sky130 with zero DRC/LVS violations."

## Key Technical Points

### RTL Design
- Parameterized MAC array: configurable WIDTH (4-16 bits) and ARRAY_SIZE (2-8 units)
- Two variants: basic (single-cycle) and pipelined (2-stage multiplier)
- Status flags: overflow detection, zero-result detection
- FSM-based control: IDLE -> ACCUM -> DONE

### Physical Design Flow
- **Synthesis**: Yosys with ABC optimization, technology mapping to sky130 cells
- **Floorplanning**: 50% utilization, 1:1 aspect ratio, power grid generation
- **Placement**: Global placement with density-driven optimization
- **CTS**: Clock tree synthesis with sky130 clock buffers
- **Routing**: TritonRoute detailed routing, zero violations
- **Signoff**: Multi-corner STA, SPEF extraction, Magic DRC, Netgen LVS

### Results
| Metric | Basic | Pipelined | Improvement |
|--------|-------|-----------|-------------|
| Setup WNS | -1.50 ns | -0.47 ns | 68% |
| TNS | -7.58 ns | -0.81 ns | 89% |
| Power | 697 uW | 1,041 uW | +49% |
| Area | 14,424 um^2 | 15,655 um^2 | +8.5% |

### Design Trade-offs Explained
1. **Pipeline vs. Latency**: Pipelining adds 2 cycles latency but reduces critical path from 3.13 ns to 2.79 ns
2. **Area vs. Timing**: Pipelined uses 8.5% more area for 68% timing improvement
3. **Power vs. Performance**: 49% power increase comes from pipeline registers, justified by timing gain
4. **Utilization**: 50% utilization chosen to reduce congestion; could increase to 60% for smaller area

## Tool Chain Knowledge

### Yosys
- `read_verilog -sv` for SystemVerilog
- `hierarchy -top ... -chparam` for parameterized designs
- `proc; opt; fsm; opt; techmap` for RTL optimization
- `abc -D <period> -dff` for technology mapping with timing
- `write_verilog` for gate-level netlist

### OpenLane/OpenROAD
- Config.tcl with `::env()` variables for PDK, clock, utilization
- Flow stages: synth -> floorplan -> placement -> CTS -> routing -> signoff
- Multi-corner STA for timing validation
- SPEF extraction for parasitic-aware timing

### Sky130 PDK
- 130nm process, 1.8V standard cells
- 5 metal layers + 2 special metals
- Standard cell library: sky130_fd_sc_hd (high-density)
- Characterization corners: TT, FF, SS for timing validation

## Common Interview Questions

**Q: How did you handle timing closure?**
A: The basic variant had WNS = -1.50 ns at 100 MHz. I added a 2-stage pipeline to the multiplier, breaking the critical path. This reduced WNS to -0.47 ns — a 68% improvement. For full closure, I'd increase the clock to 12.5 ns or add a 3rd pipeline stage.

**Q: Why Sky130?**
A: It's the most mature open PDK with full characterization, DRC decks, and LVS rules. The efabless/OpenLane flow has first-class support, making it reliable for a portfolio project.

**Q: What would you do differently?**
A: I'd start with floorplan-aware RTL partitioning, use macro blocks for the multiplier array, and implement automated timing-driven synthesis with multiple Vt cells.

**Q: How does the exploration framework work?**
A: Python CLI generates per-variant OpenLane configs, runs them through Docker, parses metrics.csv and STA reports into JSON, then generates comparison tables and HTML dashboards with matplotlib charts.

**Q: What are the DRC violations about?**
A: Zero DRC violations in all 3 variants. The Magic DRC checks cover antenna rules, metal density, minimum width, and spacing. LVS also clean — netlist matches layout.
