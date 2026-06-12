"""Tests for OpenMAC-PD timing violation analyzer (openmac/analyze.py)."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openmac.analyze import (
    AnalysisResult,
    TimingViolation,
    analyze_run,
    _parse_setup_rpt,
    _parse_hold_rpt,
    _parse_area_rpt,
    _parse_power_rpt,
    _parse_stat_rpt,
    _generate_suggestions,
)


def test_analysis_result_defaults():
    """AnalysisResult has sensible defaults."""
    r = AnalysisResult(run_dir="/tmp/test")
    assert r.wns_setup is None
    assert not r.has_violations()
    d = r.to_dict()
    assert d["wns_setup"] is None
    assert d["cell_area"] is None


def test_has_violations():
    """has_violations returns True when violations exist."""
    r = AnalysisResult(run_dir="/tmp")
    assert not r.has_violations()

    r.setup_violations.append(
        TimingViolation(type="setup", path="/tmp/setup.rpt", slack=-0.5)
    )
    assert r.has_violations()


def test_generate_suggestions_no_violations():
    """Clean design gets a positive suggestion."""
    r = AnalysisResult(run_dir="/tmp")
    r.wns_setup = 1.0
    s = _generate_suggestions(r)
    assert len(s) == 1
    assert "No timing violations" in s[0]


def test_generate_suggestions_setup_violation():
    """Setup violation triggers clock period suggestion."""
    r = AnalysisResult(run_dir="/tmp")
    r.wns_setup = -0.25
    r.critical_path_delay = 10.25
    s = _generate_suggestions(r)
    assert any("SETUP VIOLATION" in x for x in s)


def test_generate_suggestions_hold_violation():
    """Hold violation triggers buffer suggestion."""
    r = AnalysisResult(run_dir="/tmp")
    r.wns_hold = -0.1
    s = _generate_suggestions(r)
    assert any("HOLD VIOLATION" in x for x in s)


def test_generate_suggestions_high_utilization():
    """High utilization triggers congestion suggestion."""
    r = AnalysisResult(run_dir="/tmp")
    r.utilization = 85.0
    s = _generate_suggestions(r)
    assert any("HIGH UTILIZATION" in x for x in s)


def test_generate_suggestions_routing_violations():
    """Routing violations trigger routing suggestion."""
    r = AnalysisResult(run_dir="/tmp")
    r.routing_violations = 5
    s = _generate_suggestions(r)
    assert any("ROUTING VIOLATIONS" in x for x in s)


def test_parse_setup_rpt():
    """Parse setup report with slack."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rpt", delete=False) as f:
        f.write("worst slack -0.25\ntotal slack -1.5\n")
        f.flush()
        result = _parse_setup_rpt(f.name)
        assert result["wns"] == -0.25
        assert result["tns"] == -1.5
    os.unlink(f.name)


def test_parse_area_rpt():
    """Parse area report."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rpt", delete=False) as f:
        f.write("Combinational area : 1234.5\nCore area : 5678.9\n")
        f.flush()
        result = _parse_area_rpt(f.name)
        assert result["cell_area"] == 1234.5
        assert result["core_area"] == 5678.9
    os.unlink(f.name)


def test_parse_power_rpt():
    """Parse power report."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rpt", delete=False) as f:
        f.write("Total 1.23 mW\nDynamic 0.98 mW\nLeakage 0.25 mW\n")
        f.flush()
        result = _parse_power_rpt(f.name)
        assert result["total_power"] == 1.23
        assert result["dynamic_power"] == 0.98
        assert result["leakage_power"] == 0.25
    os.unlink(f.name)


def test_parse_stat_rpt():
    """Parse yosys stat.rpt."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rpt", delete=False) as f:
        f.write("Number of cells : 632\nNumber of wires : 605\n")
        f.flush()
        result = _parse_stat_rpt(f.name)
        assert result["yosys_cells"] == 632
    os.unlink(f.name)


def test_parse_missing_file():
    """Parsing missing file returns empty dict."""
    assert _parse_setup_rpt("/nonexistent.rpt") == {}
    assert _parse_hold_rpt("/nonexistent.rpt") == {}
    assert _parse_area_rpt("/nonexistent.rpt") == {}
    assert _parse_power_rpt("/nonexistent.rpt") == {}
    assert _parse_stat_rpt("/nonexistent.rpt") == {}


def test_analyze_run_empty_dir():
    """Analyzing an empty directory doesn't crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = analyze_run(tmpdir)
        assert result.wns_setup is None
        assert result.suggestions == ["No timing violations detected. Design is clean."]


def test_analyze_run_with_stat_rpt():
    """Analyzing a dir with stat.rpt picks up yosys_cells."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "stat.rpt"), "w") as f:
            f.write("Number of cells : 632\n")
        result = analyze_run(tmpdir)
        assert getattr(result, "yosys_cells", None) == 632


def test_to_dict():
    """to_dict produces a JSON-serializable dict."""
    r = AnalysisResult(run_dir="/tmp", wns_setup=-0.3, cell_area=1000.0)
    d = r.to_dict()
    assert d["wns_setup"] == -0.3
    assert d["cell_area"] == 1000.0
    assert isinstance(d["suggestions"], list)
