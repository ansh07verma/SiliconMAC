"""OpenMAC-PD TCL Generator (PRD Module 10).

Generates Tcl scripts from configuration values for each flow stage.
Supports clock/variable generation, run-specific script creation,
stage-wise flow templates, and OpenLane config.tcl generation.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FlowConfig:
    width: int = 8
    array_size: int = 4
    clock_period: float = 10.0
    utilization: int = 60
    pdk_root: str = ""
    top: str = "mac_core"
    pipelined: bool = False
    pipeline_depth: int = 2
    target: str = "sky130A"
    std_cell_lib: str = "sky130_fd_sc_hd"

    @property
    def design_name(self) -> str:
        suffix = "_pipe" if self.pipelined else ""
        return f"{self.top}_W{self.width}_A{self.array_size}{suffix}"

    @property
    def rtl_module(self) -> str:
        return "mac_core_pipelined" if self.pipelined else "mac_core"

    @property
    def syn_dir(self) -> str:
        return f"runs/syn_W{self.width}_A{self.array_size}"

    @property
    def flow_dir(self) -> str:
        return f"runs/{self.design_name}"

    def to_dict(self) -> dict:
        return {
            "WIDTH": self.width,
            "ARRAY_SIZE": self.array_size,
            "CLOCK_PERIOD": self.clock_period,
            "UTILIZATION": self.utilization,
            "PDK_ROOT": self.pdk_root,
            "TOP": self.top,
            "PIPELINED": self.pipelined,
            "PIPELINE_DEPTH": self.pipeline_depth,
        }


# ------------------------------------------------------------------
# OpenLane config.tcl generation (PRD Module 4)
# ------------------------------------------------------------------
def gen_openlane_config(cfg: FlowConfig, verilog_path: str = "") -> str:
    """Return OpenLane config.tcl content for a design variant."""
    if not verilog_path:
        verilog_path = f"/workspace/flow/src/{cfg.rtl_module}.sv"

    return f"""\
set ::env(DESIGN_NAME) "{cfg.rtl_module}"
set ::env(VERILOG_FILES) "{verilog_path}"
set ::env(CLOCK_PERIOD) "{cfg.clock_period}"
set ::env(CLOCK_PORT) "clk"
set ::env(CLOCK_NET) "clk"
set ::env(PDK) "{cfg.target}"
set ::env(STD_CELL_LIBRARY) "{cfg.std_cell_lib}"
set ::env(SYNTH_DRIVING_CELL) "{cfg.std_cell_lib}__inv_2"
set ::env(MAX_FANOUT_CONSTRAINT) 6
set ::env(FP_CORE_UTIL) {cfg.utilization}
set ::env(FP_ASPECT_RATIO) 1
set ::env(PL_TARGET_DENSITY) {cfg.utilization / 100.0:.2f}
set ::env(GRT_REPAIR_ANTENNAS) 1
set ::env(DIODE_ON_PORTS) "in"
set ::env(RUN_HEURISTIC_DIODE_INSERTION) 1
set ::env(QUIT_ON_TIMING_VIOLATIONS) "false"
set ::env(RUN_KLAYOUT) "0"
set ::env(RUN_LINTER) "0"
"""


def write_openlane_config(cfg: FlowConfig, path: str) -> str:
    """Write OpenLane config.tcl and return the path."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(gen_openlane_config(cfg))
    return path


# ------------------------------------------------------------------
# SDC constraint generation
# ------------------------------------------------------------------
def gen_sdc(cfg: FlowConfig) -> str:
    """Return SDC constraints as a string."""
    return f"""\
# Auto-generated SDC for {cfg.design_name}
# WIDTH={cfg.width}  ARRAY_SIZE={cfg.array_size}  CLOCK_PERIOD={cfg.clock_period}

create_clock -name clk -period {cfg.clock_period} [get_ports clk]
set_clock_uncertainty 0.2 [get_clocks clk]
set_clock_transition 0.1 [get_clocks clk]

set_input_delay -max [expr {cfg.clock_period} * 0.4] -clock clk [remove_from_collection [all_inputs] [get_ports clk]]
set_input_delay -min 0.5 -clock clk [remove_from_collection [all_inputs] [get_ports clk]]

set_output_delay -max [expr {cfg.clock_period} * 0.4] -clock clk [all_outputs]
set_output_delay -min 0.5 -clock clk [all_outputs]

set_driving_cell -lib_cell buf_1 [remove_from_collection [all_inputs] [get_ports clk]]
set_load 0.05 [all_outputs]
"""


def write_sdc(cfg: FlowConfig, path: str) -> str:
    """Write SDC file and return the path."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(gen_sdc(cfg))
    return path


# ------------------------------------------------------------------
# OpenROAD flow script generation
# ------------------------------------------------------------------
def gen_openroad_flow(cfg: FlowConfig) -> str:
    """Return the OpenROAD Tcl flow script as a string."""
    return f"""\
# Auto-generated OpenROAD flow for {cfg.design_name}
# WIDTH={cfg.width}  ARRAY_SIZE={cfg.array_size}  CLOCK_PERIOD={cfg.clock_period}  UTILIZATION={cfg.utilization}

if {{![info exists ::env(WIDTH)]}}        {{ set ::env(WIDTH)        {cfg.width} }}
if {{![info exists ::env(ARRAY_SIZE)]}}   {{ set ::env(ARRAY_SIZE)   {cfg.array_size} }}
if {{![info exists ::env(CLOCK_PERIOD)]}} {{ set ::env(CLOCK_PERIOD) {cfg.clock_period} }}
if {{![info exists ::env(UTILIZATION)]}}  {{ set ::env(UTILIZATION)  {cfg.utilization} }}
if {{![info exists ::env(PDK_ROOT)]}}     {{ puts "ERROR: PDK_ROOT not set"; exit 1 }}

set WIDTH        $::env(WIDTH)
set ARRAY_SIZE   $::env(ARRAY_SIZE)
set CLOCK_PERIOD $::env(CLOCK_PERIOD)
set UTILIZATION  $::env(UTILIZATION)
set PDK_ROOT     $::env(PDK_ROOT)

set TOP        {cfg.rtl_module}
set DESIGN     {cfg.design_name}
set SYN_DIR    {cfg.syn_dir}
set RESULTS    {cfg.flow_dir}
set NETLIST    [file join $SYN_DIR "${{TOP}}_syn.v"]

file mkdir $RESULTS/reports
file mkdir $RESULTS/results

set lef_candidates {{
    [file join $PDK_ROOT sky130hd libs ref sky130hd.tcl]
    [file join $PDK_ROOT sky130A libs.ref sky130_fd_sc_hd lib sky130_fd_sc_hd.tcl]
}}
set lib_candidates {{
    [file join $PDK_ROOT sky130A libs.ref sky130_fd_sc_hd lib sky130_fd_sc_hd__tt_025C_1v80.lib]
    [file join $PDK_ROOT sky130hd libs ref sky130hd.lib]
}}

proc find_first {{candidates}} {{
    foreach f $candidates {{ if {{[file exists $f]}} {{ return $f }} }}
    return ""
}}

set LIB_FILE [find_first $lib_candidates]
if {{$LIB_FILE eq ""}} {{
    puts "ERROR: no Liberty file found under $PDK_ROOT"
    exit 2
}}
if {{![file exists $NETLIST]}} {{
    puts "ERROR: netlist not found: $NETLIST"
    exit 3
}}

puts "=========================================="
puts "OpenMAC-PD OpenROAD: $DESIGN"
puts "  W={cfg.width}  A={cfg.array_size}  T={cfg.clock_period}ns  U={cfg.utilization}%"
puts "=========================================="

read_liberty $LIB_FILE
read_verilog $NETLIST
link_design $TOP

initialize_floorplan \\
    -die_area  "0 0 300 300" \\
    -core_area "20 20 280 280" \\
    -site unithd

global_connect
place_pins -hor_layers met2 -ver_layers met3

global_placement -density [expr {{$UTILIZATION / 100.0}}]
detailed_placement
check_placement
repair_design -max_wire_length 100

clock_tree_synthesis \\
    -buf_cell {cfg.std_cell_lib}__buf_1 \\
    -root_buf {cfg.std_cell_lib}__clkbuf_1

set_routing_layers -signal met1-met5 -clock met3-met5
global_route -congestion_report $RESULTS/reports/congestion.rpt
detailed_route

create_clock -name clk -period $CLOCK_PERIOD [get_ports clk]
set_propagated_clock [all_clocks]
report_checks -path_delay max -fields {{slack input output capacitance transition}} \\
    > $RESULTS/reports/setup.rpt
report_checks -path_delay min -fields {{slack input output capacitance transition}} \\
    > $RESULTS/reports/hold.rpt
report_area > $RESULTS/reports/area.rpt
report_power > $RESULTS/reports/power.rpt

write_verilog        $RESULTS/results/${{DESIGN}}.v
write_def            $RESULTS/results/${{DESIGN}}.def
write_abstract_lef   $RESULTS/results/${{DESIGN}}.lef

puts "Flow complete for $DESIGN"
"""


def write_openroad_flow(cfg: FlowConfig, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(gen_openroad_flow(cfg))
    return path


# ------------------------------------------------------------------
# Yosys synthesis script generation
# ------------------------------------------------------------------
def gen_yosys_script(cfg: FlowConfig) -> str:
    """Return a Yosys synthesis command string (for -p flag)."""
    return (
        f"read_verilog -sv ../rtl/{cfg.rtl_module}.sv; "
        f"hierarchy -top {cfg.rtl_module} -chparam WIDTH {cfg.width} -chparam ARRAY_SIZE {cfg.array_size}"
        + (f" -chparam PIPELINE_DEPTH {cfg.pipeline_depth}" if cfg.pipelined else "")
        + "; proc; opt; fsm; opt; memory; opt; techmap; opt; "
        f"abc -D {cfg.clock_period} -dff; opt_clean -purge; "
        f"tee -o {cfg.syn_dir}/stat.rpt stat -top {cfg.rtl_module}; "
        f"write_verilog -noexpr {cfg.syn_dir}/{cfg.rtl_module}_syn.v"
    )


# ------------------------------------------------------------------
# Convenience: generate everything for a config
# ------------------------------------------------------------------
def generate_all(cfg: FlowConfig, output_dir: str = "runs") -> dict[str, str]:
    """Generate SDC + OpenROAD flow for a config. Returns dict of paths."""
    design_dir = os.path.join(output_dir, cfg.design_name)
    os.makedirs(design_dir, exist_ok=True)
    syn_dir = os.path.join(output_dir, cfg.syn_dir)
    os.makedirs(syn_dir, exist_ok=True)

    sdc_path = os.path.join(design_dir, f"{cfg.design_name}.sdc")
    flow_path = os.path.join(design_dir, "openroad_flow.tcl")

    return {
        "sdc": write_sdc(cfg, sdc_path),
        "openroad_flow": write_openroad_flow(cfg, flow_path),
    }


# ------------------------------------------------------------------
# Batch generation for multiple variants
# ------------------------------------------------------------------
def generate_variant_configs(
    variants: list[FlowConfig], output_dir: str = "runs"
) -> dict[str, dict[str, str]]:
    """Generate OpenLane configs for multiple design variants.
    
    Returns dict of {design_name: {sdc, openroad_flow, openlane_config}}.
    """
    results = {}
    for cfg in variants:
        design_dir = os.path.join(output_dir, cfg.design_name)
        os.makedirs(design_dir, exist_ok=True)

        sdc_path = os.path.join(design_dir, f"{cfg.design_name}.sdc")
        flow_path = os.path.join(design_dir, "openroad_flow.tcl")
        config_path = os.path.join(design_dir, "config.tcl")

        results[cfg.design_name] = {
            "sdc": write_sdc(cfg, sdc_path),
            "openroad_flow": write_openroad_flow(cfg, flow_path),
            "openlane_config": write_openlane_config(cfg, config_path),
        }
    return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="OpenMAC-PD TCL generator")
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--array-size", type=int, default=4)
    parser.add_argument("--clock-period", type=float, default=10.0)
    parser.add_argument("--utilization", type=int, default=60)
    parser.add_argument("--pdk-root", default="")
    parser.add_argument("--pipelined", action="store_true")
    parser.add_argument("--pipeline-depth", type=int, default=2)
    parser.add_argument("--output-dir", default="runs")
    args = parser.parse_args()

    cfg = FlowConfig(
        width=args.width,
        array_size=args.array_size,
        clock_period=args.clock_period,
        utilization=args.utilization,
        pdk_root=args.pdk_root,
        pipelined=args.pipelined,
        pipeline_depth=args.pipeline_depth,
    )
    paths = generate_all(cfg, args.output_dir)
    for k, v in paths.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
