# OpenMAC-PD Report Parser
# Extracts PPA metrics from OpenLane run directories into structured JSON.
#
# Handles OpenLane's actual output structure:
#   runs/<tag>/
#     reports/
#       metrics.csv                    -- master metrics
#       signoff/37-sta-rcx_nom/        -- timing (multi-corner)
#       signoff/42-*.lvs.rpt           -- LVS
#       signoff/44-drc.log             -- DRC
#       routing/30-detailed.log        -- routing
#       synthesis/1-synthesis.rpt      -- yosys stats

import csv
import json
import os
import re


# ------------------------------------------------------------------
# OpenLane metrics.csv parser
# ------------------------------------------------------------------
def parse_metrics_csv(csv_path: str) -> dict:
    """Parse OpenLane's metrics.csv into a flat dict."""
    if not os.path.exists(csv_path):
        return {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return {}
    return rows[0]


# ------------------------------------------------------------------
# Multi-corner STA summary parser
# ------------------------------------------------------------------
def parse_sta_summary(rpt_path: str) -> dict:
    """Parse multi_corner_sta.summary.rpt for WNS/TNS."""
    result = {}
    if not os.path.exists(rpt_path):
        return result
    with open(rpt_path) as f:
        text = f.read()

    m = re.search(r"wns\s+(-?\d+\.?\d*)", text, re.IGNORECASE)
    if m:
        result["wns"] = float(m.group(1))
    m = re.search(r"tns\s+(-?\d+\.?\d*)", text, re.IGNORECASE)
    if m:
        result["tns"] = float(m.group(1))

    # Hold slack
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "worst_slack" in line.lower() and "min" in line.lower():
            for j in range(i, min(i + 5, len(lines))):
                m2 = re.search(r"slack\s+(-?\d+\.?\d*)", lines[j], re.IGNORECASE)
                if m2:
                    result["hold_wns"] = float(m2.group(1))
                    break
        if "worst_slack" in line.lower() and "max" in line.lower():
            for j in range(i, min(i + 5, len(lines))):
                m2 = re.search(r"slack\s+(-?\d+\.?\d*)", lines[j], re.IGNORECASE)
                if m2:
                    result["setup_wns"] = float(m2.group(1))
                    break

    return result


# ------------------------------------------------------------------
# Power report parser
# ------------------------------------------------------------------
def parse_power_report(rpt_path: str) -> dict:
    """Parse multi_corner_sta.power.rpt for power values."""
    result = {}
    if not os.path.exists(rpt_path):
        return result
    with open(rpt_path) as f:
        text = f.read()

    # Find Typical corner section
    in_typical = False
    for line in text.split("\n"):
        if "Typical Corner" in line:
            in_typical = True
        if in_typical and "Total" in line:
            m = re.search(r"Total\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)", line)
            if m:
                result["internal_power_uW"] = float(m.group(1)) * 1e6
                result["switching_power_uW"] = float(m.group(2)) * 1e6
                result["leakage_power_uW"] = float(m.group(3)) * 1e6
                result["total_power_uW"] = float(m.group(4)) * 1e6
            break

    return result


# ------------------------------------------------------------------
# LVS report parser
# ------------------------------------------------------------------
def parse_lvs_report(rpt_path: str) -> dict:
    """Parse LVS report for error count."""
    result = {"lvs_clean": False, "lvs_errors": -1}
    if not os.path.exists(rpt_path):
        return result
    with open(rpt_path) as f:
        text = f.read()
    if "LVS clean" in text or "no net, device, pin, or property mismatches" in text:
        result["lvs_clean"] = True
        result["lvs_errors"] = 0
    else:
        m = re.search(r"Total errors\s*=\s*(\d+)", text)
        if m:
            result["lvs_errors"] = int(m.group(1))
    return result


# ------------------------------------------------------------------
# DRC report parser
# ------------------------------------------------------------------
def parse_drc_log(log_path: str) -> dict:
    """Parse DRC log for violation count."""
    result = {"drc_clean": False, "drc_violations": -1}
    if not os.path.exists(log_path):
        return result
    with open(log_path) as f:
        text = f.read()
    if "No Magic DRC violations" in text or "Total Magic DRC violations is 0" in text:
        result["drc_clean"] = True
        result["drc_violations"] = 0
    else:
        m = re.search(r"Total\s*(?:Magic\s*)?DRC violations\s*(?:is|=)\s*(\d+)", text, re.IGNORECASE)
        if m:
            result["drc_violations"] = int(m.group(1))
    return result


# ------------------------------------------------------------------
# Routing log parser
# ------------------------------------------------------------------
def parse_routing_log(log_path: str) -> dict:
    """Extract routing metrics from detailed route log."""
    result = {}
    if not os.path.exists(log_path):
        return result
    with open(log_path) as f:
        text = f.read()
    m = re.search(r"Total\s+vias\s*:\s*(\d+)", text)
    if m:
        result["total_vias"] = int(m.group(1))
    m = re.search(r"Total\s+wires\s*:\s*(\d+)", text)
    if m:
        result["total_wires"] = int(m.group(1))
    m = re.search(r"DRC violations\s*:\s*(\d+)", text)
    if m:
        result["drc_after_route"] = int(m.group(1))
    return result


# ------------------------------------------------------------------
# Master: parse all reports from an OpenLane run directory
# ------------------------------------------------------------------
def parse_openlane_run(run_dir: str) -> dict:
    """Parse all reports from an OpenLane run directory.
    
    Expected structure:
      run_dir/
        reports/
          metrics.csv
          signoff/
            37-sta-rcx_nom/multi_corner_sta.summary.rpt
            37-sta-rcx_nom/multi_corner_sta.power.rpt
            42-*.lvs.rpt
            44-drc.log
          routing/
            30-detailed.log
          synthesis/
            1-synthesis.rpt
        results/final/
          gds/*.gds
          def/*.def
          lib/*.lib
          lef/*.lef
    """
    metrics = {
        "run_dir": run_dir,
        "run_name": os.path.basename(run_dir.rstrip("/\\")),
        "wns": None, "tns": None,
        "hold_wns": None, "setup_wns": None,
        "cell_area": None, "core_area": None, "utilization": None,
        "total_power_uW": None, "leakage_power_uW": None,
        "drc_clean": None, "drc_violations": None,
        "lvs_clean": None, "lvs_errors": None,
        "total_vias": None, "total_wires": None,
        "synth_cells": None, "total_cells": None,
        "gds_path": None, "def_path": None, "lib_path": None,
        "flow_complete": False,
    }

    reports_dir = os.path.join(run_dir, "reports")
    results_dir = os.path.join(run_dir, "results", "final")

    # 1. metrics.csv (master source)
    csv_path = os.path.join(reports_dir, "metrics.csv")
    csv_data = parse_metrics_csv(csv_path)
    if csv_data:
        metrics["flow_complete"] = csv_data.get("flow_status", "") == "flow completed"
        for key in [
            ("wns", "spef_wns"), ("tns", "spef_tns"),
            ("synth_cells", "synth_cell_count"),
            ("total_cells", None),
        ]:
            dst, src = key
            if src and src in csv_data:
                try:
                    metrics[dst] = float(csv_data[src])
                except (ValueError, TypeError):
                    pass
        # Area from CSV
        for csv_key, dst_key in [
            ("CoreArea_um^2", "core_area"),
            ("DIEAREA_mm^2", "die_area"),
            ("Final_Util", "utilization"),
            ("tritonRoute_violations", "routing_violations"),
            ("wire_length", "wire_length"),
            ("vias", "total_vias"),
        ]:
            if csv_key in csv_data:
                try:
                    metrics[dst_key] = float(csv_data[csv_key])
                except (ValueError, TypeError):
                    pass

    # 2. STA summary
    sta_dirs = [
        os.path.join(reports_dir, "signoff", "37-sta-rcx_nom"),
        os.path.join(reports_dir, "signoff", "33-sta-rcx_min"),
    ]
    for d in sta_dirs:
        summary = os.path.join(d, "multi_corner_sta.summary.rpt")
        data = parse_sta_summary(summary)
        for k, v in data.items():
            if metrics.get(k) is None and v is not None:
                metrics[k] = v
        power = os.path.join(d, "multi_corner_sta.power.rpt")
        pdata = parse_power_report(power)
        for k, v in pdata.items():
            if v is not None:
                metrics[k] = v

    # 3. LVS
    import glob as globmod
    lvs_pattern = os.path.join(reports_dir, "signoff", "*-*.lvs.rpt")
    lvs_files = globmod.glob(lvs_pattern)
    if lvs_files:
        lvs = parse_lvs_report(lvs_files[0])
        metrics.update({k: v for k, v in lvs.items() if v is not None})

    # 4. DRC
    drc_files = globmod.glob(os.path.join(reports_dir, "signoff", "*-drc.log"))
    if drc_files:
        drc = parse_drc_log(drc_files[0])
        metrics.update({k: v for k, v in drc.items() if v is not None})

    # 5. Routing
    route_logs = globmod.glob(os.path.join(reports_dir, "routing", "*-detailed.log"))
    if route_logs:
        rdata = parse_routing_log(route_logs[0])
        for k, v in rdata.items():
            if v is not None:
                metrics[k] = v

    # 6. Synthesis stat.rpt
    synth_rpt = os.path.join(reports_dir, "synthesis", "1-synthesis.rpt")
    if os.path.exists(synth_rpt):
        with open(synth_rpt) as f:
            text = f.read()
        m = re.search(r"Number of cells\s*:\s*(\d+)", text)
        if m:
            metrics["synth_cells"] = int(m.group(1))

    # 7. Final artifacts
    for artifact, pattern in [
        ("gds_path", "gds/*.gds"),
        ("def_path", "def/*.def"),
        ("lib_path", "lib/*.lib"),
        ("lef_path", "lef/*.lef"),
    ]:
        matches = globmod.glob(os.path.join(results_dir, pattern))
        if matches:
            metrics[artifact] = matches[0]

    return metrics


# ------------------------------------------------------------------
# Compare multiple runs
# ------------------------------------------------------------------
def compare_runs(runs: dict) -> dict:
    """Compare multiple OpenLane run directories.
    
    Args:
        runs: dict of {name: run_dir_path}
    Returns:
        dict of {name: metrics_dict}
    """
    data = {}
    for name, run_dir in runs.items():
        if os.path.isdir(os.path.join(run_dir, "reports")):
            data[name] = parse_openlane_run(run_dir)
        else:
            data[name] = {"run_dir": run_dir, "error": "not an OpenLane run"}
    return data


# ------------------------------------------------------------------
# Legacy: parse flat report directory (non-OpenLane)
# ------------------------------------------------------------------
def parse_flat_run(run_dir: str) -> dict:
    """Parse reports from a flat directory (original format)."""
    metrics = {
        "wns": None, "tns": None, "cell_area": None, "core_area": None,
        "utilization": None, "total_power": None, "leakage_power": None,
        "dynamic_power": None, "drc_count": None, "routing_violations": None,
        "yosys_cells": None,
    }

    reports_dir = os.path.join(run_dir, "reports")
    if not os.path.isdir(reports_dir):
        reports_dir = run_dir

    for fname in os.listdir(reports_dir):
        fpath = os.path.join(reports_dir, fname)
        if not os.path.isfile(fpath):
            continue
        with open(fpath) as f:
            text = f.read()

        if "setup" in fname or "hold" in fname:
            m = re.search(r"worst slack\s+(-?\d+\.?\d*)", text, re.IGNORECASE)
            if m:
                metrics["wns"] = float(m.group(1))
            m = re.search(r"total slack\s+(-?\d+\.?\d*)", text, re.IGNORECASE)
            if m:
                metrics["tns"] = float(m.group(1))
        elif "area" in fname:
            m = re.search(r"Combinational area\s*:\s*(\d+\.?\d*)", text)
            if not m:
                m = re.search(r"Chip area\s*:\s*(\d+\.?\d*)", text)
            if m:
                metrics["cell_area"] = float(m.group(1))
        elif "power" in fname:
            m = re.search(r"Total\s+(\d+\.?\d*)", text)
            if m:
                metrics["total_power"] = float(m.group(1))

    stat_path = os.path.join(run_dir, "stat.rpt")
    if os.path.exists(stat_path):
        with open(stat_path) as f:
            text = f.read()
        m = re.search(r"Number of cells\s*:\s*(\d+)", text)
        if m:
            metrics["yosys_cells"] = int(m.group(1))

    return metrics


# ------------------------------------------------------------------
# Table output
# ------------------------------------------------------------------
# Columns to display and their human-readable labels
DISPLAY_COLS = [
    ("run_name",          "Run"),
    ("flow_complete",     "Done"),
    ("wns",               "WNS (ns)"),
    ("tns",               "TNS (ns)"),
    ("hold_wns",          "Hold WNS"),
    ("core_area",         "Core um^2"),
    ("utilization",       "Util %"),
    ("total_power_uW",    "Power uW"),
    ("synth_cells",       "Cells"),
    ("total_vias",        "Vias"),
    ("drc_violations",    "DRC"),
    ("lvs_clean",         "LVS"),
    ("gds_path",          "GDS"),
]


def print_table(data: dict):
    """Print a comparison table from parsed run data."""
    if not data:
        print("No runs to compare.")
        return

    # Determine active columns (skip all-None columns)
    active = []
    for key, label in DISPLAY_COLS:
        has_data = any(
            v.get(key) is not None for v in data.values() if isinstance(v, dict)
        )
        if has_data:
            active.append((key, label))

    # Header
    widths = [max(len(label), 8) for _, label in active]
    header = "".join(f"{label:>{w}}" for (_, label), w in zip(active, widths))
    print(f"\n{'Run':<30}" + header)
    print("-" * (30 + len(header)))

    # Rows
    for name, vals in data.items():
        if not isinstance(vals, dict) or "error" in vals:
            print(f"{name:<30} {'ERROR':>{len(header)}}")
            continue
        row = ""
        for (key, label), w in zip(active, widths):
            v = vals.get(key)
            if v is None:
                cell = "N/A"
            elif isinstance(v, bool):
                cell = "Y" if v else "N"
            elif isinstance(v, float):
                cell = f"{v:.2f}"
            elif isinstance(v, str):
                cell = os.path.basename(v)[:w]
            else:
                cell = str(v)
            row += f"{cell:>{w}}"
        print(f"{name:<30}{row}")


def save_json(data: dict, path: str):
    """Save parsed data to JSON."""
    # Convert paths to relative for portability
    cleaned = {}
    for name, vals in data.items():
        if isinstance(vals, dict):
            cleaned[name] = {
                k: (os.path.basename(v) if isinstance(v, str) and os.sep in v else v)
                for k, v in vals.items()
            }
        else:
            cleaned[name] = vals
    with open(path, "w") as f:
        json.dump(cleaned, f, indent=2)
    print(f"Saved to {path}")


# ------------------------------------------------------------------
# Best-config recommendation
# ------------------------------------------------------------------
def recommend_best(data: dict) -> str:
    """Recommend the best configuration from parsed runs.
    
    Priority: 1) timing met, 2) lowest power, 3) smallest area.
    """
    candidates = []
    for name, vals in data.items():
        if not isinstance(vals, dict) or vals.get("flow_complete") is False:
            continue
        candidates.append((name, vals))

    if not candidates:
        return "No completed runs found."

    # Filter to timing-clean first
    clean = [(n, v) for n, v in candidates if v.get("wns") is not None and v["wns"] >= 0]
    if not clean:
        # No timing-clean runs — recommend the one with least violation
        best = min(candidates, key=lambda x: abs(x[1].get("wns") or 999))
        return (
            f"Best: {best[0]} (least timing violation, WNS={best[1].get('wns', 'N/A')} ns). "
            f"Consider increasing clock period or adding pipeline stages."
        )

    # Among clean runs, prefer lowest power then smallest area
    def sort_key(item):
        _, v = item
        power = v.get("total_power_uW") or 999999
        area = v.get("core_area") or 999999
        return (power, area)

    best = min(clean, key=sort_key)
    return (
        f"Best: {best[0]} "
        f"(WNS={best[1].get('wns', 'N/A')} ns, "
        f"Power={best[1].get('total_power_uW', 'N/A')} uW, "
        f"Area={best[1].get('core_area', 'N/A')} um^2)"
    )


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parse_reports.py <run_dir1> [run_dir2 ...]")
        print("       python parse_reports.py --openlane <ol_run1> [ol_run2 ...]")
        sys.exit(1)

    mode = "openlane" if sys.argv[1] == "--openlane" else "flat"
    dirs = sys.argv[2:] if mode == "openlane" else sys.argv[1:]

    runs = {}
    for d in dirs:
        name = os.path.basename(d.rstrip("/\\"))
        runs[name] = d

    if mode == "openlane":
        data = compare_runs(runs)
    else:
        data = {n: parse_flat_run(d) for n, d in runs.items()}

    print_table(data)
    save_json(data, "metrics.json")

    # Best-config recommendation
    if mode == "openlane":
        print(f"\n{recommend_best(data)}")
