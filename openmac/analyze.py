"""OpenMAC-PD Timing Violation Analyzer (PRD Module 9).

Reads timing/area/power reports from a run directory and produces:
- Setup/hold violation identification
- Critical-path analysis
- Congestion detection
- Actionable suggestions for fixing violations
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TimingViolation:
    type: str  # "setup" or "hold"
    path: str
    slack: float
    endpoint: str = ""
    startpoint: str = ""
    fanout: int = 0


@dataclass
class AnalysisResult:
    run_dir: str
    design_name: str = ""

    # Timing
    wns_setup: Optional[float] = None
    tns_setup: Optional[float] = None
    wns_hold: Optional[float] = None
    tns_hold: Optional[float] = None
    critical_path_delay: Optional[float] = None

    # Area
    cell_area: Optional[float] = None
    core_area: Optional[float] = None
    utilization: Optional[float] = None

    # Power
    total_power: Optional[float] = None
    leakage_power: Optional[float] = None
    dynamic_power: Optional[float] = None

    # DRC / routing
    drc_count: Optional[int] = None
    routing_violations: Optional[int] = None

    # Violations found
    setup_violations: list[TimingViolation] = field(default_factory=list)
    hold_violations: list[TimingViolation] = field(default_factory=list)

    # Suggestions
    suggestions: list[str] = field(default_factory=list)

    def has_violations(self) -> bool:
        return bool(self.setup_violations or self.hold_violations)

    def to_dict(self) -> dict:
        return {
            "design_name": self.design_name,
            "wns_setup": self.wns_setup,
            "tns_setup": self.tns_setup,
            "wns_hold": self.wns_hold,
            "tns_hold": self.tns_hold,
            "critical_path_delay": self.critical_path_delay,
            "cell_area": self.cell_area,
            "core_area": self.core_area,
            "utilization": self.utilization,
            "total_power": self.total_power,
            "leakage_power": self.leakage_power,
            "dynamic_power": self.dynamic_power,
            "drc_count": self.drc_count,
            "routing_violations": self.routing_violations,
            "setup_violation_count": len(self.setup_violations),
            "hold_violation_count": len(self.hold_violations),
            "suggestions": self.suggestions,
        }


# ------------------------------------------------------------------
# Report parsers
# ------------------------------------------------------------------
def _parse_setup_rpt(path: str) -> dict:
    """Parse OpenROAD timing report (setup checks)."""
    result = {}
    if not os.path.exists(path):
        return result

    with open(path) as f:
        text = f.read()

    # WNS
    m = re.search(r"worst slack\s+(-?\d+\.?\d*)", text, re.IGNORECASE)
    if m:
        result["wns"] = float(m.group(1))

    # TNS
    m = re.search(r"total slack\s+(-?\d+\.?\d*)", text, re.IGNORECASE)
    if m:
        result["tns"] = float(m.group(1))

    # Count violations (lines with negative slack)
    violations = re.findall(r"slack\s+(-\d+\.?\d*)", text, re.IGNORECASE)
    result["violation_count"] = len([v for v in violations if float(v) < 0])

    # Critical path delay (approximate from the path)
    m = re.search(r"data arrival time\s+(\d+\.?\d*)", text, re.IGNORECASE)
    if m:
        result["critical_path_delay"] = float(m.group(1))

    return result


def _parse_hold_rpt(path: str) -> dict:
    """Parse OpenROAD timing report (hold checks)."""
    result = {}
    if not os.path.exists(path):
        return result

    with open(path) as f:
        text = f.read()

    m = re.search(r"worst slack\s+(-?\d+\.?\d*)", text, re.IGNORECASE)
    if m:
        result["wns_hold"] = float(m.group(1))

    m = re.search(r"total slack\s+(-?\d+\.?\d*)", text, re.IGNORECASE)
    if m:
        result["tns_hold"] = float(m.group(1))

    return result


def _parse_area_rpt(path: str) -> dict:
    result = {}
    if not os.path.exists(path):
        return result

    with open(path) as f:
        text = f.read()

    for key, pattern in [
        ("cell_area", r"Combinational area\s*:\s*(\d+\.?\d*)"),
        ("core_area", r"Core area\s*:\s*(\d+\.?\d*)"),
        ("utilization", r"Utilization\s*:\s*(\d+\.?\d*)"),
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            result[key] = float(m.group(1))

    if "cell_area" not in result:
        m = re.search(r"Chip area\s*:\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if m:
            result["cell_area"] = float(m.group(1))

    return result


def _parse_power_rpt(path: str) -> dict:
    result = {}
    if not os.path.exists(path):
        return result

    with open(path) as f:
        text = f.read()

    for key, pattern in [
        ("total_power", r"Total\s+(\d+\.?\d*)"),
        ("dynamic_power", r"Dynamic\s+(\d+\.?\d*)"),
        ("leakage_power", r"Leakage\s+(\d+\.?\d*)"),
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            result[key] = float(m.group(1))

    return result


def _parse_stat_rpt(path: str) -> dict:
    """Parse yosys stat.rpt for cell count."""
    result = {}
    if not os.path.exists(path):
        return result

    with open(path) as f:
        text = f.read()

    m = re.search(r"Number of cells\s*:\s*(\d+)", text)
    if m:
        result["yosys_cells"] = int(m.group(1))

    return result


# ------------------------------------------------------------------
# Suggestion engine
# ------------------------------------------------------------------
def _generate_suggestions(result: AnalysisResult) -> list[str]:
    suggestions = []

    if result.wns_setup is not None and result.wns_setup < 0:
        suggestions.append(
            f"SETUP VIOLATION: WNS={result.wns_setup:.3f}ns. "
            "Increase clock period (currently "
            f"{result.critical_path_delay:.1f}ns path delay) or "
            "add a pipeline stage."
        )

    if result.wns_hold is not None and result.wns_hold < 0:
        suggestions.append(
            f"HOLD VIOLATION: WNS={result.wns_hold:.3f}ns. "
            "Add buffer insertion or increase hold margin."
        )

    if result.utilization is not None and result.utilization > 80:
        suggestions.append(
            f"HIGH UTILIZATION: {result.utilization:.1f}%. "
            "Reduce utilization to 50-70% to relieve congestion."
        )

    if result.routing_violations is not None and result.routing_violations > 0:
        suggestions.append(
            f"ROUTING VIOLATIONS: {result.routing_violations}. "
            "Check congestion, increase routing layers, or simplify floorplan."
        )

    if result.drc_count is not None and result.drc_count > 0:
        suggestions.append(
            f"DRC VIOLATIONS: {result.drc_count}. "
            "Review antenna, metal density, and spacing violations."
        )

    if not suggestions:
        suggestions.append("No timing violations detected. Design is clean.")

    return suggestions


# ------------------------------------------------------------------
# Main analysis function
# ------------------------------------------------------------------
def analyze_run(run_dir: str) -> AnalysisResult:
    """Analyze all reports in a run directory."""
    result = AnalysisResult(run_dir=run_dir)
    result.design_name = os.path.basename(run_dir)

    reports_dir = os.path.join(run_dir, "reports")
    if not os.path.isdir(reports_dir):
        # Try flat layout (reports directly in run_dir)
        reports_dir = run_dir

    # Find and parse timing reports
    for fname in os.listdir(reports_dir):
        fpath = os.path.join(reports_dir, fname)
        if not os.path.isfile(fpath):
            continue

        if "setup" in fname.lower():
            data = _parse_setup_rpt(fpath)
            if "wns" in data:
                result.wns_setup = data["wns"]
            if "tns" in data:
                result.tns_setup = data["tns"]
            if "violation_count" in data:
                result.setup_violations = [
                    TimingViolation(type="setup", path=fpath, slack=0)
                    for _ in range(data["violation_count"])
                ]
            if "critical_path_delay" in data:
                result.critical_path_delay = data["critical_path_delay"]

        elif "hold" in fname.lower():
            data = _parse_hold_rpt(fpath)
            if "wns_hold" in data:
                result.wns_hold = data["wns_hold"]
            if "tns_hold" in data:
                result.tns_hold = data["tns_hold"]

        elif "area" in fname.lower():
            data = _parse_area_rpt(fpath)
            result.__dict__.update(
                {k: v for k, v in data.items() if v is not None}
            )

        elif "power" in fname.lower():
            data = _parse_power_rpt(fpath)
            result.__dict__.update(
                {k: v for k, v in data.items() if v is not None}
            )

        elif "congestion" in fname.lower():
            with open(fpath) as f:
                text = f.read()
            m = re.search(r"number of violations\s*:\s*(\d+)", text, re.IGNORECASE)
            if m:
                result.routing_violations = int(m.group(1))

    # Check for stat.rpt (yosys)
    stat_path = os.path.join(run_dir, "stat.rpt")
    if os.path.exists(stat_path):
        data = _parse_stat_rpt(stat_path)
        result.__dict__.update(data)

    result.suggestions = _generate_suggestions(result)
    return result


def print_report(result: AnalysisResult):
    """Pretty-print analysis results."""
    print(f"\n{'=' * 60}")
    print(f"  Timing Violation Analysis: {result.design_name}")
    print(f"{'=' * 60}")

    if result.wns_setup is not None:
        print(f"  Setup WNS:  {result.wns_setup:.3f} ns")
    if result.tns_setup is not None:
        print(f"  Setup TNS:  {result.tns_setup:.3f} ns")
    if result.wns_hold is not None:
        print(f"  Hold  WNS:  {result.wns_hold:.3f} ns")
    if result.tns_hold is not None:
        print(f"  Hold  TNS:  {result.tns_hold:.3f} ns")
    if result.critical_path_delay is not None:
        print(f"  Critical Path: {result.critical_path_delay:.3f} ns")

    print(f"\n  Cell Area:   {result.cell_area or 'N/A'}")
    print(f"  Utilization: {result.utilization or 'N/A'}")
    print(f"  Total Power: {result.total_power or 'N/A'} mW")

    if result.setup_violations:
        print(f"\n  Setup violations: {len(result.setup_violations)}")
    if result.hold_violations:
        print(f"  Hold violations:  {len(result.hold_violations)}")

    print(f"\n  Suggestions:")
    for s in result.suggestions:
        print(f"    - {s}")
    print(f"{'=' * 60}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="OpenMAC-PD timing violation analyzer")
    parser.add_argument("run_dirs", nargs="+", help="Run directories to analyze")
    args = parser.parse_args()

    all_results = []
    for d in args.run_dirs:
        result = analyze_run(d)
        print_report(result)
        all_results.append(result.to_dict())

    out_path = "analysis_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
