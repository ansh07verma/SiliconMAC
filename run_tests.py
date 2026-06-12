#!/usr/bin/env python3
"""Run all OpenMAC-PD tests."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.test_logger import (
    test_stage_lifecycle,
    test_stage_fail,
    test_stage_skip,
    test_summary_json,
    test_save_summary,
    test_per_stage_logs,
    test_combined_log,
    test_context_manager,
    test_stage_record_elapsed,
    test_custom_metrics,
)
from tests.test_tclgen import (
    test_flow_config_defaults,
    test_flow_config_custom,
    test_gen_sdc_content,
    test_gen_sdc_different_period,
    test_write_sdc,
    test_gen_openroad_flow_content,
    test_gen_yosys_script,
    test_generate_all,
    test_sdc_writes_correct_output_dir,
)
from tests.test_analyze import (
    test_analysis_result_defaults,
    test_has_violations,
    test_generate_suggestions_no_violations,
    test_generate_suggestions_setup_violation,
    test_generate_suggestions_hold_violation,
    test_generate_suggestions_high_utilization,
    test_generate_suggestions_routing_violations,
    test_parse_setup_rpt,
    test_parse_area_rpt,
    test_parse_power_rpt,
    test_parse_stat_rpt,
    test_parse_missing_file,
    test_analyze_run_empty_dir,
    test_analyze_run_with_stat_rpt,
    test_to_dict,
)

ALL_TESTS = [
    test_stage_lifecycle,
    test_stage_fail,
    test_stage_skip,
    test_summary_json,
    test_save_summary,
    test_per_stage_logs,
    test_combined_log,
    test_context_manager,
    test_stage_record_elapsed,
    test_custom_metrics,
    test_flow_config_defaults,
    test_flow_config_custom,
    test_gen_sdc_content,
    test_gen_sdc_different_period,
    test_write_sdc,
    test_gen_openroad_flow_content,
    test_gen_yosys_script,
    test_generate_all,
    test_sdc_writes_correct_output_dir,
    test_analysis_result_defaults,
    test_has_violations,
    test_generate_suggestions_no_violations,
    test_generate_suggestions_setup_violation,
    test_generate_suggestions_hold_violation,
    test_generate_suggestions_high_utilization,
    test_generate_suggestions_routing_violations,
    test_parse_setup_rpt,
    test_parse_area_rpt,
    test_parse_power_rpt,
    test_parse_stat_rpt,
    test_parse_missing_file,
    test_analyze_run_empty_dir,
    test_analyze_run_with_stat_rpt,
    test_to_dict,
]

passed = 0
failed = 0
errors = []

for test_fn in ALL_TESTS:
    try:
        test_fn()
        passed += 1
        print(f"  PASS  {test_fn.__name__}")
    except Exception as e:
        failed += 1
        errors.append((test_fn.__name__, e))
        print(f"  FAIL  {test_fn.__name__}: {e}")

print(f"\n{'=' * 50}")
print(f"  Ran {passed + failed} tests: {passed} passed, {failed} failed")
if errors:
    print(f"\n  Failures:")
    for name, err in errors:
        print(f"    {name}: {err}")
print(f"{'=' * 50}")
sys.exit(1 if failed else 0)
