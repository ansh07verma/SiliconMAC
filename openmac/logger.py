"""OpenMAC-PD Logging Framework (PRD Module 11).

Provides timestamped, stage-aware logging with per-stage log files
and a combined run.log. Tracks success/failure status per stage.
"""

import datetime
import json
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class StageRecord:
    name: str
    status: StageStatus = StageStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_s: Optional[float] = None
    message: str = ""
    metrics: dict = field(default_factory=dict)

    def elapsed_str(self) -> str:
        if self.duration_s is None:
            return "n/a"
        if self.duration_s < 1:
            return f"{self.duration_s*1000:.0f}ms"
        return f"{self.duration_s:.1f}s"


class FlowLogger:
    """Central logger that writes to a combined run.log + per-stage files.

    Usage::

        log = FlowLogger("runs/W8_A4")
        log.stage_start("synthesis")
        log.stage_ok("synthesis", cells=632, netlist="runs/.../mac_core_syn.v")
        log.stage_start("openroad")
        log.stage_fail("openroad", "PDK_ROOT not set")
        log.summary()
        log.close()
    """

    def __init__(self, run_dir: str, run_name: str = ""):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.run_name = run_name or self.run_dir.name
        self.stages: dict[str, StageRecord] = {}
        self._run_start = time.time()

        # Combined log
        self._log_path = self.run_dir / "run.log"
        self._log_fp = open(self._log_path, "w")

        # Per-stage log files go into a logs/ subdirectory
        self._logs_dir = self.run_dir / "logs"
        self._logs_dir.mkdir(exist_ok=True)

        self._info(f"Run '{self.run_name}' started")
        self._info(f"Log: {self._log_path}")
        self._info(f"Stage logs: {self._logs_dir}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ts(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _info(self, msg: str):
        line = f"[{self._ts()}] {msg}"
        print(line, file=self._log_fp, flush=True)

    def _stage_log_path(self, stage: str) -> Path:
        safe = stage.replace(" ", "_").replace("/", "_")
        return self._logs_dir / f"{safe}.txt"

    # ------------------------------------------------------------------
    # Stage lifecycle
    # ------------------------------------------------------------------
    def stage_start(self, name: str):
        rec = StageRecord(name=name, status=StageStatus.RUNNING, start_time=time.time())
        self.stages[name] = rec
        self._info(f"[INFO] {name} Started")
        # Write to per-stage file
        with open(self._stage_log_path(name), "w") as f:
            f.write(f"[{self._ts()}] STARTED\n")

    def stage_ok(self, name: str, message: str = "", **metrics):
        rec = self.stages.get(name)
        if rec is None:
            rec = StageRecord(name=name, status=StageStatus.RUNNING, start_time=time.time())
            self.stages[name] = rec
        rec.status = StageStatus.PASS
        rec.end_time = time.time()
        rec.duration_s = rec.end_time - (rec.start_time or rec.end_time)
        rec.message = message
        rec.metrics.update(metrics)
        self._info(f"[INFO] {name} Complete ({rec.elapsed_str()})")
        if metrics:
            self._info(f"[INFO]   metrics: {json.dumps(metrics)}")
        with open(self._stage_log_path(name), "a") as f:
            f.write(f"[{self._ts()}] PASS ({rec.elapsed_str()})\n")
            if metrics:
                f.write(f"  metrics: {json.dumps(metrics, indent=2)}\n")

    def stage_fail(self, name: str, message: str = "", **metrics):
        rec = self.stages.get(name)
        if rec is None:
            rec = StageRecord(name=name, status=StageStatus.RUNNING, start_time=time.time())
            self.stages[name] = rec
        rec.status = StageStatus.FAIL
        rec.end_time = time.time()
        rec.duration_s = rec.end_time - (rec.start_time or rec.end_time)
        rec.message = message
        rec.metrics.update(metrics)
        self._info(f"[ERROR] {name} FAILED ({rec.elapsed_str()}): {message}")
        with open(self._stage_log_path(name), "a") as f:
            f.write(f"[{self._ts()}] FAIL ({rec.elapsed_str()}): {message}\n")

    def stage_skip(self, name: str, reason: str = ""):
        rec = StageRecord(name=name, status=StageStatus.SKIP, end_time=time.time())
        self.stages[name] = rec
        self._info(f"[INFO] {name} SKIPPED: {reason}")
        with open(self._stage_log_path(name), "a") as f:
            f.write(f"[{self._ts()}] SKIP: {reason}\n")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def summary(self) -> str:
        total = time.time() - self._run_start
        lines = []
        lines.append("")
        lines.append("=" * 60)
        lines.append(f"  OpenMAC-PD Run Summary: {self.run_name}")
        lines.append("=" * 60)

        all_pass = True
        for name, rec in self.stages.items():
            icon = {"pass": "OK", "fail": "FAIL", "skip": "SKIP", "running": "...", "pending": ".."}.get(
                rec.status.value, "?"
            )
            line = f"  [{icon:>4}] {name:<20} {rec.elapsed_str():>8}"
            if rec.message:
                line += f"  {rec.message}"
            lines.append(line)
            if rec.status == StageStatus.FAIL:
                all_pass = False

        lines.append("-" * 60)
        verdict = "ALL PASSED" if all_pass else "FAILED"
        lines.append(f"  Total: {total:.1f}s  |  Verdict: {verdict}")
        lines.append("=" * 60)

        text = "\n".join(lines)
        print(text)
        self._info(f"Summary: {verdict} (total {total:.1f}s)")
        return text

    def summary_json(self) -> dict:
        total = time.time() - self._run_start
        stages = {}
        for name, rec in self.stages.items():
            stages[name] = {
                "status": rec.status.value,
                "duration_s": rec.duration_s,
                "message": rec.message,
                "metrics": rec.metrics,
            }
        return {
            "run_name": self.run_name,
            "total_duration_s": total,
            "stages": stages,
            "verdict": "pass" if all(
                s["status"] in ("pass", "skip") for s in stages.values()
            ) else "fail",
        }

    def save_summary(self, path: str = ""):
        p = Path(path) if path else self.run_dir / "summary.json"
        with open(p, "w") as f:
            json.dump(self.summary_json(), f, indent=2)

    def close(self):
        if self._log_fp and not self._log_fp.closed:
            self._log_fp.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def main():
    """CLI demo: create a log, run a fake stage, print summary."""
    import argparse

    parser = argparse.ArgumentParser(description="OpenMAC-PD logger demo")
    parser.add_argument("--run-dir", default="runs/demo")
    args = parser.parse_args()

    with FlowLogger(args.run_dir, "demo") as log:
        log.stage_start("synthesis")
        time.sleep(0.1)
        log.stage_ok("synthesis", cells=632, netlist="runs/demo/mac_core_syn.v")

        log.stage_start("openroad")
        time.sleep(0.05)
        log.stage_fail("openroad", "PDK_ROOT not set")

        log.summary()
        log.save_summary()


if __name__ == "__main__":
    main()
