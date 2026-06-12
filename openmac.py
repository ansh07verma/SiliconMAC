#!/usr/bin/env python3
"""OpenMAC-PD CLI Orchestrator.

Subcommands:
    sim     Run RTL simulation
    syn     Run Yosys synthesis
    flow    Run full backend flow (needs Docker + PDK)
    explore Run design space exploration
    parse   Parse reports into JSON
    analyze Run timing violation analysis
    dash    Generate PPA dashboard
    all     Full flow: sim -> syn -> explore -> parse -> dash

Usage:
    python openmac.py sim --width 8 --array-size 4
    python openmac.py syn --width 16 --array-size 8 --clock-period 10
    python openmac.py explore --preset timing_4x4 --mode backend
    python openmac.py all --width 8 --array-size 4
"""

import argparse
import json
import os
import subprocess
import sys
import time

# Ensure the project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from openmac.logger import FlowLogger
from openmac.tclgen import FlowConfig, generate_all, write_sdc
from openmac.analyze import analyze_run, print_report

SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")


def find_wsl() -> str:
    """Return 'wsl' if on Windows, else '' (already in Linux)."""
    if sys.platform == "win32":
        return "wsl"
    return ""


def run_cmd(cmd: str, description: str = "", timeout: int = 3600) -> tuple[int, str, str]:
    """Run a shell command, return (returncode, stdout, stderr)."""
    wsl = find_wsl()
    if wsl:
        cmd = f"{wsl} -e bash --noprofile --norc -c \"{cmd.replace('\"', '\\\"')}\""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def cmd_sim(args, log: FlowLogger):
    """Run RTL simulation."""
    log.stage_start("simulation")
    cfg = FlowConfig(width=args.width, array_size=args.array_size)

    sim_dir = os.path.join(PROJECT_ROOT, "verification")
    cmd = f"cd {sim_dir} && make sim WIDTH={cfg.width} ARRAY_SIZE={cfg.array_size}"
    rc, out, err = run_cmd(cmd, timeout=120)

    if rc == 0:
        log.stage_ok("simulation", width=cfg.width, array_size=cfg.array_size)
    else:
        log.stage_fail("simulation", f"rc={rc}", stderr=err[-500:] if err else "")
        print(out)
        print(err)
    return rc


def cmd_syn(args, log: FlowLogger):
    """Run Yosys synthesis."""
    log.stage_start("synthesis")
    cfg = FlowConfig(
        width=args.width,
        array_size=args.array_size,
        clock_period=args.clock_period,
    )

    cmd = f"cd {PROJECT_ROOT} && make -C flow syn WIDTH={cfg.width} ARRAY_SIZE={cfg.array_size} CLOCK_PERIOD={cfg.clock_period}"
    rc, out, err = run_cmd(cmd, timeout=300)

    if rc == 0:
        syn_dir = os.path.join(PROJECT_ROOT, "flow", "runs", f"syn_W{cfg.width}_A{cfg.array_size}")
        cells = ""
        stat_path = os.path.join(syn_dir, "stat.rpt")
        if os.path.exists(stat_path):
            with open(stat_path) as f:
                for line in f:
                    if "Number of cells" in line:
                        cells = line.split(":")[-1].strip()
                        break
        log.stage_ok("synthesis", cells=cells, netlist=f"{syn_dir}/mac_core_syn.v")
    else:
        log.stage_fail("synthesis", f"rc={rc}", stderr=err[-500:] if err else "")
        print(out[-1000:])
        print(err[-500:])
    return rc


def cmd_flow(args, log: FlowLogger):
    """Run full backend flow (needs Docker + PDK)."""
    log.stage_start("backend_flow")
    cfg = FlowConfig(
        width=args.width,
        array_size=args.array_size,
        clock_period=args.clock_period,
        utilization=args.utilization,
        pdk_root=args.pdk_root,
        pipelined=getattr(args, "pipelined", False),
        pipeline_depth=getattr(args, "pipeline_depth", 2),
    )

    # Generate scripts
    paths = generate_all(cfg, os.path.join(PROJECT_ROOT, "flow", "runs"))
    log.stage_ok("tcl_gen", sdc=paths["sdc"], openroad_flow=paths["openroad_flow"])

    # Run OpenLane inside Docker
    log.stage_start("openlane")
    from scripts.explore import run_backend_variant
    ok = run_backend_variant(cfg, PROJECT_ROOT)
    if ok:
        log.stage_ok("openlane", results_dir=cfg.flow_dir)
    else:
        log.stage_fail("openlane", "OpenLane flow failed")
    return 0 if ok else 1


def cmd_explore(args, log: FlowLogger):
    """Run design space exploration."""
    log.stage_start("exploration")

    sys.path.insert(0, SCRIPTS_DIR)
    from scripts.explore import explore, print_exploration_summary

    preset = getattr(args, "preset", None)
    mode = getattr(args, "mode", "synthesis")

    if preset:
        results = explore(preset=preset, project_root=PROJECT_ROOT, mode=mode)
    else:
        sweep = {}
        params = getattr(args, "params", None) or ["array_size", "clock_period"]
        for p in params:
            from scripts.explore import CONFIGS
            sweep[p] = CONFIGS.get(p, [4])
        results = explore(sweep, project_root=PROJECT_ROOT, mode=mode)

    print_exploration_summary(results, PROJECT_ROOT)
    log.stage_ok("exploration", configs_run=len(results))
    return 0


def cmd_parse(args, log: FlowLogger):
    """Parse reports from run directories."""
    log.stage_start("parse_reports")
    from scripts.parse_reports import compare_runs, save_json, print_table, recommend_best

    run_dirs = {}
    for d in (getattr(args, "run_dirs", None) or []):
        name = os.path.basename(d.rstrip("/\\"))
        run_dirs[name] = d

    if not run_dirs:
        runs_base = os.path.join(PROJECT_ROOT, "flow", "runs")
        if os.path.isdir(runs_base):
            for name in os.listdir(runs_base):
                full = os.path.join(runs_base, name)
                if os.path.isdir(full) and os.path.isdir(os.path.join(full, "reports")):
                    run_dirs[name] = full

    if not run_dirs:
        log.stage_skip("parse_reports", "No run directories found")
        return 0

    data = compare_runs(run_dirs)
    print_table(data)
    save_json(data, os.path.join(PROJECT_ROOT, "metrics.json"))
    print(f"\n{recommend_best(data)}")
    log.stage_ok("parse_reports", runs=len(run_dirs))
    return 0


def cmd_analyze(args, log: FlowLogger):
    """Run timing violation analysis."""
    log.stage_start("timing_analysis")

    run_dirs = getattr(args, "run_dirs", None) or []
    if not run_dirs:
        runs_base = os.path.join(PROJECT_ROOT, "flow", "runs")
        if os.path.isdir(runs_base):
            for name in os.listdir(runs_base):
                full = os.path.join(runs_base, name)
                if os.path.isdir(full):
                    run_dirs.append(full)

    for d in run_dirs:
        result = analyze_run(d)
        print_report(result)

    log.stage_ok("timing_analysis", runs_analyzed=len(run_dirs))
    return 0


def cmd_dash(args, log: FlowLogger):
    """Generate PPA dashboard."""
    log.stage_start("dashboard")
    metrics_file = os.path.join(PROJECT_ROOT, "metrics.json")
    output_dir = os.path.join(PROJECT_ROOT, "reports")

    sys.path.insert(0, SCRIPTS_DIR)
    from scripts.dashboard import generate_dashboard

    generate_dashboard(metrics_file, output_dir)
    log.stage_ok("dashboard", output=output_dir)
    return 0


def cmd_all(args, log: FlowLogger):
    """Full flow: sim -> syn -> explore -> parse -> dash."""
    rc = cmd_sim(args, log)
    if rc != 0:
        return rc

    rc = cmd_syn(args, log)
    if rc != 0:
        return rc

    cmd_explore(args, log)
    cmd_parse(args, log)
    cmd_dash(args, log)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="OpenMAC-PD: RTL-to-GDS MAC Accelerator Flow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand to run")

    # Common args
    def add_common(p):
        p.add_argument("--width", type=int, default=8, help="Operand bit width")
        p.add_argument("--array-size", type=int, default=4, help="Number of MAC units")
        p.add_argument("--clock-period", type=float, default=10.0, help="Target clock period (ns)")
        p.add_argument("--utilization", type=int, default=60, help="Core utilization (percent)")
        p.add_argument("--pdk-root", default="", help="Path to SkyWater PDK")
        p.add_argument("--run-dir", default="runs", help="Output run directory")

    # sim
    p_sim = sub.add_parser("sim", help="Run RTL simulation")
    add_common(p_sim)

    # syn
    p_syn = sub.add_parser("syn", help="Run Yosys synthesis")
    add_common(p_syn)

    # flow
    p_flow = sub.add_parser("flow", help="Run full backend flow")
    add_common(p_flow)
    p_flow.add_argument("--pipelined", action="store_true", help="Use pipelined RTL")
    p_flow.add_argument("--pipeline-depth", type=int, default=2, help="Pipeline depth")

    # explore
    p_exp = sub.add_parser("explore", help="Design space exploration")
    add_common(p_exp)
    p_exp.add_argument("--params", nargs="+", default=["array_size", "clock_period"],
                       help="Parameters to sweep")
    p_exp.add_argument("--mode", choices=["synthesis", "backend"], default="synthesis",
                       help="Run synthesis-only or full backend exploration")
    p_exp.add_argument("--preset", choices=[
        "timing_4x4", "width_sweep", "clock_sweep", "pipelined_vs_basic"
    ], help="Use a predefined variant set")

    # parse
    p_parse = sub.add_parser("parse", help="Parse reports into JSON")
    p_parse.add_argument("run_dirs", nargs="*", help="Run directories (auto-discovered if empty)")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Timing violation analysis")
    p_analyze.add_argument("run_dirs", nargs="*", help="Run directories (auto-discovered if empty)")

    # dash
    p_dash = sub.add_parser("dash", help="Generate PPA dashboard")

    # all
    p_all = sub.add_parser("all", help="Full flow: sim -> syn -> explore -> parse -> dash")
    add_common(p_all)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    # Determine run directory
    cfg = FlowConfig(
        width=getattr(args, "width", 8),
        array_size=getattr(args, "array_size", 4),
    )
    run_dir = os.path.join(PROJECT_ROOT, "runs", cfg.design_name)
    os.makedirs(run_dir, exist_ok=True)

    with FlowLogger(run_dir, f"openmac_{args.command}") as log:
        cmd_map = {
            "sim": cmd_sim,
            "syn": cmd_syn,
            "flow": cmd_flow,
            "explore": cmd_explore,
            "parse": cmd_parse,
            "analyze": cmd_analyze,
            "dash": cmd_dash,
            "all": cmd_all,
        }
        rc = cmd_map[args.command](args, log)
        log.summary()
        log.save_summary()

    return rc


if __name__ == "__main__":
    sys.exit(main() or 0)
