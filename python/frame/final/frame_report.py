# -*- coding: utf-8 -*-
"""
Self-contained HTML calculation report for a PlaneFrame.

AI-ASSISTED APPLICATION LAYER. This module only reads results from the
verified core (frame_model.py) and never computes engineering quantities
of its own. The report deliberately echoes every input, lists the model
assumptions and includes the verification evidence (equilibrium and
analytical benchmarks), so a reviewer can see what was actually computed.

Run ``python frame_report.py`` to write frame_report.html for the default
frame, or ``python frame_report.py --help`` for options. Figures are
embedded as SVG, so the file can be e-mailed, archived and printed.
"""

import argparse
import datetime
import html
import io
import platform
import sys
from importlib.metadata import version
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# The verified core lives in the parent directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from frame_model import PlaneFrame              # noqa: E402
from sections import SECTIONS, STEEL_GRADES     # noqa: E402
from verification import run_benchmarks         # noqa: E402

ASSUMPTIONS = [
    "Linear elastic, first-order analysis (no P-delta, buckling or "
    "lateral-torsional buckling).",
    "Euler-Bernoulli beam elements (CALFEM beam2e) with axial deformation; "
    "shear deformation neglected.",
    "Rigid beam-column connections.",
    "Loads are applied as given; partial factors and load combinations are "
    "not applied by the program.",
    "Utilisation = (|N|/A + |M|/W) / fy is an elastic stress measure, not a "
    "design code verification.",
    "Section properties are nominal table values for strong-axis bending.",
]

COLOR_MEMBER = "#37474f"
COLOR_SUPPORT = "#6d4c41"
COLOR_LOAD = "#c62828"
COLOR_DEFORMED = "#1565c0"
COLOR_POSITIVE = "#c62828"
COLOR_NEGATIVE = "#1565c0"
COLOR_DIAGRAM = "#6a1b9a"


# ----------------------------------------------------------------------
# Geometry helpers shared with the web application
# ----------------------------------------------------------------------

def member_normal(mr):
    """Unit normal (local y axis) of a member result."""
    dx, dy = mr.x[-1] - mr.x[0], mr.y[-1] - mr.y[0]
    L = np.hypot(dx, dy)
    return np.array([-dy / L, dx / L])


def diagram_polygon(mr, values, scale, tension_side=False):
    """
    Closed outline (x, y) of a section-force diagram along a member.

    Values are drawn along the member's local y axis. Bending moments are
    drawn on the tension side, which with CALFEM's M = EI v'' is the -y
    side, so pass tension_side=True for M.
    """
    n = member_normal(mr)
    sign = -1.0 if tension_side else 1.0
    ox = mr.x + sign * scale * values * n[0]
    oy = mr.y + sign * scale * values * n[1]
    x = np.concatenate([[mr.x[0]], ox, [mr.x[-1]]])
    y = np.concatenate([[mr.y[0]], oy, [mr.y[-1]]])
    return x, y


def diagram_scale(frame, key):
    """Scale so the largest |value| is drawn at 30 % of a bay/storey."""
    vmax = max(np.max(np.abs(getattr(m, key))) for m in frame.results.members)
    size = 0.3 * min(frame.bay_width, frame.storey_height)
    return size / vmax if vmax > 0 else 0.0, vmax


def deformation_scale(frame, fraction=0.06):
    """Scale so the largest displacement is drawn at a fraction of the size."""
    umax = max(np.max(np.hypot(m.ux, m.uy)) for m in frame.results.members)
    size = max(frame.width, frame.height)
    return (fraction * size / umax if umax > 0 else 1.0), umax


# ----------------------------------------------------------------------
# Matplotlib figures
# ----------------------------------------------------------------------

def _draw_members(ax, frame, **kw):
    for m in frame.members:
        (x1, y1), (x2, y2) = frame.coords[m.i], frame.coords[m.j]
        ax.plot([x1, x2], [y1, y2], color=kw.get("color", COLOR_MEMBER),
                lw=kw.get("lw", 2.0), solid_capstyle="round", zorder=2)


def _draw_supports(ax, frame):
    size = 0.25 * min(frame.bay_width, frame.storey_height)
    for node, (_, _, fixed_rot) in frame.supports.items():
        x, y = frame.coords[node]
        if fixed_rot:
            ax.plot([x - size, x + size], [y, y], color=COLOR_SUPPORT, lw=3, zorder=3)
            for k in np.linspace(-size, size, 5):
                ax.plot([x + k, x + k - 0.3 * size], [y, y - 0.3 * size],
                        color=COLOR_SUPPORT, lw=1, zorder=3)
        else:
            ax.fill([x, x - 0.6 * size, x + 0.6 * size], [y, y - size, y - size],
                    color=COLOR_SUPPORT, alpha=0.8, zorder=3)


def _figure(frame, title):
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.grid(alpha=0.25)
    pad = 0.15 * max(frame.width, frame.height)
    ax.set_xlim(-pad, frame.width + pad)
    ax.set_ylim(-pad, frame.height + pad)
    return fig, ax


def _svg(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    svg = buf.getvalue()
    return svg[svg.find("<svg"):]


def figure_model(frame):
    fig, ax = _figure(frame, "Model, supports and loads")
    _draw_members(ax, frame)
    _draw_supports(ax, frame)
    arrow = 0.35 * frame.bay_width
    for node, (fx, fy, _) in frame.point_loads.items():
        if fx:
            x, y = frame.coords[node]
            ax.annotate("", xy=(x, y), xytext=(x - arrow * np.sign(fx), y),
                        arrowprops=dict(arrowstyle="-|>", color=COLOR_LOAD, lw=1.8))
            ax.text(x - arrow * np.sign(fx), y + 0.08 * frame.storey_height,
                    f"{fx / 1e3:.1f} kN", color=COLOR_LOAD, fontsize=8)
    for k in frame.beams:
        m = frame.members[k]
        (x1, y1), (x2, y2) = frame.coords[m.i], frame.coords[m.j]
        q = frame.roof_load if y1 == frame.height else frame.floor_load
        h = 0.18 * frame.storey_height
        ax.fill([x1, x2, x2, x1], [y1, y2, y2 + h, y1 + h], color=COLOR_LOAD,
                alpha=0.15, lw=0)
        ax.text(0.5 * (x1 + x2), y1 + 1.15 * h, f"{q / 1e3:.1f} kN/m",
                color=COLOR_LOAD, fontsize=7, ha="center")
    if frame.self_weight:
        ax.text(0.0, -0.12 * max(frame.width, frame.height), "+ steel self-weight",
                color=COLOR_LOAD, fontsize=8)
    return _svg(fig)


def figure_deformed(frame):
    scale, umax = deformation_scale(frame)
    fig, ax = _figure(frame, f"Deformed shape (scale {scale:.0f}x, "
                             f"max displacement {umax * 1e3:.1f} mm)")
    _draw_members(ax, frame, color="#b0bec5", lw=1.2)
    for mr in frame.results.members:
        ax.plot(mr.x + scale * mr.ux, mr.y + scale * mr.uy, color=COLOR_DEFORMED, lw=2)
    _draw_supports(ax, frame)
    return _svg(fig)


def figure_diagram(frame, key, label, unit_factor, unit):
    scale, vmax = diagram_scale(frame, key)
    tension = key == "M"
    title = f"{label} (max |{key}| = {vmax / unit_factor:.1f} {unit})"
    if tension:
        title += ", drawn on tension side"
    fig, ax = _figure(frame, title)
    _draw_members(ax, frame)
    for mr in frame.results.members:
        values = getattr(mr, key)
        x, y = diagram_polygon(mr, values, scale, tension_side=tension)
        # Normal force keeps one sign along a member, so colour it by sign.
        # M and V change sign along members; their side shows the sign.
        if key == "N":
            k = int(np.argmax(np.abs(values)))
            color = COLOR_POSITIVE if values[k] >= 0 else COLOR_NEGATIVE
        else:
            color = COLOR_DIAGRAM
        ax.fill(x, y, color=color, alpha=0.3, lw=0, zorder=1)
        ax.plot(x, y, color=color, lw=0.8, zorder=1)
    _draw_supports(ax, frame)
    return _svg(fig)


# ----------------------------------------------------------------------
# HTML
# ----------------------------------------------------------------------

CSS = """
body { font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
       max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #212121;
       line-height: 1.45; }
h1 { margin-bottom: 0.2rem; }
h2 { border-bottom: 2px solid #cfd8dc; padding-bottom: 0.2rem; margin-top: 2rem; }
.meta { color: #616161; font-size: 0.9rem; }
table { border-collapse: collapse; width: 100%; font-size: 0.88rem; margin: 0.5rem 0; }
th, td { border-bottom: 1px solid #e0e0e0; padding: 0.3rem 0.5rem; text-align: left; }
th { background: #f5f5f5; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.ok { color: #2e7d32; font-weight: 600; }
.fail { color: #c62828; font-weight: 600; }
.banner { padding: 0.8rem 1rem; border-radius: 6px; margin: 1rem 0; font-weight: 600; }
.banner.ok { background: #e8f5e9; border: 1px solid #a5d6a7; }
.banner.fail { background: #ffebee; border: 1px solid #ef9a9a; }
.figs svg { width: 100%; height: auto; }
.signoff td { height: 2.2rem; }
@media print { h2 { page-break-after: avoid; } .fig { page-break-inside: avoid; } }
"""


def _status(ok):
    return '<span class="ok">OK</span>' if ok else '<span class="fail">NOT OK</span>'


def _table(header, rows, numeric=()):
    out = ["<table><tr>"] + [f"<th>{html.escape(h)}</th>" for h in header] + ["</tr>"]
    for row in rows:
        out.append("<tr>")
        for i, cell in enumerate(row):
            cls = ' class="num"' if i in numeric else ""
            out.append(f"<td{cls}>{cell}</td>")
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def input_rows(frame):
    return [
        ("Number of bays", f"{frame.n_bays}"),
        ("Bay width", f"{frame.bay_width:.2f} m"),
        ("Number of storeys", f"{frame.n_storeys}"),
        ("Storey height", f"{frame.storey_height:.2f} m"),
        ("Column section", frame.column_section),
        ("Beam section", frame.beam_section),
        ("Column bases", frame.base),
        ("Steel grade", f"{frame.steel_grade} (fy = {frame.fy / 1e6:.0f} MPa)"),
        ("Young's modulus", f"{frame.E / 1e9:.0f} GPa"),
        ("Floor beam load", f"{frame.floor_load / 1e3:.2f} kN/m"),
        ("Roof beam load", f"{frame.roof_load / 1e3:.2f} kN/m"),
        ("Horizontal load per floor (left)", f"{frame.wind_load / 1e3:.2f} kN"),
        ("Steel self-weight", "included" if frame.self_weight else "not included"),
    ]


def build_report(frame, project="Steel frame", author=""):
    """Return the calculation report for a PlaneFrame as an HTML string."""
    if frame.results is None:
        frame.solve()
    res = frame.results
    s = frame.summary()
    benchmarks = run_benchmarks()
    bench_ok = all(b["passed"] for b in benchmarks)
    eq = res.equilibrium_error()
    eq_ok = max(eq.values()) < 1e-8
    checks_ok = s["drift_ok"] and s["deflection_ok"] and s["utilisation_ok"]

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    versions = (f"Python {platform.python_version()}, NumPy {np.__version__}, "
                f"CALFEM {version('calfem-python')}")

    if not (bench_ok and eq_ok):
        banner = ('<div class="banner fail">Verification FAILED - the results in '
                  'this report must not be used.</div>')
    elif checks_ok:
        banner = ('<div class="banner ok">All checks below are satisfied for the '
                  'given loads. Verification passed.</div>')
    else:
        banner = ('<div class="banner fail">One or more checks are NOT satisfied '
                  'for the given loads.</div>')

    check_rows = [
        ("Interstorey drift",
         f"{s['max_drift'] * 1e3:.2f} mm (storey {s['max_drift_storey']}) = "
         f"h/{1 / s['drift_ratio']:.0f}" if s["drift_ratio"] > 0 else "0",
         f"h/{1 / frame.DRIFT_LIMIT:.0f}", _status(s["drift_ok"])),
        ("Beam deflection (relative to supports)",
         f"{s['max_beam_deflection'] * 1e3:.2f} mm = L/{1 / s['deflection_ratio']:.0f}"
         if s["deflection_ratio"] > 0 else "0",
         f"L/{1 / frame.DEFLECTION_LIMIT:.0f}", _status(s["deflection_ok"])),
        ("Max elastic utilisation",
         f"{100 * s['max_utilisation']:.1f} % (member {s['critical_member']}, "
         f"{s['critical_kind']})", "100 %", _status(s["utilisation_ok"])),
    ]

    key_rows = [
        ("Roof sway", f"{s['top_sway'] * 1e3:.2f} mm"),
        ("Max bending moment", f"{s['max_moment'] / 1e3:.1f} kNm"),
        ("Max compression force", f"{s['max_compression'] / 1e3:.1f} kN"),
        ("Steel mass", f"{s['steel_mass']:.0f} kg"),
        ("Model size", f"{frame.n_nodes} nodes, {len(frame.members)} members, "
                       f"{3 * frame.n_nodes} dofs"),
    ]

    reaction_rows = [
        (f"{node}", f"{x:.2f}", f"{rx / 1e3:.2f}", f"{ry / 1e3:.2f}", f"{mz / 1e3:.2f}")
        for node, (rx, ry, mz) in sorted(res.reactions.items())
        for x in [frame.coords[node][0]]
    ]

    member_rows = []
    util = res.utilisation
    for k, mr in enumerate(res.members):
        m = mr.member
        member_rows.append((
            f"{k}", m.kind, m.section.name, f"{mr.length:.2f}",
            f"{mr.N.min() / 1e3:.1f}", f"{mr.N.max() / 1e3:.1f}",
            f"{mr.max_abs_moment / 1e3:.1f}",
            f"{np.max(np.abs(mr.V)) / 1e3:.1f}",
            f'<span class="{"fail" if util[k] > 1 else ""}">{100 * util[k]:.1f}</span>',
        ))

    bench_rows = [
        (html.escape(b["case"]), html.escape(b["quantity"]),
         f"{b['expected']:.5g} {b['unit']}", f"{b['computed']:.5g} {b['unit']}",
         f"{b['rel_error']:.1e}", _status(b["passed"]))
        for b in benchmarks
    ]

    figures = [
        figure_model(frame),
        figure_deformed(frame),
        figure_diagram(frame, "M", "Bending moment", 1e3, "kNm"),
        figure_diagram(frame, "N", "Normal force (tension +)", 1e3, "kN"),
        figure_diagram(frame, "V", "Shear force", 1e3, "kN"),
    ]

    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>{html.escape(project)} - calculation report</title>",
        f"<style>{CSS}</style></head><body>",
        f"<h1>{html.escape(project)}</h1>",
        f"<div class='meta'>Plane steel frame - linear elastic analysis<br>"
        f"Generated {now}{' by ' + html.escape(author) if author else ''} - "
        f"{versions}</div>",
        banner,
        "<h2>1. Input</h2>",
        "<p>All values below are exactly the values passed to the model.</p>",
        _table(["Parameter", "Value"], input_rows(frame)),
        "<h2>2. Assumptions and limitations</h2><ul>",
        *[f"<li>{html.escape(a)}</li>" for a in ASSUMPTIONS],
        "</ul>",
        "<h2>3. Checks</h2>",
        _table(["Check", "Result", "Limit", "Status"], check_rows),
        "<h2>4. Key results</h2>",
        _table(["Quantity", "Value"], key_rows),
        "<h2>5. Figures</h2><div class='figs'>",
        *[f"<div class='fig'>{svg}</div>" for svg in figures],
        "</div>",
        "<h2>6. Support reactions</h2>",
        _table(["Node", "x (m)", "Rx (kN)", "Ry (kN)", "M (kNm)"], reaction_rows,
               numeric=(1, 2, 3, 4)),
        "<h2>7. Member results</h2>",
        _table(["#", "Type", "Section", "L (m)", "N min (kN)", "N max (kN)",
                "|M| max (kNm)", "|V| max (kN)", "Util. (%)"], member_rows,
               numeric=(3, 4, 5, 6, 7, 8)),
        "<h2>8. Verification</h2>",
        "<h3>Global equilibrium of this model</h3>",
        "<p>Sum of reactions and applied loads, computed independently of the "
        "stiffness matrix. Relative residuals:</p>",
        _table(["Component", "Residual", "Status"],
               [(k, f"{v:.1e}", _status(v < 1e-8)) for k, v in eq.items()]),
        "<h3>Analytical benchmarks of the computational core</h3>",
        _table(["Case", "Quantity", "Analytical", "Computed", "Rel. error", "Status"],
               bench_rows, numeric=(2, 3, 4)),
        "<h2>9. Review</h2>",
        "<p>The program verifies the numerical method. The engineer is responsible "
        "for the model: geometry, supports, loads and their combination, and for "
        "checks not covered here (stability, connections, foundations).</p>",
        "<table class='signoff'><tr><th>Role</th><th>Name</th><th>Date</th>"
        "<th>Signature</th></tr><tr><td>Prepared</td><td></td><td></td><td></td></tr>"
        "<tr><td>Checked</td><td></td><td></td><td></td></tr></table>",
        "</body></html>",
    ]
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Write an HTML report for a plane steel frame.")
    parser.add_argument("--bays", type=int, default=2)
    parser.add_argument("--bay-width", type=float, default=6.0, help="m")
    parser.add_argument("--storeys", type=int, default=3)
    parser.add_argument("--storey-height", type=float, default=3.6, help="m")
    parser.add_argument("--column", default="HEA 240", choices=list(SECTIONS))
    parser.add_argument("--beam", default="IPE 360", choices=list(SECTIONS))
    parser.add_argument("--base", default="fixed", choices=["fixed", "pinned"])
    parser.add_argument("--floor-load", type=float, default=25.0, help="kN/m")
    parser.add_argument("--roof-load", type=float, default=15.0, help="kN/m")
    parser.add_argument("--wind-load", type=float, default=12.0, help="kN per floor")
    parser.add_argument("--grade", default="S355", choices=list(STEEL_GRADES))
    parser.add_argument("--no-self-weight", action="store_true")
    parser.add_argument("--project", default="Steel frame")
    parser.add_argument("-o", "--output", default="frame_report.html")
    args = parser.parse_args()

    frame = PlaneFrame(
        n_bays=args.bays, bay_width=args.bay_width,
        n_storeys=args.storeys, storey_height=args.storey_height,
        column_section=args.column, beam_section=args.beam, base=args.base,
        floor_load=args.floor_load * 1e3, roof_load=args.roof_load * 1e3,
        wind_load=args.wind_load * 1e3, self_weight=not args.no_self_weight,
        steel_grade=args.grade,
    )
    Path(args.output).write_text(build_report(frame, args.project), encoding="utf-8")
    print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
