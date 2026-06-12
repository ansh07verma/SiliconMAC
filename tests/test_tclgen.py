"""Tests for OpenMAC-PD TCL generator (openmac/tclgen.py)."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openmac.tclgen import FlowConfig, gen_sdc, write_sdc, gen_openroad_flow, gen_yosys_script, generate_all


def test_flow_config_defaults():
    """FlowConfig has sensible defaults."""
    cfg = FlowConfig()
    assert cfg.width == 8
    assert cfg.array_size == 4
    assert cfg.clock_period == 10.0
    assert cfg.utilization == 60
    assert cfg.design_name == "mac_core_W8_A4"
    assert cfg.syn_dir == "runs/syn_W8_A4"


def test_flow_config_custom():
    """FlowConfig with custom values."""
    cfg = FlowConfig(width=16, array_size=8, clock_period=5.0)
    assert cfg.design_name == "mac_core_W16_A8"
    assert cfg.syn_dir == "runs/syn_W16_A8"
    d = cfg.to_dict()
    assert d["WIDTH"] == 16
    assert d["ARRAY_SIZE"] == 8


def test_gen_sdc_content():
    """gen_sdc produces valid SDC with clock and I/O delays."""
    cfg = FlowConfig(width=8, array_size=4, clock_period=10.0)
    sdc = gen_sdc(cfg)
    assert "create_clock" in sdc
    assert "-period 10.0" in sdc
    assert "set_input_delay" in sdc
    assert "set_output_delay" in sdc
    assert "set_load" in sdc
    assert "mac_core_W8_A4" in sdc


def test_gen_sdc_different_period():
    """SDC uses the configured clock period."""
    cfg = FlowConfig(clock_period=5.0)
    sdc = gen_sdc(cfg)
    assert "-period 5.0" in sdc
    assert "5.0 * 0.4" in sdc


def test_write_sdc():
    """write_sdc creates file on disk."""
    cfg = FlowConfig(width=8, array_size=4)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.sdc")
        result = write_sdc(cfg, path)
        assert os.path.exists(result)
        with open(result) as f:
            content = f.read()
        assert "create_clock" in content


def test_gen_openroad_flow_content():
    """OpenROAD flow script references correct config values."""
    cfg = FlowConfig(width=16, array_size=8, clock_period=5.0, utilization=70)
    script = gen_openroad_flow(cfg)
    assert "mac_core_W16_A8" in script
    assert "set ::env(WIDTH)" in script
    assert "set ::env(ARRAY_SIZE)" in script
    assert "5.0" in script
    assert "initialize_floorplan" in script
    assert "clock_tree_synthesis" in script
    assert "write_verilog" in script


def test_gen_yosys_script():
    """Yosys script includes hierarchy, synth, abc, write_verilog."""
    cfg = FlowConfig(width=8, array_size=4, clock_period=10.0)
    script = gen_yosys_script(cfg)
    assert "read_verilog -sv" in script
    assert "hierarchy -top mac_core" in script
    assert "WIDTH 8" in script
    assert "ARRAY_SIZE 4" in script
    assert "abc -D 10.0" in script
    assert "write_verilog" in script


def test_generate_all():
    """generate_all produces SDC and flow script files."""
    cfg = FlowConfig(width=8, array_size=4, clock_period=10.0)
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = generate_all(cfg, tmpdir)
        assert "sdc" in paths
        assert "openroad_flow" in paths
        assert os.path.exists(paths["sdc"])
        assert os.path.exists(paths["openroad_flow"])


def test_sdc_writes_correct_output_dir():
    """SDC goes into the design subdirectory under output_dir."""
    cfg = FlowConfig(width=16, array_size=8)
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = generate_all(cfg, tmpdir)
        expected_sdc = os.path.join(tmpdir, "mac_core_W16_A8", "mac_core_W16_A8.sdc")
        assert paths["sdc"] == expected_sdc
