# OpenMAC-PD Constraint Generator
# Generates SDC constraints for a given configuration

import argparse
import os

def generate_sdc(width, array_size, clock_period, output_dir):
    acc_width = width * 2 + (array_size.bit_length() - 1) if array_size > 1 else width * 2

    sdc_content = f"""# Auto-generated SDC for MAC (W={width}, A={array_size})
create_clock -name clk -period {clock_period} [get_ports clk]
set_clock_uncertainty 0.2 [get_clocks clk]
set_clock_transition 0.1 [get_clocks clk]

set_input_delay -max [expr {clock_period} * 0.4] -clock clk [remove_from_collection [all_inputs] [get_ports clk]]
set_input_delay -min 0.5 -clock clk [remove_from_collection [all_inputs] [get_ports clk]]

set_output_delay -max [expr {clock_period} * 0.4] -clock clk [all_outputs]
set_output_delay -min 0.5 -clock clk [all_outputs]

set_driving_cell -lib_cell buf_1 [remove_from_collection [all_inputs] [get_ports clk]]
set_load 0.05 [all_outputs]
"""

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"mac_W{width}_A{array_size}.sdc")
    with open(path, 'w') as f:
        f.write(sdc_content)
    print(f"SDC: {path}")
    return path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--array-size", type=int, default=4)
    parser.add_argument("--clock-period", type=float, default=10.0)
    parser.add_argument("--output-dir", default="runs")
    args = parser.parse_args()

    generate_sdc(args.width, args.array_size, args.clock_period, args.output_dir)
