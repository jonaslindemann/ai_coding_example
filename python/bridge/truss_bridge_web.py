"""
Web application for the parametric truss bridge in truss_bridge.py.

Built with NiceGUI and Plotly. The TrussBridge class is reused unchanged.

Run with:

    python truss_bridge_web.py

and open http://localhost:8080 in a browser.

Extra dependencies (besides calfem-python, numpy and matplotlib):

    pip install nicegui plotly
"""

import time

import numpy as np
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
from nicegui import ui

from truss_bridge import TrussBridge

# Red = compression, blue = tension (normal force > 0)
FORCE_COLORSCALE = "RdBu"

# Debounce settings for slider dragging [s]
DEBOUNCE_DELAY = 0.04       # update when input has been quiet this long ...
MAX_UPDATE_INTERVAL = 0.15  # ... but never wait longer than this while dragging
POLL_INTERVAL = 0.03

PLOT_CONFIG = {"responsive": True, "displaylogo": False}


class TrussBridgeApp:
    """One instance per browser client, holding its own bridge model."""

    def __init__(self):
        self.bridge = TrussBridge()
        self.params = {
            "truss_type": "Pratt",
            "width": self.bridge.width,
            "height": self.bridge.height,
            "n_panels": self.bridge.n_panels,
            "E": self.bridge.E / 1e9,               # GPa
            "fy": self.bridge.fy / 1e6,             # MPa
            "A_chord": self.bridge.A_chord * 1e4,   # cm2
            "A_web": self.bridge.A_web * 1e4,       # cm2
            "deck_load": self.bridge.deck_load / 1e3,  # kN/m
            "point_load": 0.0,                      # kN
            "point_pos": 0.5,                       # x/L
            "auto_scale": True,
            "scale": 20.0,
        }

        self._dirty = False
        self._last_change = 0.0
        self._last_update = 0.0

        self.build()
        self.update_model()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def slider(self, label, key, minimum, maximum, step, unit="", decimals=1):
        with ui.column().classes("w-full gap-0"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label(label).classes("text-sm")
                ui.label().classes("text-sm font-mono text-gray-600").bind_text_from(
                    self.params, key, backward=lambda v: f"{v:.{decimals}f} {unit}".strip())
            s = ui.slider(min=minimum, max=maximum, step=step,
                          on_change=self.schedule_update).bind_value(self.params, key)
        return s

    def build(self):
        ui.query("body").classes("bg-gray-100")

        with ui.header().classes("bg-slate-800 items-center"):
            ui.icon("architecture").classes("text-2xl")
            ui.label("Truss Bridge Designer").classes("text-lg font-semibold")
            ui.label("CALFEM bar2 elements").classes("text-sm opacity-70")

        with ui.element("div").classes(
                "w-full flex flex-col lg:flex-row gap-4 items-stretch lg:items-start"):

            # ---------------- Parameter panel ----------------
            with ui.card().classes("w-full lg:w-96 shrink-0 gap-2"):
                ui.label("Geometry").classes("text-base font-semibold")
                ui.toggle(["Pratt", "Howe", "Warren"], on_change=self._on_type_changed) \
                    .bind_value(self.params, "truss_type").classes("w-full")
                self.slider("Width (span)", "width", 5, 120, 0.5, "m")
                self.slider("Height", "height", 0.5, 20, 0.1, "m")
                self.panels_slider = self.slider("Panels", "n_panels", 2, 40, 2, "", 0)
                self.panels_note = ui.label("Pratt and Howe need an even number of panels") \
                    .classes("text-xs text-gray-500")

                ui.separator()
                ui.label("Material and sections").classes("text-base font-semibold")
                self.slider("E-modulus", "E", 10, 300, 1, "GPa", 0)
                self.slider("Yield strength fy", "fy", 100, 700, 5, "MPa", 0)
                self.slider("Chord area", "A_chord", 5, 500, 1, "cm²", 0)
                self.slider("Web area (diagonals, verticals)", "A_web", 5, 500, 1, "cm²", 0)

                ui.separator()
                ui.label("Loads").classes("text-base font-semibold")
                self.slider("Deck load", "deck_load", 0, 300, 1, "kN/m", 0)
                self.slider("Point load", "point_load", 0, 2000, 10, "kN", 0)
                self.slider("Point load position x/L", "point_pos", 0, 1, 0.01, "", 2)

                ui.separator()
                ui.label("Display").classes("text-base font-semibold")
                ui.switch("Automatic deformation scale", on_change=self.schedule_update) \
                    .bind_value(self.params, "auto_scale")
                self.scale_slider = self.slider("Deformation scale", "scale", 1, 500, 1, "x", 0)
                self.scale_slider.bind_enabled_from(self.params, "auto_scale",
                                                    backward=lambda v: not v)

            # ---------------- Results ----------------
            with ui.column().classes("w-full flex-1 min-w-0 gap-4"):
                with ui.card().classes("w-full"):
                    self.summary_container = ui.element("div").classes(
                        "w-full grid grid-cols-2 md:grid-cols-4 gap-3")
                    self.status_label = ui.label().classes("text-sm")

                with ui.card().classes("w-full p-2"):
                    self.truss_plot = ui.plotly(go.Figure()).classes("w-full h-[420px]")
                with ui.card().classes("w-full p-2"):
                    self.util_plot = ui.plotly(go.Figure()).classes("w-full h-[320px]")

        ui.timer(POLL_INTERVAL, self._poll)

    # ------------------------------------------------------------------
    # Update handling (debounced)
    # ------------------------------------------------------------------

    def _on_type_changed(self, _=None):
        if not hasattr(self, "panels_slider"):
            return  # fired by value binding while the UI is being built
        even = self.params["truss_type"] in ("Pratt", "Howe")
        self.panels_slider.props(f"step={2 if even else 1}")
        self.panels_note.set_visibility(even)
        if even and int(self.params["n_panels"]) % 2:
            self.params["n_panels"] = int(self.params["n_panels"]) + 1
        self.schedule_update()

    def schedule_update(self, _=None):
        self._dirty = True
        self._last_change = time.perf_counter()

    def _poll(self):
        if not self._dirty:
            return
        now = time.perf_counter()
        if (now - self._last_change >= DEBOUNCE_DELAY
                or now - self._last_update >= MAX_UPDATE_INTERVAL):
            self.update_model()

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------

    def update_model(self):
        self._dirty = False
        self._last_update = time.perf_counter()

        p = self.params
        b = self.bridge
        b.truss_type = p["truss_type"].lower()
        b.width = float(p["width"])
        b.height = float(p["height"])
        n = int(p["n_panels"])
        if b.truss_type in ("pratt", "howe") and n % 2:
            n += 1
        b.n_panels = n
        b.E = p["E"] * 1e9
        b.fy = p["fy"] * 1e6
        b.A_chord = p["A_chord"] * 1e-4
        b.A_web = p["A_web"] * 1e-4
        b.deck_load = p["deck_load"] * 1e3

        try:
            b.point_loads = []
            b.generate()
            if p["point_load"] > 0:
                node = b.bottom_nodes[round(p["point_pos"] * b.n_panels)]
                b.add_point_load(node, Fy=-p["point_load"] * 1e3)
            b.solve()
        except Exception as exc:
            self.status_label.set_text(f"Error: {exc}")
            self.status_label.classes(replace="text-sm text-red-700")
            return

        if p["auto_scale"]:
            scale = 0.1 * b.height / max(b.max_deflection, 1e-12)
            p["scale"] = float(np.clip(round(scale), 1, 500))
        else:
            scale = p["scale"]

        self.truss_plot.update_figure(self.truss_figure(scale))
        self.util_plot.update_figure(self.util_figure())
        self.update_summary()

    # ------------------------------------------------------------------
    # Figures
    # ------------------------------------------------------------------

    def _hover_texts(self):
        b = self.bridge
        sigma = b.stresses / 1e6
        util = b.utilisation * 100
        return [
            f"<b>Element {i}</b> ({b.groups[i]})<br>"
            f"N = {b.N[i] / 1e3:.1f} kN<br>"
            f"σ = {sigma[i]:.1f} MPa<br>"
            f"Utilisation = {util[i]:.1f} %"
            for i in range(b.n_elements)
        ]

    def truss_figure(self, scale):
        b = self.bridge
        coords = b.coords
        deformed = coords + scale * b.displacements
        Nk = b.N / 1e3
        nmax = max(np.abs(Nk).max(), 1e-9)
        colors = sample_colorscale(FORCE_COLORSCALE, list((Nk + nmax) / (2 * nmax)))
        hover = self._hover_texts()

        fig = go.Figure()

        # Undeformed shape as one trace with None separators
        xs, ys = [], []
        for n1, n2 in b.elements:
            xs += [coords[n1, 0], coords[n2, 0], None]
            ys += [coords[n1, 1], coords[n2, 1], None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="Undeformed",
                                 line=dict(color="#b0b0b0", width=1, dash="dash"),
                                 hoverinfo="skip"))

        # Deformed members, coloured by normal force. Hover on the line
        # (end points and midpoint) shows member results.
        for i, (n1, n2) in enumerate(b.elements):
            x1, y1 = deformed[n1]
            x2, y2 = deformed[n2]
            fig.add_trace(go.Scatter(
                x=[x1, (x1 + x2) / 2, x2], y=[y1, (y1 + y2) / 2, y2],
                mode="lines", line=dict(color=colors[i], width=6),
                hovertext=[hover[i]] * 3, hoverinfo="text",
                showlegend=False))

        # Invisible midpoint markers carry the colour bar
        mid = deformed[b.elements].mean(axis=1)
        fig.add_trace(go.Scatter(
            x=mid[:, 0], y=mid[:, 1], mode="markers",
            marker=dict(size=10, color=Nk, colorscale=FORCE_COLORSCALE,
                        cmin=-nmax, cmax=nmax, opacity=0,
                        colorbar=dict(title=dict(text="N [kN]", side="right"),
                                      thickness=14)),
            hovertext=hover, hoverinfo="text", showlegend=False))

        fig.add_trace(go.Scatter(x=deformed[:, 0], y=deformed[:, 1], mode="markers",
                                 marker=dict(size=5, color="black"),
                                 hoverinfo="skip", showlegend=False))

        # Supports
        s = 0.03 * b.width
        for node, fill in ((b.bottom_nodes[0], "#888"), (b.bottom_nodes[-1], "white")):
            x, y = coords[node]
            fig.add_shape(type="path",
                          path=f"M {x} {y} L {x - s / 2} {y - s} L {x + s / 2} {y - s} Z",
                          fillcolor=fill, line=dict(color="black", width=1))

        fig.update_layout(
            title=dict(text=f"{b.truss_type.capitalize()} truss – normal forces on "
                            f"deformed shape (scale {scale:.0f}×)", x=0.01),
            margin=dict(l=50, r=20, t=45, b=40),
            plot_bgcolor="white",
            hovermode="closest",
            uirevision="truss",
            showlegend=False,
        )
        fig.update_xaxes(title="x [m]", showgrid=True, gridcolor="#eee", zeroline=False)
        fig.update_yaxes(title="y [m]", scaleanchor="x", scaleratio=1,
                         showgrid=True, gridcolor="#eee", zeroline=False)
        return self._with_config(fig)

    def util_figure(self):
        b = self.bridge
        util = b.utilisation * 100
        colors = ["#d62728" if u > 100 else "#ff9f1c" if u > 80 else "#2ca02c" for u in util]

        fig = go.Figure(go.Bar(x=np.arange(b.n_elements), y=util, marker_color=colors,
                               hovertext=self._hover_texts(), hoverinfo="text"))
        fig.add_hline(y=100, line=dict(color="black", dash="dash", width=1),
                      annotation_text="100 %", annotation_position="top left")
        fig.update_layout(
            title=dict(text="Member utilisation |σ| / fy", x=0.01),
            margin=dict(l=50, r=20, t=45, b=40),
            plot_bgcolor="white",
            yaxis=dict(title="Utilisation [%]", range=[0, max(110, util.max() * 1.1)],
                       gridcolor="#eee"),
            xaxis=dict(title="Element"),
            bargap=0.15,
        )
        return self._with_config(fig)

    @staticmethod
    def _with_config(fig):
        figure = fig.to_plotly_json()
        figure["config"] = PLOT_CONFIG
        return figure

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def update_summary(self):
        b = self.bridge
        sigma = b.stresses / 1e6
        util = b.utilisation * 100
        defl = b.max_deflection
        items = [
            ("Max deflection", f"{defl * 1e3:.1f} mm", f"L/{b.width / defl:.0f}"),
            ("Max tension", f"{sigma.max():.1f} MPa", f"N = {b.N.max() / 1e3:.0f} kN"),
            ("Max compression", f"{sigma.min():.1f} MPa", f"N = {b.N.min() / 1e3:.0f} kN"),
            ("Max utilisation", f"{util.max():.1f} %", f"element {util.argmax()}"),
        ]

        self.summary_container.clear()
        with self.summary_container:
            for title, value, sub in items:
                with ui.column().classes("gap-0 p-2 rounded bg-slate-50"):
                    ui.label(title).classes("text-xs text-gray-500 uppercase")
                    color = "text-red-700" if title == "Max utilisation" and util.max() > 100 else ""
                    ui.label(value).classes(f"text-xl font-semibold {color}")
                    ui.label(sub).classes("text-xs text-gray-500")

        n_over = int(np.sum(util > 100))
        total = b.deck_load * b.width - sum(pl[2] for pl in b.point_loads)
        info = (f"{b.n_nodes} nodes, {b.n_elements} elements · "
                f"total load {total / 1e3:.0f} kN · ")
        if n_over:
            self.status_label.set_text(info + f"{n_over} member(s) exceed the yield strength")
            self.status_label.classes(replace="text-sm text-red-700")
        else:
            self.status_label.set_text(info + "all members below yield")
            self.status_label.classes(replace="text-sm text-green-700")


@ui.page("/")
def index():
    TrussBridgeApp()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Truss Bridge Designer", reload=False)
