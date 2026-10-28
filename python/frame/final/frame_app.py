# -*- coding: utf-8 -*-
"""
Interactive web application for the plane steel frame in frame_model.py,
built with NiceGUI and Plotly.

AI-ASSISTED APPLICATION LAYER. The application only builds a PlaneFrame
from the inputs, solves it and presents the results. All engineering
quantities come from the verified core; nothing is recomputed here.

Run with ``python frame_app.py`` and open http://localhost:8080.
Extra dependencies: ``pip install nicegui plotly``.

Features
--------
* Parameter panel: geometry, sections, steel grade, supports and loads.
* Result tabs: model and loads, deformed shape, M/V/N diagrams,
  utilisation and verification (benchmarks and equilibrium).
* Check cards for drift, deflection, utilisation and verification.
* An "as modelled" line rendered from the solved model itself (not from
  the input widgets), so a UI wiring mistake is visible immediately.
* Download of a self-contained HTML calculation report.
"""

import asyncio
import sys
import time
from pathlib import Path

import numpy as np
from nicegui import background_tasks, run, ui
from plotly.colors import sample_colorscale

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from frame_model import PlaneFrame              # noqa: E402
from sections import SECTIONS, STEEL_GRADES     # noqa: E402
from verification import run_benchmarks         # noqa: E402
from frame_report import (                      # noqa: E402
    build_report, deformation_scale, diagram_polygon, diagram_scale,
)
from frame_design import (                      # noqa: E402
    beam_candidates, check_ratios, column_candidates, design_search,
)

DEBOUNCE = 0.25          # seconds of quiet before re-solving
PLOT_CONFIG = {"displaylogo": False, "responsive": True}

COLOR_COLUMN = "#37474f"
COLOR_BEAM = "#546e7a"
COLOR_UNDEFORMED = "#b0bec5"
COLOR_DEFORMED = "#1565c0"
COLOR_LOAD = "#c62828"
COLOR_SUPPORT = "#6d4c41"
COLOR_DIAGRAM = "rgba(106, 27, 154, 0.30)"
COLOR_DIAGRAM_LINE = "rgb(106, 27, 154)"
COLOR_TENSION = "rgba(198, 40, 40, 0.30)"
COLOR_COMPRESSION = "rgba(21, 101, 192, 0.30)"

# Utilisation 0-100 % green -> red; overloaded members purple
UTIL_COLORSCALE = [[0.0, "rgb(26, 152, 80)"], [0.5, "rgb(254, 224, 139)"],
                   [1.0, "rgb(215, 48, 39)"]]
UTIL_OVER_COLOR = "rgb(123, 31, 162)"

DIAGRAMS = {
    # tab: (result attribute, label, unit factor, unit)
    "Moment": ("M", "Bending moment", 1e3, "kNm"),
    "Shear": ("V", "Shear force", 1e3, "kN"),
    "Normal force": ("N", "Normal force (tension +)", 1e3, "kN"),
}
RESULT_TABS = ["Model", "Deformed", "Moment", "Shear", "Normal force",
               "Utilisation", "Design", "Verification"]
COLOR_PASS = "rgb(26, 152, 80)"
COLOR_FAIL = "rgb(176, 190, 197)"
DESIGN_ROWS = 12         # designs listed in the design table

# The benchmarks do not depend on the inputs - run them once at start-up
BENCHMARKS = run_benchmarks()


def build_and_solve(params):
    frame = PlaneFrame(**params)
    frame.solve()
    frame.summary_values = frame.summary()
    return frame


# ----------------------------------------------------------------------
# Plotly figures
# ----------------------------------------------------------------------

def base_layout(frame, title):
    pad = 0.18 * max(frame.width, frame.height)
    return {
        "title": {"text": title, "x": 0.01, "font": {"size": 14}},
        "showlegend": False,
        "hovermode": "closest",
        "margin": {"l": 50, "r": 20, "t": 45, "b": 40},
        "xaxis": {"title": "x (m)", "range": [-pad, frame.width + pad],
                  "zeroline": False},
        "yaxis": {"title": "y (m)", "range": [-pad, frame.height + pad],
                  "scaleanchor": "x", "scaleratio": 1, "zeroline": False},
        "plot_bgcolor": "white",
    }


def member_label(frame, k):
    m = frame.members[k]
    return f"Member {k} ({m.kind}, {m.section.name})"


def member_traces(frame, color=None, width=4, hover=True):
    """Columns and beams, one trace per kind, with section in the hover."""
    traces = []
    for kind, default in (("column", COLOR_COLUMN), ("beam", COLOR_BEAM)):
        x, y, text = [], [], []
        for k, m in enumerate(frame.members):
            if m.kind != kind:
                continue
            (x1, y1), (x2, y2) = frame.coords[m.i], frame.coords[m.j]
            label = member_label(frame, k)
            x += [x1, 0.5 * (x1 + x2), x2, None]
            y += [y1, 0.5 * (y1 + y2), y2, None]
            text += [label, label, label, None]
        traces.append({
            "type": "scatter", "x": x, "y": y, "mode": "lines",
            "line": {"color": color or default, "width": width},
            "text": text, "hoverinfo": "text" if hover else "skip",
        })
    return traces


def support_trace(frame):
    x, y, text = [], [], []
    res = frame.results
    for node, (_, _, fixed) in frame.supports.items():
        nx, ny = frame.coords[node]
        rx, ry, mz = res.reactions[node]
        x.append(nx)
        y.append(ny)
        text.append(f"{'Fixed' if fixed else 'Pinned'} support, node {node}<br>"
                    f"Rx = {rx / 1e3:.2f} kN<br>Ry = {ry / 1e3:.2f} kN<br>"
                    f"M = {mz / 1e3:.2f} kNm")
    symbol = "square" if frame.base == "fixed" else "triangle-up"
    return {
        "type": "scatter", "x": x, "y": y, "mode": "markers",
        "marker": {"symbol": symbol, "size": 16, "color": COLOR_SUPPORT},
        "text": text, "hoverinfo": "text",
    }


def figure_model(frame):
    layout = base_layout(frame, "Model, supports and loads")
    shapes, annotations = [], []
    h = 0.15 * frame.storey_height
    for k in frame.beams:
        m = frame.members[k]
        (x1, y1), (x2, _) = frame.coords[m.i], frame.coords[m.j]
        q = frame.roof_load if y1 == frame.height else frame.floor_load
        shapes.append({"type": "rect", "x0": x1, "x1": x2, "y0": y1, "y1": y1 + h,
                       "fillcolor": "rgba(198, 40, 40, 0.15)", "line": {"width": 0}})
        annotations.append({"x": 0.5 * (x1 + x2), "y": y1 + h, "yshift": 9,
                            "text": f"{q / 1e3:.1f} kN/m", "showarrow": False,
                            "font": {"color": COLOR_LOAD, "size": 11}})
    arrow = 0.3 * frame.bay_width
    for node, (fx, _, _) in frame.point_loads.items():
        if fx:
            x, y = frame.coords[node]
            annotations.append({
                "x": x, "y": y, "ax": x - arrow * np.sign(fx), "ay": y,
                "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
                "showarrow": True, "arrowhead": 2, "arrowwidth": 2,
                "arrowcolor": COLOR_LOAD, "text": f"{fx / 1e3:.1f} kN",
                "font": {"color": COLOR_LOAD, "size": 11}, "xanchor": "right",
            })
    if frame.self_weight:
        annotations.append({"x": 0, "y": 0, "xref": "paper", "yref": "paper",
                            "text": "+ steel self-weight", "showarrow": False,
                            "xanchor": "left", "yanchor": "bottom",
                            "font": {"color": COLOR_LOAD, "size": 11}})
    layout["shapes"] = shapes
    layout["annotations"] = annotations

    nodes = {
        "type": "scatter", "mode": "markers",
        "x": [c[0] for c in frame.coords], "y": [c[1] for c in frame.coords],
        "marker": {"size": 6, "color": "white", "line": {"width": 1.5, "color": COLOR_COLUMN}},
        "text": [f"Node {n}<br>({x:.2f}, {y:.2f}) m" for n, (x, y) in enumerate(frame.coords)],
        "hoverinfo": "text",
    }
    return member_traces(frame) + [nodes, support_trace(frame)], layout


def figure_deformed(frame, factor):
    scale, umax = deformation_scale(frame)
    scale *= factor
    layout = base_layout(
        frame, f"Deformed shape - drawn {scale:.0f}x enlarged, "
               f"max displacement {umax * 1e3:.2f} mm")
    x, y, text = [], [], []
    for k, mr in enumerate(frame.results.members):
        x += list(mr.x + scale * mr.ux) + [None]
        y += list(mr.y + scale * mr.uy) + [None]
        label = member_label(frame, k)
        text += [f"{label}<br>s = {s:.2f} m<br>ux = {ux * 1e3:.2f} mm<br>"
                 f"uy = {uy * 1e3:.2f} mm" for s, ux, uy in zip(mr.s, mr.ux, mr.uy)]
        text.append(None)
    deformed = {"type": "scatter", "x": x, "y": y, "mode": "lines",
                "line": {"color": COLOR_DEFORMED, "width": 3},
                "text": text, "hoverinfo": "text"}
    return member_traces(frame, COLOR_UNDEFORMED, 2, hover=False) + [
        deformed, support_trace(frame)], layout


def figure_diagram(frame, tab):
    key, label, factor, unit = DIAGRAMS[tab]
    scale, vmax = diagram_scale(frame, key)
    tension = key == "M"
    title = f"{label} - max |{key}| = {vmax / factor:.1f} {unit}"
    if tension:
        title += " (drawn on tension side)"
    layout = base_layout(frame, title)

    traces = member_traces(frame, width=2, hover=False)
    hx, hy, htext = [], [], []
    peaks_x, peaks_y, peaks_text = [], [], []
    min_gap = 0.12 * min(frame.bay_width, frame.storey_height)
    for k, mr in enumerate(frame.results.members):
        values = getattr(mr, key)
        x, y = diagram_polygon(mr, values, scale, tension_side=tension)
        if key == "N":
            fill = COLOR_TENSION if values.mean() >= 0 else COLOR_COMPRESSION
            line = fill.replace("0.30", "1.0")
        else:
            fill, line = COLOR_DIAGRAM, COLOR_DIAGRAM_LINE
        traces.append({"type": "scatter", "x": list(x), "y": list(y),
                       "fill": "toself", "fillcolor": fill, "mode": "lines",
                       "line": {"color": line, "width": 1}, "hoverinfo": "skip"})
        name = member_label(frame, k)
        hx += list(x[1:-1])
        hy += list(y[1:-1])
        htext += [f"{name}<br>s = {s:.2f} m<br>{key} = {v / factor:.2f} {unit}"
                  for s, v in zip(mr.s, values)]
        # Label the peak of each member, pushed slightly beyond the diagram
        # and skipped if it would overlap a label already placed
        i = int(np.argmax(np.abs(values)))
        if abs(values[i]) >= 0.2 * vmax:
            dx, dy = x[i + 1] - mr.x[i], y[i + 1] - mr.y[i]
            d = np.hypot(dx, dy)
            px, py = x[i + 1] + 0.35 * dx / d * min_gap, y[i + 1] + 0.35 * dy / d * min_gap
            if all(np.hypot(px - qx, py - qy) > min_gap for qx, qy in zip(peaks_x, peaks_y)):
                peaks_x.append(px)
                peaks_y.append(py)
                peaks_text.append(f"{values[i] / factor:.0f}")

    traces.append({"type": "scatter", "x": hx, "y": hy, "mode": "markers",
                   "marker": {"size": 7, "opacity": 0}, "text": htext,
                   "hoverinfo": "text"})
    if len(frame.members) <= 40:
        traces.append({"type": "scatter", "x": peaks_x, "y": peaks_y,
                       "mode": "text", "text": peaks_text, "hoverinfo": "skip",
                       "textfont": {"size": 10, "color": "#212121"}})
    traces.append(support_trace(frame))
    return traces, layout


def figure_utilisation(frame):
    res = frame.results
    util = 100 * res.utilisation
    layout = base_layout(frame, f"Elastic utilisation (|N|/A + |M|/W) / fy - "
                                f"max {util.max():.1f} %")
    traces = []
    for k, mr in enumerate(res.members):
        u = util[k]
        color = (UTIL_OVER_COLOR if u > 100
                 else sample_colorscale(UTIL_COLORSCALE, [u / 100])[0])
        (x1, y1), (x2, y2) = frame.coords[mr.member.i], frame.coords[mr.member.j]
        text = (f"{member_label(frame, k)}<br>utilisation {u:.1f} %<br>"
                f"max stress {mr.max_stress / 1e6:.1f} MPa<br>"
                f"fy = {frame.fy / 1e6:.0f} MPa")
        traces.append({"type": "scatter", "x": [x1, 0.5 * (x1 + x2), x2],
                       "y": [y1, 0.5 * (y1 + y2), y2], "mode": "lines",
                       "line": {"color": color, "width": 8},
                       "text": [text] * 3, "hoverinfo": "text"})
    # Invisible trace that only carries the colour bar
    traces.append({
        "type": "scatter", "x": [None], "y": [None], "mode": "markers",
        "hoverinfo": "skip",
        "marker": {"colorscale": UTIL_COLORSCALE, "cmin": 0, "cmax": 100,
                   "color": [0], "showscale": True,
                   "colorbar": {"title": {"text": "%"}, "thickness": 14}},
    })
    traces.append(support_trace(frame))
    return traces, layout


def design_label(r):
    return (f"{r['column']} / {r['beam']}<br>{r['mass']:.0f} kg<br>"
            f"drift h/{1 / r['drift']:.0f}, deflection L/{1 / r['deflection']:.0f}, "
            f"utilisation {100 * r['utilisation']:.0f} %<br>governed by {r['governs']}")


def figure_design(rows, frame):
    """Steel mass against the governing check ratio for every combination."""
    n_ok = sum(r["ok"] for r in rows)
    layout = {
        "title": {"text": f"Design space - {n_ok} of {len(rows)} combinations pass "
                          f"all checks (lower left is lighter and safer)",
                  "x": 0.01, "font": {"size": 14}},
        "showlegend": True,
        "legend": {"orientation": "h", "y": -0.18},
        "hovermode": "closest",
        "margin": {"l": 60, "r": 20, "t": 45, "b": 70},
        "xaxis": {"title": "Steel mass (kg)"},
        "yaxis": {"title": "Governing check / limit"},
        "plot_bgcolor": "white",
        "shapes": [{"type": "line", "xref": "paper", "x0": 0, "x1": 1, "y0": 1, "y1": 1,
                    "line": {"color": "rgb(215, 48, 39)", "dash": "dash", "width": 1.5}}],
        "annotations": [{"xref": "paper", "x": 1, "y": 1, "yshift": 10, "yref": "y",
                         "text": "limit", "showarrow": False, "xanchor": "right",
                         "font": {"color": "rgb(215, 48, 39)", "size": 11}}],
    }
    traces = []
    for ok, name, color in ((False, "Fails a check", COLOR_FAIL), (True, "Passes all checks", COLOR_PASS)):
        group = [r for r in rows if r["ok"] == ok]
        traces.append({
            "type": "scatter", "mode": "markers", "name": name,
            "x": [r["mass"] for r in group], "y": [r["ratio"] for r in group],
            "text": [design_label(r) for r in group], "hoverinfo": "text",
            "marker": {"size": 10, "color": color, "line": {"width": 1, "color": "white"}},
        })
    best = next((r for r in rows if r["ok"]), None)
    if best:
        traces.append({
            "type": "scatter", "mode": "markers+text", "name": "Lightest passing",
            "x": [best["mass"]], "y": [best["ratio"]], "hoverinfo": "skip",
            "text": [f"{best['column']} / {best['beam']}"], "textposition": "bottom right",
            "marker": {"size": 18, "color": "rgba(0,0,0,0)",
                       "line": {"width": 2.5, "color": COLOR_PASS}},
        })
    s = frame.summary_values
    ratios = check_ratios(frame, s)
    traces.append({
        "type": "scatter", "mode": "markers", "name": "Current design",
        "x": [s["steel_mass"]], "y": [max(ratios.values())],
        "text": [f"Current: {frame.column_section} / {frame.beam_section}"],
        "hoverinfo": "text",
        "marker": {"size": 16, "symbol": "star", "color": "#1565c0"},
    })
    return traces, layout


# ----------------------------------------------------------------------
# Application
# ----------------------------------------------------------------------

class FrameApp:
    def __init__(self):
        self.frame = None
        self.design = None       # last design search: {"key", "rows"}
        self._requested = 0
        self._solve_id = 0

        ui.query("body").classes("bg-gray-100")
        with ui.header().classes("bg-blue-grey-9 items-center px-4 py-2"):
            ui.label("Steel Frame Studio").classes("text-lg font-semibold")
            ui.label("CALFEM beam2e - linear elastic").classes("text-sm opacity-70")

        with ui.row().classes("w-full p-3 gap-3 items-start flex-col lg:flex-row lg:flex-nowrap"):
            with ui.card().classes("w-full lg:w-[340px] shrink-0 p-3 gap-1"):
                self._build_inputs()
            with ui.column().classes("w-full lg:flex-1 min-w-0 gap-3"):
                self._build_results()

        ui.timer(0.05, self.update_model, once=True)

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------

    def _number(self, label, value, minimum, maximum, step, suffix="", fmt="%.2f"):
        field = ui.number(label=label, value=value, min=minimum, max=maximum,
                          step=step, format=fmt, suffix=suffix,
                          on_change=self.schedule_update)
        return field.props("dense outlined").classes("w-full")

    @staticmethod
    def _heading(text):
        ui.label(text).classes("text-xs font-semibold uppercase text-gray-500 mt-3")

    def _build_inputs(self):
        sections = list(SECTIONS)

        self._heading("Geometry")
        with ui.grid(columns=2).classes("w-full gap-2"):
            self.n_bays = self._number("Bays", 2, 1, 8, 1, fmt="%d")
            self.bay_width = self._number("Bay width", 6.0, 2.0, 15.0, 0.5, " m")
            self.n_storeys = self._number("Storeys", 3, 1, 15, 1, fmt="%d")
            self.storey_height = self._number("Storey height", 3.6, 2.5, 6.0, 0.1, " m")

        self._heading("Sections and material")
        self.column = ui.select(sections, value="HEA 240", label="Columns",
                                on_change=self.schedule_update).props("dense outlined").classes("w-full")
        self.beam = ui.select(sections, value="IPE 360", label="Beams",
                              on_change=self.schedule_update).props("dense outlined").classes("w-full")
        self.grade = ui.select(list(STEEL_GRADES), value="S355", label="Steel grade",
                               on_change=self.schedule_update).props("dense outlined").classes("w-full")

        self._heading("Column bases")
        # Option values are the exact strings PlaneFrame expects
        self.base = ui.toggle({"fixed": "Fixed", "pinned": "Pinned"}, value="fixed",
                              on_change=self.schedule_update).props("spread no-caps").classes("w-full")

        self._heading("Loads")
        with ui.grid(columns=2).classes("w-full gap-2"):
            self.floor_load = self._number("Floor beams", 25.0, 0, 200, 1, " kN/m", "%.1f")
            self.roof_load = self._number("Roof beams", 15.0, 0, 200, 1, " kN/m", "%.1f")
            self.wind_load = self._number("Horizontal / floor", 12.0, -200, 200, 1, " kN", "%.1f")
        self.self_weight = ui.switch("Include steel self-weight", value=True,
                                     on_change=self.schedule_update)

        self._heading("Report")
        self.project = ui.input("Project name", value="Steel frame").props(
            "dense outlined").classes("w-full")
        ui.button("Download calculation report", icon="description",
                  on_click=self.download_report).props("no-caps").classes("w-full mt-1")

    def _read_inputs(self):
        def value(field, label, integer=False):
            if field.value is None:
                raise ValueError(f"Enter a value for '{label}'.")
            return int(field.value) if integer else float(field.value)

        return dict(
            n_bays=value(self.n_bays, "Bays", integer=True),
            bay_width=value(self.bay_width, "Bay width"),
            n_storeys=value(self.n_storeys, "Storeys", integer=True),
            storey_height=value(self.storey_height, "Storey height"),
            column_section=self.column.value,
            beam_section=self.beam.value,
            steel_grade=self.grade.value,
            base=self.base.value,
            floor_load=value(self.floor_load, "Floor beams") * 1e3,
            roof_load=value(self.roof_load, "Roof beams") * 1e3,
            wind_load=value(self.wind_load, "Horizontal / floor") * 1e3,
            self_weight=self.self_weight.value,
        )

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _check_card(self, title):
        with ui.card().classes("p-3 gap-0 min-w-0") as card:
            ui.label(title).classes("text-xs uppercase text-gray-500")
            value = ui.label("-").classes("text-xl font-semibold")
            detail = ui.label("").classes("text-xs text-gray-600")
        return card, value, detail

    def _build_results(self):
        with ui.grid().classes("w-full gap-3 grid-cols-2 xl:grid-cols-4"):
            self.cards = {
                "drift": self._check_card("Interstorey drift"),
                "deflection": self._check_card("Beam deflection"),
                "utilisation": self._check_card("Max utilisation"),
                "verification": self._check_card("Verification"),
            }

        with ui.card().classes("w-full p-2 gap-1"):
            self.as_modelled = ui.label("").classes("text-xs text-gray-600 px-2 font-mono")
            with ui.tabs(value="Moment", on_change=self.render_current).props(
                    "dense no-caps align=left").classes("w-full") as tabs:
                for name in RESULT_TABS:
                    ui.tab(name)
            self.tabs = tabs
            self.plot = ui.plotly({"data": [], "config": PLOT_CONFIG}).classes(
                "w-full h-[62vh] min-h-[380px]")
            with ui.row().classes("items-center gap-3 px-2 w-full") as self.scale_row:
                ui.label("Exaggeration").classes("text-sm")
                self.scale_slider = ui.slider(min=0.25, max=4.0, step=0.25, value=1.0,
                                              on_change=self.render_current).classes("w-48")
                self.scale_slider.props("label")
            self.verification = ui.column().classes("w-full px-2 gap-2")
            with ui.column().classes("w-full px-2 gap-2") as self.design_panel:
                with ui.row().classes("items-center gap-4 w-full"):
                    self.design_button = ui.button(
                        "Find lightest designs", icon="search",
                        on_click=self.run_design_search).props("no-caps")
                    self.h_columns_only = ui.switch(
                        "H-sections only for columns (the model has no buckling check)",
                        value=True)
                self.design_note = ui.label(
                    "Solves every column/beam combination for the current geometry, "
                    "supports and loads. Click a row to apply that design.").classes(
                    "text-sm text-gray-600")
                self.design_table = ui.column().classes("w-full")
            with ui.row().classes("items-center gap-2 px-2"):
                self.spinner = ui.spinner(size="sm")
                self.status = ui.label("Solving ...").classes("text-sm")

        with ui.card().classes("w-full p-3"):
            self.key_results = ui.label("").classes("text-sm font-mono whitespace-pre-wrap")

    def _set_card(self, name, ok, value, detail):
        card, value_label, detail_label = self.cards[name]
        card.classes(remove="bg-green-1 bg-red-1")
        card.classes(add="bg-green-1" if ok else "bg-red-1")
        value_label.text = value
        detail_label.text = detail

    def _update_summary(self):
        frame, s = self.frame, self.frame.summary_values
        self._set_card("drift", s["drift_ok"],
                       f"h/{1 / s['drift_ratio']:.0f}" if s["drift_ratio"] > 0 else "0",
                       f"{s['max_drift'] * 1e3:.1f} mm in storey {s['max_drift_storey']} "
                       f"(limit h/{1 / frame.DRIFT_LIMIT:.0f})")
        self._set_card("deflection", s["deflection_ok"],
                       f"L/{1 / s['deflection_ratio']:.0f}" if s["deflection_ratio"] > 0 else "0",
                       f"{s['max_beam_deflection'] * 1e3:.1f} mm "
                       f"(limit L/{1 / frame.DEFLECTION_LIMIT:.0f})")
        self._set_card("utilisation", s["utilisation_ok"],
                       f"{100 * s['max_utilisation']:.0f} %",
                       f"member {s['critical_member']} ({s['critical_kind']}), elastic")
        n_ok = sum(b["passed"] for b in BENCHMARKS)
        eq_ok = s["equilibrium_error"] < 1e-8
        self._set_card("verification", eq_ok and n_ok == len(BENCHMARKS),
                       f"{n_ok}/{len(BENCHMARKS)} benchmarks",
                       f"equilibrium residual {s['equilibrium_error']:.0e}")

        self.as_modelled.text = (
            f"As modelled: {frame.n_bays} x {frame.bay_width:.2f} m bays, "
            f"{frame.n_storeys} x {frame.storey_height:.2f} m storeys | "
            f"{frame.column_section} / {frame.beam_section}, {frame.steel_grade} | "
            f"{frame.base} bases | q = {frame.floor_load / 1e3:.1f} / "
            f"{frame.roof_load / 1e3:.1f} kN/m, H = {frame.wind_load / 1e3:.1f} kN"
            f"{' + self-weight' if frame.self_weight else ''}")
        self.key_results.text = (
            f"Roof sway {s['top_sway'] * 1e3:.2f} mm   |   "
            f"max M {s['max_moment'] / 1e3:.1f} kNm   |   "
            f"max compression {s['max_compression'] / 1e3:.0f} kN   |   "
            f"steel {s['steel_mass']:.0f} kg")

    def _render_verification(self):
        self.verification.clear()
        eq = self.frame.results.equilibrium_error()
        with self.verification:
            ui.label("Global equilibrium of the current model "
                     "(reactions + applied loads, independent of K)").classes(
                "text-sm font-semibold mt-2")
            ui.label("   ".join(f"{k}: {v:.1e}" for k, v in eq.items())).classes(
                "font-mono text-sm")
            ui.label("Analytical benchmarks of the computational core").classes(
                "text-sm font-semibold mt-2")
            columns = [
                {"name": "case", "label": "Case", "field": "case", "align": "left"},
                {"name": "quantity", "label": "Quantity", "field": "quantity", "align": "left"},
                {"name": "expected", "label": "Analytical", "field": "expected"},
                {"name": "computed", "label": "Computed", "field": "computed"},
                {"name": "rel_error", "label": "Rel. error", "field": "rel_error"},
                {"name": "status", "label": "", "field": "status"},
            ]
            rows = [{
                "id": i, "case": b["case"], "quantity": b["quantity"],
                "expected": f"{b['expected']:.5g} {b['unit']}",
                "computed": f"{b['computed']:.5g} {b['unit']}",
                "rel_error": f"{b['rel_error']:.1e}",
                "status": "pass" if b["passed"] else "FAIL",
            } for i, b in enumerate(BENCHMARKS)]
            ui.table(columns=columns, rows=rows).props("dense flat").classes("w-full")

    def render_current(self):
        if self.frame is None:
            return
        tab = self.tabs.value
        is_plot = tab != "Verification" and (tab != "Design" or self.design is not None)
        self.plot.set_visibility(is_plot)
        self.verification.set_visibility(tab == "Verification")
        self.design_panel.set_visibility(tab == "Design")
        self.scale_row.set_visibility(tab == "Deformed")
        if tab == "Verification":
            self._render_verification()
            return
        if tab == "Design":
            self._render_design_table()
            if self.design is None:
                return

        if tab == "Design":
            data, layout = figure_design(self.design["rows"], self.frame)
        elif tab == "Model":
            data, layout = figure_model(self.frame)
        elif tab == "Deformed":
            data, layout = figure_deformed(self.frame, self.scale_slider.value)
        elif tab == "Utilisation":
            data, layout = figure_utilisation(self.frame)
        else:
            data, layout = figure_diagram(self.frame, tab)
        self.plot.figure = {"data": data, "layout": layout, "config": PLOT_CONFIG}
        self.plot.update()

    # ------------------------------------------------------------------
    # Design search
    # ------------------------------------------------------------------

    def _design_key(self):
        """Inputs a design search depends on: everything but the sections."""
        params = self._read_inputs()
        params.pop("column_section")
        params.pop("beam_section")
        return tuple(sorted(params.items())), self.h_columns_only.value

    async def run_design_search(self):
        try:
            key = self._design_key()
        except ValueError as error:
            ui.notify(str(error), type="warning")
            return
        params = dict(key[0])
        columns = column_candidates(h_sections_only=key[1])
        beams = beam_candidates()
        self.design_button.props("loading")
        t0 = time.perf_counter()
        try:
            rows = await run.io_bound(design_search, params, columns, beams)
        finally:
            self.design_button.props(remove="loading")
        self.design = {"key": key, "rows": rows}
        self.design_note.text = (
            f"Solved {len(rows)} combinations in {time.perf_counter() - t0:.1f} s. "
            f"Click a row to apply that design.")
        self.render_current()

    def _render_design_table(self):
        self.design_table.clear()
        if self.design is None:
            return
        rows = self.design["rows"]
        passing = [r for r in rows if r["ok"]]
        # No passing design: list the ones closest to passing instead
        shown = passing[:DESIGN_ROWS] or sorted(rows, key=lambda r: r["ratio"])[:5]
        with self.design_table:
            try:
                stale = self._design_key() != self.design["key"]
            except ValueError:
                stale = True
            if stale:
                ui.label("Inputs have changed since this search - run it again.").classes(
                    "text-sm text-red-700")
            if not passing:
                ui.label("No combination passes all checks. Closest designs:").classes(
                    "text-sm text-red-700")
            columns = [
                {"name": "rank", "label": "#", "field": "rank"},
                {"name": "column", "label": "Columns", "field": "column", "align": "left"},
                {"name": "beam", "label": "Beams", "field": "beam", "align": "left"},
                {"name": "mass", "label": "Steel (kg)", "field": "mass"},
                {"name": "drift", "label": "Drift", "field": "drift"},
                {"name": "deflection", "label": "Deflection", "field": "deflection"},
                {"name": "utilisation", "label": "Utilisation", "field": "utilisation"},
                {"name": "governs", "label": "Governs", "field": "governs", "align": "left"},
            ]
            table_rows = [{
                "id": i, "rank": i + 1, "column": r["column"], "beam": r["beam"],
                "mass": f"{r['mass']:.0f}",
                "drift": f"h/{1 / r['drift']:.0f}",
                "deflection": f"L/{1 / r['deflection']:.0f}",
                "utilisation": f"{100 * r['utilisation']:.0f} %",
                "governs": r["governs"],
            } for i, r in enumerate(shown)]
            table = ui.table(columns=columns, rows=table_rows).props(
                "dense flat").classes("w-full cursor-pointer")
            table.on("rowClick", self.apply_design)

    def apply_design(self, event):
        # Quasar's rowClick sends (event, row, index); pick the row dict
        row = next(a for a in event.args if isinstance(a, dict) and "column" in a)
        self.column.value = row["column"]
        self.beam.value = row["beam"]
        ui.notify(f"Applied {row['column']} columns and {row['beam']} beams")

    # ------------------------------------------------------------------
    # Model update
    # ------------------------------------------------------------------

    def schedule_update(self, *_):
        self._requested += 1
        background_tasks.create(self._debounced_update(self._requested))

    async def _debounced_update(self, request):
        await asyncio.sleep(DEBOUNCE)
        if request == self._requested:
            await self.update_model()

    async def update_model(self):
        self._requested += 1
        self._solve_id += 1
        solve_id = self._solve_id
        self.spinner.set_visibility(True)
        t0 = time.perf_counter()
        try:
            frame = await run.io_bound(build_and_solve, self._read_inputs())
        except Exception as error:      # keep the UI alive on invalid input
            if solve_id == self._solve_id:
                self.spinner.set_visibility(False)
                self.status.text = f"Not solved: {error}"
                self.status.classes(add="text-red-700")
            return
        if solve_id != self._solve_id:  # a newer solve has been started
            return
        t_solve = time.perf_counter() - t0

        self.frame = frame
        self._update_summary()
        t0 = time.perf_counter()
        self.render_current()
        t_draw = time.perf_counter() - t0

        self.spinner.set_visibility(False)
        self.status.classes(remove="text-red-700")
        self.status.text = (f"{frame.n_nodes} nodes, {len(frame.members)} members, "
                            f"{3 * frame.n_nodes} dofs | solve {t_solve * 1e3:.0f} ms, "
                            f"draw {t_draw * 1e3:.0f} ms")

    async def download_report(self):
        if self.frame is None:
            ui.notify("No solved model yet.", type="warning")
            return
        ui.notify("Generating report ...")
        html_text = await run.io_bound(build_report, self.frame,
                                       self.project.value or "Steel frame")
        name = "".join(c if c.isalnum() else "_" for c in self.project.value or "frame")
        ui.download.content(html_text, f"{name}_report.html", "text/html")


@ui.page("/")
def index():
    FrameApp()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Steel Frame Studio", reload=False)
