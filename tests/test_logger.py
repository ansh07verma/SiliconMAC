"""Tests for OpenMAC-PD logging framework (openmac/logger.py)."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openmac.logger import FlowLogger, StageStatus, StageRecord


def test_stage_lifecycle():
    """Stage goes PENDING -> RUNNING -> PASS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FlowLogger(tmpdir, "test_run")

        log.stage_start("synthesis")
        assert log.stages["synthesis"].status == StageStatus.RUNNING

        log.stage_ok("synthesis", cells=632)
        assert log.stages["synthesis"].status == StageStatus.PASS
        assert log.stages["synthesis"].metrics["cells"] == 632

        log.close()


def test_stage_fail():
    """Stage FAIL records error message."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FlowLogger(tmpdir, "test_run")

        log.stage_start("openroad")
        log.stage_fail("openroad", "PDK not found")
        assert log.stages["openroad"].status == StageStatus.FAIL
        assert "PDK" in log.stages["openroad"].message

        log.close()


def test_stage_skip():
    """Stage SKIP with reason."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FlowLogger(tmpdir, "test_run")

        log.stage_skip("magic", "not installed")
        assert log.stages["magic"].status == StageStatus.SKIP

        log.close()


def test_summary_json():
    """summary_json produces valid structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FlowLogger(tmpdir, "test_run")

        log.stage_start("a")
        log.stage_ok("a", x=1)
        log.stage_start("b")
        log.stage_fail("b", "err")

        summary = log.summary_json()
        assert summary["run_name"] == "test_run"
        assert summary["stages"]["a"]["status"] == "pass"
        assert summary["stages"]["b"]["status"] == "fail"
        assert summary["verdict"] == "fail"

        log.close()


def test_save_summary():
    """save_summary writes JSON to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FlowLogger(tmpdir, "test_run")
        log.stage_start("syn")
        log.stage_ok("syn")

        log.save_summary()
        summary_path = os.path.join(tmpdir, "summary.json")
        assert os.path.exists(summary_path)

        with open(summary_path) as f:
            data = json.load(f)
        assert data["stages"]["syn"]["status"] == "pass"

        log.close()


def test_per_stage_logs():
    """Per-stage log files are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FlowLogger(tmpdir, "test_run")
        log.stage_start("synthesis")
        log.stage_ok("synthesis")

        stage_log = os.path.join(tmpdir, "logs", "synthesis.txt")
        assert os.path.exists(stage_log)
        with open(stage_log) as f:
            content = f.read()
        assert "STARTED" in content
        assert "PASS" in content

        log.close()


def test_combined_log():
    """run.log contains all stage events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FlowLogger(tmpdir, "test_run")
        log.stage_start("a")
        log.stage_ok("a")
        log.stage_start("b")
        log.stage_fail("b", "oops")
        log.summary()

        log_path = os.path.join(tmpdir, "run.log")
        assert os.path.exists(log_path)
        with open(log_path) as f:
            content = f.read()
        assert "a Started" in content
        assert "a Complete" in content
        assert "b FAILED" in content

        log.close()


def test_context_manager():
    """FlowLogger works as context manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with FlowLogger(tmpdir, "ctx_test") as log:
            log.stage_start("x")
            log.stage_ok("x")
        assert log._log_fp.closed


def test_stage_record_elapsed():
    """StageRecord.elapsed_str returns sensible strings."""
    rec = StageRecord(name="test")
    assert rec.elapsed_str() == "n/a"

    rec.start_time = 100.0
    rec.end_time = 100.5
    rec.duration_s = 0.5
    assert rec.elapsed_str() == "500ms"

    rec.duration_s = 3.5
    assert rec.elapsed_str() == "3.5s"


def test_custom_metrics():
    """Multiple metrics are recorded correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FlowLogger(tmpdir, "test_run")
        log.stage_start("syn")
        log.stage_ok("syn", cells=632, wires=605, area=1234.5)
        assert log.stages["syn"].metrics["cells"] == 632
        assert log.stages["syn"].metrics["wires"] == 605
        assert log.stages["syn"].metrics["area"] == 1234.5
        log.close()
