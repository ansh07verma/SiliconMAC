"""OpenMAC-PD Design Space Explorer (PRD Module 7).

Sweeps design parameters, runs synthesis and/or full backend for each
configuration, parses results, and generates comparison tables with
best-config recommendations.
"""

import itertools
import json
import os
import subprocess
import sys

# Add parent dir so we can import parse_reports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.parse_reports import (
    compare_runs,
    save_json,
    print_table,
    recommend_best,
)
from openmac.tclgen import FlowConfig, gen_openlane_config, gen_yosys_script


# Default sweep configurations
CONFIGS = {
    "array_size": [4, 8],
    "clock_period": [10, 15],
    "utilization": [50, 60],
    "width": [8, 16],
}

# Predefined variant sets for common comparisons
VARIANT_PRESETS = {
    "timing_4x4": [
        FlowConfig(width=8, array_size=4, clock_period=10, utilization=50),
        FlowConfig(width=8, array_size=4, clock_period=10, utilization=60),
        FlowConfig(width=8, array_size=4, clock_period=10, utilization=70),
    ],
    "width_sweep": [
        FlowConfig(width=8, array_size=4, clock_period=10, utilization=60),
        FlowConfig(width=16, array_size=4, clock_period=10, utilization=60),
        FlowConfig(width=8, array_size=8, clock_period=10, utilization=60),
    ],
    "clock_sweep": [
        FlowConfig(width=8, array_size=4, clock_period=8, utilization=60),
        FlowConfig(width=8, array_size=4, clock_period=10, utilization=60),
        FlowConfig(width=8, array_size=4, clock_period=15, utilization=60),
    ],
    "pipelined_vs_basic": [
        FlowConfig(width=8, array_size=4, clock_period=10, utilization=60, pipelined=False),
        FlowConfig(width=8, array_size=4, clock_period=10, utilization=60, pipelined=True, pipeline_depth=2),
    ],
}


def run_synthesis(width: int, array_size: int, clock_period: float,
                  project_root: str, pipelined: bool = False,
                  pipeline_depth: int = 2) -> tuple[bool, str, str]:
    """Run Yosys synthesis for a given config. Returns (success, stdout, stderr)."""
    rtl_module = "mac_core_pipelined" if pipelined else "mac_core"
    syn_dir = os.path.join(project_root, "flow", "runs", f"syn_W{width}_A{array_size}")
    os.makedirs(syn_dir, exist_ok=True)

    cmd_parts = [f"read_verilog -sv ../rtl/{rtl_module}.sv"]
    cmd_parts.append(f"hierarchy -top {rtl_module} -chparam WIDTH {width} -chparam ARRAY_SIZE {array_size}")
    if pipelined:
        cmd_parts.append(f"-chparam PIPELINE_DEPTH {pipeline_depth}")
    cmd_parts[-1] += ";"
    cmd_parts.append("proc; opt; fsm; opt; memory; opt; techmap; opt;")
    cmd_parts.append(f"abc -D {clock_period} -dff; opt_clean -purge;")
    cmd_parts.append(f"tee -o {syn_dir}/stat.rpt stat -top {rtl_module};")
    cmd_parts.append(f"write_verilog -noexpr {syn_dir}/{rtl_module}_syn.v")

    yosys_cmd = " ".join(cmd_parts)
    result = subprocess.run(
        f'cd {os.path.join(project_root, "flow")} && yosys -p "{yosys_cmd}"',
        shell=True, capture_output=True, text=True, cwd=project_root,
    )
    return result.returncode == 0, result.stdout, result.stderr


def run_backend_variant(cfg: FlowConfig, project_root: str) -> bool:
    """Run full OpenLane backend for one variant inside Docker.
    
    Returns True on success.
    """
    container_id = _get_docker_container()
    if not container_id:
        print("  ERROR: Docker container not found")
        return False

    rtl_module = cfg.rtl_module
    src_path = os.path.join(project_root, "rtl", f"{rtl_module}.sv")
    config_content = gen_openlane_config(cfg, f"/workspace/flow/src/{rtl_module}.sv")
    tag = cfg.design_name

    # Copy RTL and config into container
    subprocess.run(
        f"wsl -d Ubuntu -- bash -c \"docker cp "
        f"\"/mnt/c/Projects/OpenMAC-PD/rtl/{rtl_module}.sv\" "
        f"{container_id}:/workspace/flow/src/{rtl_module}.sv\"",
        shell=True, capture_output=True,
    )

    # Write config locally, then copy
    config_path = os.path.join(project_root, "flow", "runs", tag, "config.tcl")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        f.write(config_content)

    subprocess.run(
        f"wsl -d Ubuntu -- bash -c \"docker cp "
        f"\"/mnt/c/Projects/OpenMAC-PD/flow/runs/{tag}/config.tcl\" "
        f"{container_id}:/workspace/flow/config.tcl\"",
        shell=True, capture_output=True,
    )

    # Remove old run if exists
    subprocess.run(
        f"wsl -d Ubuntu -- bash -c \"docker exec {container_id} "
        f"bash -c 'rm -rf /workspace/flow/runs/{tag}'\"",
        shell=True, capture_output=True,
    )

    # Run OpenLane
    result = subprocess.run(
        f"wsl -d Ubuntu -- bash -c \"docker exec {container_id} "
        f"bash -c 'export PDK_ROOT=/opt/pdk && cd /workspace && "
        f"flow.tcl -design flow -tag {tag} 2>&1'\"",
        shell=True, capture_output=True, text=True, timeout=600,
    )

    success = "Flow complete" in (result.stdout or "") or "SUCCESS" in (result.stdout or "")

    # Copy results back
    if success:
        runs_local = os.path.join(project_root, "flow", "runs")
        os.makedirs(runs_local, exist_ok=True)
        subprocess.run(
            f"wsl -d Ubuntu -- bash -c \"docker cp "
            f"{container_id}:/workspace/flow/runs/{tag} "
            f"\"/mnt/c/Projects/OpenMAC-PD/flow/runs/{tag}\"\"",
            shell=True, capture_output=True,
        )

    return success


def _get_docker_container() -> str:
    """Find the running Docker container ID."""
    result = subprocess.run(
        "wsl -d Ubuntu -- bash -c \"docker ps -q\"",
        shell=True, capture_output=True, text=True,
    )
    cid = (result.stdout or "").strip()
    if len(cid.split("\n")) > 1:
        cid = cid.split("\n")[0]
    return cid


def explore_synthesis(sweep_params: dict = None, project_root: str = ".") -> list[dict]:
    """Run synthesis-only exploration sweep."""
    if sweep_params is None:
        sweep_params = {"array_size": [4, 8], "clock_period": [10, 15]}

    keys = list(sweep_params.keys())
    results = []

    for values in itertools.product(*sweep_params.values()):
        config = dict(zip(keys, values))
        width = config.get("width", 8)
        array_size = config.get("array_size", 4)
        clock_period = config.get("clock_period", 10.0)

        label = f"W{width}_A{array_size}_T{clock_period}ns"
        print(f"\n[{label}] Running synthesis...")

        ok, stdout, stderr = run_synthesis(width, array_size, clock_period, project_root)
        config["success"] = ok
        config["label"] = label
        results.append(config)

        if ok:
            print(f"  OK - {label}")
        else:
            print(f"  FAILED - {label}")
            if stderr:
                print(f"  {stderr[:200]}")

    return results


def explore_backend(variants: list[FlowConfig] = None, project_root: str = ".") -> list[dict]:
    """Run full backend exploration for multiple variants.
    
    Args:
        variants: list of FlowConfig objects. If None, uses timing_4x4 preset.
        project_root: path to the OpenMAC-PD root.
    """
    if variants is None:
        variants = VARIANT_PRESETS["timing_4x4"]

    results = []
    for cfg in variants:
        label = cfg.design_name
        print(f"\n[{label}] Running full backend...")

        ok = run_backend_variant(cfg, project_root)
        results.append({
            "label": label,
            "config": cfg.to_dict(),
            "success": ok,
        })

        status = "OK" if ok else "FAILED"
        print(f"  {status} - {label}")

    return results


def explore(sweep_params: dict = None, project_root: str = ".",
            mode: str = "synthesis", preset: str = None) -> list[dict]:
    """Run design space exploration.
    
    Args:
        sweep_params: dict of param_name -> list of values.
        project_root: path to the OpenMAC-PD root.
        mode: "synthesis" or "backend".
        preset: name of a VARIANT_PRESETS entry (overrides sweep_params).
    """
    if preset and preset in VARIANT_PRESETS:
        variants = VARIANT_PRESETS[preset]
    else:
        variants = None

    if mode == "backend":
        return explore_backend(variants, project_root)
    else:
        return explore_synthesis(sweep_params or {"array_size": [4, 8], "clock_period": [10, 15]}, project_root)


def print_exploration_summary(results: list[dict], project_root: str = "."):
    """Print summary table from exploration results."""
    print("\n=== Exploration Summary ===")
    print(f"{'Config':<35} {'Status':<8} {'Cells':<8}")
    print("-" * 51)
    for r in results:
        status = "PASS" if r.get("success") else "FAIL"
        cells = "N/A"
        label = r.get("label", "unknown")
        # Try to read cell count
        parts = label.split("_")
        stat_path = os.path.join(project_root, "flow", "runs", f"syn_{parts[0]}_{parts[1]}" if len(parts) >= 2 else "N/A", "stat.rpt")
        if os.path.exists(stat_path):
            with open(stat_path) as f:
                for line in f:
                    if "Number of cells" in line:
                        cells = line.split(":")[-1].strip()
                        break
        print(f"{label:<35} {status:<8} {cells:<8}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="OpenMAC-PD Design Space Explorer")
    parser.add_argument(
        "--params", nargs="+", default=["array_size", "clock_period"],
        help="Parameters to sweep"
    )
    parser.add_argument(
        "--mode", choices=["synthesis", "backend"], default="synthesis",
        help="Run synthesis-only or full backend exploration"
    )
    parser.add_argument(
        "--preset", choices=list(VARIANT_PRESETS.keys()),
        help="Use a predefined variant set"
    )
    parser.add_argument(
        "--project-root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="Path to OpenMAC-PD root"
    )
    args = parser.parse_args()

    if args.preset:
        results = explore(preset=args.preset, project_root=args.project_root, mode=args.mode)
    else:
        sweep = {}
        for p in args.params:
            sweep[p] = CONFIGS.get(p, [4])
        results = explore(sweep, project_root=args.project_root, mode=args.mode)

    print_exploration_summary(results, args.project_root)

    # Collect OpenLane runs for comparison
    runs_base = os.path.join(args.project_root, "flow", "runs")
    if os.path.isdir(runs_base):
        run_dirs = {}
        for name in os.listdir(runs_base):
            full = os.path.join(runs_base, name)
            if os.path.isdir(full) and os.path.isdir(os.path.join(full, "reports")):
                run_dirs[name] = full
        if run_dirs:
            print("\n=== Backend Comparison ===")
            data = compare_runs(run_dirs)
            print_table(data)
            save_json(data, os.path.join(args.project_root, "exploration_results.json"))
            print(f"\n{recommend_best(data)}")
