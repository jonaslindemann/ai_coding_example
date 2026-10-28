# -*- coding: utf-8 -*-
"""
Regenerate the figures used in engineering_problem.md.

Run from anywhere: ``python make_figures.py``. The PNG figures come
from the verified model through the report's plotting helpers; the two
SVG diagrams are static drawings of the geometry and the beam2e element.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

out = Path(__file__).resolve().parent
sys.path.insert(0, str(out.parent))
sys.path.insert(0, str(out.parent / "final"))

import frame_report as fr  # noqa: E402

EDGE, INK, QUIET = "#9aa0a6", "#202124", "#5f6368"
ACCENT, LOCAL, TINT = "#2a78d6", "#e8622c", "#eef1f4"
FONT = "font-family='Helvetica, Arial, sans-serif'"


def svg(w, h, label, body):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='{w}' height='{h}' "
            f"role='img' aria-label='{label}' {FONT} font-size='13'>"
            f"<rect width='{w}' height='{h}' fill='white'/>{body}</svg>\n")


def text(x, y, s, fill=INK, size=None, weight=None, anchor=None):
    a = f" font-size='{size}'" if size else ""
    a += f" font-weight='{weight}'" if weight else ""
    a += f" text-anchor='{anchor}'" if anchor else ""
    return f"<text x='{x}' y='{y}' fill='{fill}'{a}>{s}</text>"


def line(x1, y1, x2, y2, stroke=EDGE, width=1.25, extra=""):
    return f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{stroke}' stroke-width='{width}' {extra}/>"


# ---- Geometry -------------------------------------------------------
xs, ys = [200, 344, 488], [360, 273.6, 187.2, 100.8]
b = [text(24, 30, "Two bays of 6.0 m and three storeys of 3.6 m", size=15, weight=600),
     text(24, 50, "S355 steel, rigid beam-column joints, 12 nodes and 15 members", QUIET, 11.5)]
b += [line(x, ys[0], x, ys[3], ACCENT, 3, "stroke-linecap='round'") for x in xs]
b += [line(xs[0], y, xs[2], y, ACCENT, 3, "stroke-linecap='round'") for y in ys[1:]]
b += [f"<circle cx='{x}' cy='{y}' r='4' fill='{TINT}' stroke='{EDGE}' stroke-width='1.25'/>" for x in xs for y in ys]
for x in xs:
    b.append(line(x - 16, 362, x + 16, 362, EDGE, 2.5))
    b += [line(x + d, 364, x + d - 6, 372) for d in (-12, -4, 4, 12)]
b.append(line(200, 396, 488, 396, EDGE, 1))
b += [line(x, 390, x, 402, EDGE, 1) for x in xs]
b += [text(272, 416, "6.0 m", anchor="middle"), text(416, 416, "6.0 m", anchor="middle")]
b.append(line(536, 360, 536, 100.8, EDGE, 1))
b += [line(530, y, 542, y, EDGE, 1) for y in ys]
b += [text(550, y, "3.6 m") for y in (321, 234, 148)]
b += [text(24, 226, "Columns", weight=600), text(24, 242, "HEA 240", QUIET),
      line(96, 231, 194, 231, EDGE, 1, "stroke-dasharray='3 3'"),
      text(272, 76, "Beams", weight=600, anchor="middle"), text(272, 92, "IPE 360", QUIET, anchor="middle"),
      text(24, 358, "Bases", weight=600), text(24, 374, "fixed or pinned", QUIET),
      line(128, 366, 180, 366, EDGE, 1, "stroke-dasharray='3 3'"),
      text(600, 234, "10.8 m in total", QUIET, 11.5)]
(out / "fig_geometry.svg").write_text(
    svg(760, 432, "Two bays of 6.0 m and three storeys of 3.6 m", "".join(b)), encoding="utf-8")

# ---- beam2e element -------------------------------------------------
n1x, n1y, n2x, n2y = 180, 320, 540, 170
defs = ("<defs>"
        f"<marker id='a' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='6' markerHeight='6' orient='auto-start-reverse'><path d='M0 0L10 5L0 10z' fill='{EDGE}'/></marker>"
        f"<marker id='l' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='6' markerHeight='6' orient='auto-start-reverse'><path d='M0 0L10 5L0 10z' fill='{LOCAL}'/></marker>"
        "</defs>")


def path(d, stroke=EDGE, width=1.25, marker="a"):
    m = f" marker-end='url(#{marker})'" if marker else ""
    return f"<path d='{d}' fill='none' stroke='{stroke}' stroke-width='{width}'{m}/>"


def dofs(x, y, labels):
    return [path(f"M{x} {y}H{x + 52}"), path(f"M{x} {y}V{y - 52}"),
            path(f"M{x - 20.8} {y + 12} A24 24 0 0 0 {x + 23.6} {y + 4.2}"),
            text(x + 58, y + 4, labels[0]), text(x + 8, y - 52, labels[1]),
            text(x, y + 44, labels[2], anchor="middle")]


b = [defs,
     text(24, 30, "A beam2e element: two nodes, three degrees of freedom each", size=15, weight=600),
     text(24, 50, "Displacements a1 to a6 in global directions; line loads in the local X and Y directions", QUIET, 11.5),
     line(n1x, n1y, n2x, n2y, ACCENT, 4, "stroke-linecap='round'")]
b += [f"<circle cx='{x}' cy='{y}' r='5' fill='{TINT}' stroke='{EDGE}' stroke-width='1.25'/>" for x, y in ((n1x, n1y), (n2x, n2y))]
b += [text(466, 236, "E, A, I, length L"),
      text(166, 306, "Node 1", weight=600, anchor="end"), text(528, 160, "Node 2", weight=600, anchor="end")]
b += dofs(n1x, n1y, ("a1", "a2", "a3")) + dofs(n2x, n2y, ("a4", "a5", "a6"))
b += [path(f"M{n1x + 40} {n1y} A40 40 0 0 0 {n1x + 36.9} {n1y - 15.4}", QUIET, 1, None),
      text(n1x + 46, n1y - 8, "α", QUIET, 11.5),
      path("M323 309L413 271.5", LOCAL, 1.5, "l"), path("M360 245L340 197", LOCAL, 1.5, "l"),
      text(420, 280, "X", weight=600), text(420, 296, "along the member: N, u, qX", QUIET, 11.5),
      text(326, 190, "Y", weight=600), text(232, 176, "across the member: V, M, v, qY", QUIET, 11.5),
      path("M60 392H112"), path("M60 392V340"),
      text(118, 396, "x"), text(56, 332, "y", anchor="middle"), text(132, 396, "global axes", QUIET, 11.5)]
(out / "fig_element.svg").write_text(
    svg(760, 420, "A beam2e element has two nodes with three degrees of freedom each", "".join(b)), encoding="utf-8")


# ---- Result figures from the verified model -------------------------
def save_png(name):
    def _save(fig):
        fig.savefig(out / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close(fig)
        return ""
    return _save


frame = fr.PlaneFrame()
frame.solve()
for name, draw in [("fig_model", lambda: fr.figure_model(frame)),
                   ("fig_deformed", lambda: fr.figure_deformed(frame)),
                   ("fig_moment", lambda: fr.figure_diagram(frame, "M", "Bending moment", 1e3, "kNm"))]:
    fr._svg = save_png(name)
    draw()

frames = {b: fr.PlaneFrame(base=b) for b in ("fixed", "pinned")}
scale = 80
fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True, layout="constrained")
for ax, (base, fm) in zip(axes, frames.items()):
    fm.solve()
    s = fm.summary()
    for m in fm.members:
        (x1, y1), (x2, y2) = fm.coords[m.i], fm.coords[m.j]
        ax.plot([x1, x2], [y1, y2], color="#b0bec5", lw=1.2)
    for mr in fm.results.members:
        ax.plot(mr.x + scale * mr.ux, mr.y + scale * mr.uy, color=fr.COLOR_DEFORMED, lw=2)
    fr._draw_supports(ax, fm)
    ax.set_title(f"{base.capitalize()} bases: roof sway {s['top_sway'] * 1e3:.1f} mm, "
                 f"drift h/{1 / s['drift_ratio']:.0f}", fontsize=11, loc="left")
    ax.set_aspect("equal")
    ax.set_xlim(-1.5, 15.5)
    ax.set_ylim(-1.5, 12)
    ax.grid(alpha=0.25)
    ax.set_xlabel("x (m)")
axes[0].set_ylabel("y (m)")
fig.suptitle(f"Same loads, displacements drawn {scale}x enlarged in both",
             fontsize=10, color="#555", x=0.01, ha="left")
fig.savefig(out / "fig_supports.png", dpi=160)
plt.close(fig)
print(f"Figures written to {out}")
