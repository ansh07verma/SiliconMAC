# OpenMAC-PD Dashboard Generator
# Creates PPA comparison charts and HTML dashboard from parsed metrics

import json
import os

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def generate_dashboard(metrics_file="metrics.json", output_dir="reports"):
    """Generate HTML + PNG dashboard from metrics.json."""
    if not os.path.exists(metrics_file):
        print(f"No metrics file: {metrics_file}")
        return

    with open(metrics_file) as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    # ---- HTML dashboard ----
    html_rows = ""
    for run, m in data.items():
        html_rows += "<tr>"
        html_rows += f"<td>{run}</td>"
        for key in ["wns", "tns", "hold_wns", "core_area", "utilization",
                     "total_power_uW", "synth_cells", "drc_violations", "lvs_clean"]:
            val = m.get(key)
            if val is None:
                html_rows += "<td>N/A</td>"
            elif isinstance(val, bool):
                html_rows += f"<td>{'Y' if val else 'N'}</td>"
            elif isinstance(val, float):
                html_rows += f"<td>{val:.2f}</td>"
            else:
                html_rows += f"<td>{val}</td>"
        html_rows += "</tr>\n"

    html = f"""<!DOCTYPE html>
<html><head><title>OpenMAC-PD PPA Dashboard</title>
<style>
body {{ font-family: monospace; margin: 40px; background: #1a1a2e; color: #e0e0e0; }}
h1 {{ color: #00d4ff; }}
table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
th {{ background: #16213e; color: #00d4ff; border: 1px solid #333; padding: 10px; text-align: right; }}
td {{ border: 1px solid #333; padding: 8px; text-align: right; }}
tr:nth-child(even) {{ background: #16213e; }}
tr:hover {{ background: #0f3460; }}
.pass {{ color: #00ff88; }}
.fail {{ color: #ff4444; }}
.summary {{ background: #16213e; padding: 15px; border-radius: 8px; margin: 20px 0; }}
</style></head><body>
<h1>OpenMAC-PD PPA Dashboard</h1>
<div class="summary">
<p>Design Space Exploration Results</p>
<p>Configs compared: {len(data)}</p>
</div>
<table><tr>
<th>Run</th><th>WNS (ns)</th><th>TNS (ns)</th><th>Hold WNS</th>
<th>Core Area</th><th>Util %</th><th>Power (uW)</th>
<th>Cells</th><th>DRC</th><th>LVS</th>
</tr>
{html_rows}</table>

<h2>Best Configuration</h2>
<div class="summary" id="best">
{ _recommend_best_html(data) }
</div>
</body></html>"""

    with open(os.path.join(output_dir, "dashboard.html"), "w") as f:
        f.write(html)
    print(f"Dashboard: {output_dir}/dashboard.html")

    # ---- Matplotlib charts ----
    if HAS_MPL and data:
        labels = list(data.keys())
        metrics_to_plot = {
            "wns": "Worst Negative Slack (ns)",
            "total_power_uW": "Total Power (uW)",
            "core_area": "Core Area (um^2)",
        }

        n_plots = len(metrics_to_plot)
        fig, axes = plt.subplots(1, n_plots, figsize=(6 * n_plots, 5))
        if n_plots == 1:
            axes = [axes]

        for ax, (key, title) in zip(axes, metrics_to_plot.items()):
            vals = []
            valid_labels = []
            for l in labels:
                v = data[l].get(key)
                if v is not None:
                    vals.append(v)
                    valid_labels.append(l)

            if vals:
                colors = []
                for v in vals:
                    if key == "wns":
                        colors.append("red" if v < 0 else "#00ff88")
                    else:
                        colors.append("#00d4ff")
                ax.bar(valid_labels, vals, color=colors)
                ax.set_title(title, color="#e0e0e0")
                ax.tick_params(axis="x", rotation=45, colors="#e0e0e0")
                ax.tick_params(axis="y", colors="#e0e0e0")
                ax.axhline(0, color="white", linewidth=0.5)
                ax.set_facecolor("#16213e")

        fig.patch.set_facecolor("#1a1a2e")
        plt.tight_layout()
        path = os.path.join(output_dir, "ppa_charts.png")
        plt.savefig(path, dpi=150, facecolor="#1a1a2e")
        print(f"Charts: {path}")


def _recommend_best_html(data: dict) -> str:
    """Return HTML string for best-config recommendation."""
    candidates = []
    for name, vals in data.items():
        if isinstance(vals, dict) and vals.get("flow_complete", True):
            candidates.append((name, vals))

    if not candidates:
        return "<p>No completed runs found.</p>"

    # Timing-clean candidates
    clean = [(n, v) for n, v in candidates if v.get("wns") is not None and v["wns"] >= 0]

    if clean:
        best = min(clean, key=lambda x: (x[1].get("total_power_uW") or 999999))
        return (
            f"<p class='pass'><strong>{best[0]}</strong> is the best configuration:</p>"
            f"<ul>"
            f"<li>WNS: {best[1].get('wns', 'N/A')} ns (timing clean)</li>"
            f"<li>Power: {best[1].get('total_power_uW', 'N/A')} uW</li>"
            f"<li>Area: {best[1].get('core_area', 'N/A')} um^2</li>"
            f"</ul>"
        )
    else:
        best = min(candidates, key=lambda x: abs(x[1].get("wns") or 999))
        return (
            f"<p class='fail'><strong>{best[0]}</strong> has least timing violation:</p>"
            f"<ul><li>WNS: {best[1].get('wns', 'N/A')} ns</li></ul>"
            f"<p>Consider increasing clock period or adding pipeline stages.</p>"
        )


if __name__ == "__main__":
    generate_dashboard()
