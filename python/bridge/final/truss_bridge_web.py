# -*- coding: utf-8 -*-
"""
Interactive web application for the parametric truss bridge in
truss_bridge.py, built with NiceGUI and Plotly.

Run with ``python truss_bridge_web.py`` and open http://localhost:8080.
Extra dependencies: ``pip install nicegui plotly``.

Every parameter change rebuilds and re-solves the model and updates the
plots. Sliders report changes while being dragged; NiceGUI throttles
these events so the browser stays smooth. Each browser tab gets its own
independent model.
"""

import numpy as np
from nicegui import ui
from plotly.colors import get_colorscale, sample_colorscale

from truss_bridge import TrussBridge

GROUP_NAMES = {
    TrussBridge.CHORD: "chord",
    TrussBridge.VERTICAL: "vertical",
    TrussBridge.DIAGONAL: "diagonal",
}

# Normal forces: blue = compression, red = tension
FORCE_COLORSCALE = get_colorscale("RdBu_r")

# Utilisation 0-100 % from green to red; overloaded members get a distinct
# "over" colour so they stand out immediately. The colour bar extends to
# UTIL_MAX to show the over colour.
UTIL_COLORSCALE = [
    [0.0, "rgb(26, 152, 80)"],
    [0.5, "rgb(254, 224, 139)"],
    [1.0, "rgb(215, 48, 39)"],
]
UTIL_OVER_COLOR = "rgb(123, 31, 162)"
UTIL_MAX = 110.0
_LIMIT = 100.0 / UTIL_MAX
UTIL_COLORBAR_SCALE = [
    [0.0, UTIL_COLORSCALE[0][1]],
    [0.5 * _LIMIT, UTIL_COLORSCALE[1][1]],
    [_LIMIT, UTIL_COLORSCALE[2][1]],
    [_LIMIT, UTIL_OVER_COLOR],
    [1.0, UTIL_OVER_COLOR],
]

# Number of distinct colours used when drawing colour-coded elements
COLOR_LEVELS = 64

PLOT_CONFIG = {"displaylogo": False, "responsive": True}


# ----------------------------------------------------------------------
# Plotly trace helpers
# ----------------------------------------------------------------------

def segment_xy(segments):
    """x and y lists drawing all segments in one trace, separated by None."""
    x, y = [], []
    for (x0, y0), (x1, y1) in segments:
        x += [x0, x1, None]
        y += [y0, y1, None]
    return x, y


def colored_segments(segments, values, colorscale, vmin, vmax, width,
                     over_color=None):
    """
    Traces drawing each segment in the colour of its value.

    A Plotly line has a single colour per trace, so the values are binned
    into COLOR_LEVELS colours and each bin is drawn as one trace. This
    keeps the number of traces small even for bridges with many members.
    Values above vmax are drawn in ``over_color`` if given.
    """
    t = np.clip((values - vmin) / (vmax - vmin), 0.0, 1.0)
    levels = np.round(t * (COLOR_LEVELS - 1)).astype(int)
    used = np.unique(levels)
    colors = sample_colorscale(colorscale, used / (COLOR_LEVELS - 1))
    bins = [levels == level for level in used]
    if over_color is not None:
        over = values > vmax
        bins = [b & ~over for b in bins] + [over]
        colors.append(over_color)

    traces = []
    for selected, color in zip(bins, colors):
        if not selected.any():
            continue
        x, y = segment_xy(segments[selected])
        traces.append(dict(
            type="scatter", x=x, y=y, mode="lines",
            line=dict(color=color, width=width),
            hoverinfo="skip", showlegend=False,
        ))
    return traces


def element_markers(mids, values, colorscale, cmin, cmax, colorbar,
                    hovertext, labels=None):
    """Midpoint markers carrying the colour bar, hover info and labels."""
    return dict(
        type="scatter", x=mids[:, 0].tolist(), y=mids[:, 1].tolist(),
        mode="markers+text" if labels else "markers",
        marker=dict(
            size=8, color=values.tolist(), colorscale=colorscale,
            cmin=cmin, cmax=cmax, colorbar=colorbar, showscale=True,
            line=dict(width=1, color="white"),
        ),
        text=labels, textposition="top center", textfont=dict(size=10),
        hovertext=hovertext, hoverinfo="text", showlegend=False,
    )


def truss_layout(title, bridge, y_range):
    margin = 0.05 * bridge.width
    return dict(
        title=dict(text=title, font=dict(size=14), x=0.01, xanchor="left"),
        xaxis=dict(range=[-margin, bridge.width + margin], title="x (m)",
                   zeroline=False, gridcolor="#eee"),
        yaxis=dict(range=y_range, scaleanchor="x", scaleratio=1,
                   title="y (m)", zeroline=False, gridcolor="#eee"),
        margin=dict(l=50, r=10, t=40, b=40),
        plot_bgcolor="white", hovermode="closest", showlegend=False,
    )


# ----------------------------------------------------------------------
# User interface
# ----------------------------------------------------------------------

def slider_input(label, minimum, maximum, value, step, suffix, decimals,
                 on_change):
    """A slider and a number field kept in sync. Returns the slider."""
    with ui.row().classes("w-full items-center no-wrap gap-2"):
        ui.label(label).classes("w-24 shrink-0 text-sm")
        slider = ui.slider(min=minimum, max=maximum, value=value, step=step,
                           on_change=on_change).classes("grow")
        number = ui.number(min=minimum, max=maximum, step=step, suffix=suffix,
                           format=f"%.{decimals}f")
        number.props("dense outlined").classes("w-32 shrink-0")
        # An empty number field keeps the current slider value
        number.bind_value(
            slider, forward=lambda v: slider.value if v is None else v)
    return slider


class TrussBridgeApp:
    """Parameter panel on the left, plots on the right."""

    def __init__(self):
        self._updating = False

        with ui.header().classes("items-center bg-slate-800"):
            ui.label("Truss Bridge Designer").classes("text-lg font-semibold")

        with ui.element("div").classes(
                "w-full flex flex-col lg:flex-row gap-4 items-start"):
            with ui.column().classes("w-full lg:w-[440px] shrink-0 gap-3"):
                self._create_geometry_card()
                self._create_material_card()
                self._create_view_card()
                self._create_summary_card()
            with ui.column().classes("w-full lg:flex-1 min-w-0 gap-3"):
                self.deformed_plot = self._create_plot()
                self.force_plot = self._create_plot()
                self.util_plot = self._create_plot()

        self.update_model()

    # ------------------------------------------------------------------
    # Control groups
    # ------------------------------------------------------------------

    @staticmethod
    def _card(title):
        card = ui.card().classes("w-full gap-1")
        with card:
            ui.label(title).classes("text-base font-semibold")
        return card

    @staticmethod
    def _create_plot():
        with ui.card().classes("w-full p-1"):
            return ui.plotly({"data": [], "config": PLOT_CONFIG}).classes(
                "w-full h-72")

    def _create_geometry_card(self):
        update = self.update_model
        with self._card("Geometry"):
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                ui.label("Truss type").classes("w-24 shrink-0 text-sm")
                self.type_toggle = ui.toggle(
                    ["Pratt", "Howe", "Warren"], value="Pratt",
                    on_change=self._on_type_changed).props("dense no-caps")
            self.width_input = slider_input(
                "Width (span)", 5.0, 200.0, 40.0, 0.5, " m", 1, update)
            self.height_input = slider_input(
                "Height", 0.5, 30.0, 5.0, 0.05, " m", 2, update)
            self.panels_input = slider_input(
                "Panels", 2, 60, 8, 2, "", 0, self._on_panels_changed)

    def _create_material_card(self):
        update = self.update_model
        with self._card("Material, sections and load"):
            self.E_input = slider_input(
                "E-modulus", 1.0, 250.0, 210.0, 0.5, " GPa", 1, update)
            self.fy_input = slider_input(
                "Yield strength", 100.0, 700.0, 355.0, 5.0, " MPa", 0, update)
            self.A_chord_input = slider_input(
                "A chord", 1.0, 500.0, 100.0, 0.5, " cm²", 1, update)
            self.A_vert_input = slider_input(
                "A vertical", 1.0, 500.0, 40.0, 0.5, " cm²", 1, update)
            self.A_diag_input = slider_input(
                "A diagonal", 1.0, 500.0, 60.0, 0.5, " cm²", 1, update)
            self.load_input = slider_input(
                "Deck load", 0.0, 500.0, 50.0, 0.5, " kN/m", 1, update)

    def _create_view_card(self):
        update = self.update_model
        with self._card("View"):
            self.auto_scale = ui.checkbox(
                "Automatic deformation scale", value=True,
                on_change=self._on_auto_scale_changed)
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                ui.label("Scale").classes("w-24 shrink-0 text-sm")
                self.scale_input = ui.number(
                    value=100.0, min=0.0, max=1e6, step=10.0, format="%.0f",
                    on_change=update,
                ).props("dense outlined").classes("w-32")
                self.scale_input.disable()
            self.undeformed_check = ui.checkbox(
                "Show undeformed shape", value=True, on_change=update)
            self.labels_check = ui.checkbox(
                "Show element values (kN / %)", value=False, on_change=update)

    def _create_summary_card(self):
        with self._card("Summary"):
            self.summary_labels = {}
            with ui.grid(columns="auto 1fr").classes("w-full gap-x-4 gap-y-1"):
                for key in ("Nodes / elements", "Total load", "Max deflection",
                            "Deflection ratio", "Max tension",
                            "Max compression", "Max stress", "Utilisation",
                            "Overloaded members"):
                    ui.label(key).classes("text-sm text-gray-600")
                    self.summary_labels[key] = ui.label("-").classes("text-sm")

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _requires_even_panels(self):
        return self.type_toggle.value.lower() in ("pratt", "howe")

    def _on_type_changed(self):
        step = 2 if self._requires_even_panels() else 1
        self.panels_input.props(f"step={step}")
        self._on_panels_changed()

    def _on_panels_changed(self):
        # Pratt and Howe need an even number of panels - round up
        value = int(round(self.panels_input.value))
        if self._requires_even_panels() and value % 2:
            self.panels_input.value = value + 1  # triggers a new update
            return
        self.update_model()

    def _on_auto_scale_changed(self):
        if self.auto_scale.value:
            self.scale_input.disable()
        else:
            self.scale_input.enable()
        self.update_model()

    def update_model(self):
        # Setting the scale field below fires its change event again
        if self._updating:
            return

        n_panels = int(round(self.panels_input.value))
        if self._requires_even_panels() and n_panels % 2:
            n_panels += 1

        try:
            bridge = TrussBridge(
                width=self.width_input.value,
                height=self.height_input.value,
                n_panels=n_panels,
                truss_type=self.type_toggle.value.lower(),
                E=self.E_input.value * 1e9,
                A_chord=self.A_chord_input.value * 1e-4,
                A_vertical=self.A_vert_input.value * 1e-4,
                A_diagonal=self.A_diag_input.value * 1e-4,
                deck_load=self.load_input.value * 1e3,
            )
            bridge.solve()
        except (ValueError, np.linalg.LinAlgError) as error:
            ui.notify(f"Could not solve the model: {error}", type="negative")
            return

        if self.auto_scale.value:
            scale = 0.1 * bridge.height / max(bridge.max_deflection, 1e-12)
            scale = min(scale, 1e6)
            self._updating = True
            self.scale_input.value = round(scale)
            self._updating = False
        else:
            scale = self.scale_input.value or 0.0

        fy = self.fy_input.value * 1e6
        self._update_plots(bridge, fy, scale)
        self._update_summary(bridge, fy)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _update_plots(self, bridge, fy, scale):
        coords = bridge.coords
        conn = np.array([(i, j) for i, j, _ in bridge.elements])
        segments = coords[conn]
        mids = segments.mean(axis=1)
        u = bridge.a.reshape(-1, 2)
        def_coords = coords + scale * u
        h = bridge.height

        N = bridge.normal_forces / 1e3
        stresses = bridge.stresses() / 1e6
        util = 100.0 * bridge.utilisation(fy)
        nmax = max(np.max(np.abs(N)), 1e-9)

        hovertext = [
            f"Element {k + 1} ({GROUP_NAMES[group]})<br>"
            f"N = {n:.1f} kN<br>σ = {s:.1f} MPa<br>Utilisation = {ut:.0f} %"
            for k, ((_, _, group), n, s, ut)
            in enumerate(zip(bridge.elements, N, stresses, util))
        ]
        show_labels = self.labels_check.value

        # Deformed shape, coloured by normal force
        data = []
        if self.undeformed_check.value:
            x, y = segment_xy(segments)
            data.append(dict(type="scatter", x=x, y=y, mode="lines",
                             line=dict(color="#999", width=1, dash="dash"),
                             hoverinfo="skip"))
        data += colored_segments(def_coords[conn], N, FORCE_COLORSCALE,
                                 -nmax, nmax, 2.5)
        data.append(dict(
            type="scatter", x=def_coords[:, 0].tolist(),
            y=def_coords[:, 1].tolist(), mode="markers",
            marker=dict(size=5, color="black"),
            hovertext=[f"Node {k + 1}<br>ux = {ux * 1e3:.2f} mm<br>"
                       f"uy = {uy * 1e3:.2f} mm" for k, (ux, uy) in enumerate(u)],
            hoverinfo="text",
        ))
        supports = coords[[bridge.bottom_node(0),
                           bridge.bottom_node(bridge.n_panels)]]
        data.append(dict(
            type="scatter", x=supports[:, 0].tolist(),
            y=(supports[:, 1] - 0.04 * h).tolist(), mode="markers",
            marker=dict(symbol="triangle-up", size=14, color="black"),
            hoverinfo="skip",
        ))
        y_min = min(-0.15 * h, def_coords[:, 1].min() - 0.1 * h)
        layout = truss_layout(
            f"{bridge.truss_type.capitalize()} truss - deformed shape "
            f"(scale {scale:.0f}×, max deflection "
            f"{bridge.max_deflection * 1e3:.1f} mm)",
            bridge, [y_min, 1.15 * h])
        self._set_figure(self.deformed_plot, data, layout)

        y_range = [-0.15 * h, 1.15 * h]

        # Normal forces on the undeformed geometry
        data = colored_segments(segments, N, FORCE_COLORSCALE, -nmax, nmax, 5)
        data.append(element_markers(
            mids, N, FORCE_COLORSCALE, -nmax, nmax,
            dict(title=dict(text="N (kN)"), thickness=12),
            hovertext, [f"{n:.0f}" for n in N] if show_labels else None))
        layout = truss_layout(
            "Normal forces (red = tension, blue = compression)",
            bridge, y_range)
        self._set_figure(self.force_plot, data, layout)

        # Utilisation on a fixed 0-100 % scale
        data = colored_segments(segments, util, UTIL_COLORSCALE, 0.0, 100.0,
                                5, over_color=UTIL_OVER_COLOR)
        data.append(element_markers(
            mids, np.minimum(util, UTIL_MAX), UTIL_COLORBAR_SCALE, 0.0, UTIL_MAX,
            dict(title=dict(text="Util. (%)"), thickness=12,
                 tickvals=[0, 25, 50, 75, 100, UTIL_MAX],
                 ticktext=["0", "25", "50", "75", "100", ">100"]),
            hovertext, [f"{ut:.0f}%" for ut in util] if show_labels else None))
        n_over = np.count_nonzero(util > 100.0)
        layout = truss_layout(
            f"Utilisation |σ| / fy (max {util.max():.0f} %, {n_over} "
            f"member{'s' if n_over != 1 else ''} overloaded)",
            bridge, y_range)
        self._set_figure(self.util_plot, data, layout)

    @staticmethod
    def _set_figure(plot, data, layout):
        plot.figure = {"data": data, "layout": layout, "config": PLOT_CONFIG}
        plot.update()

    def _update_summary(self, bridge, fy):
        stresses = bridge.stresses() / 1e6
        N = bridge.normal_forces / 1e3
        max_stress = np.max(np.abs(stresses))
        element_util = bridge.utilisation(fy)
        utilisation = element_util.max()
        n_over = np.count_nonzero(element_util > 1.0)
        delta = bridge.max_deflection
        ratio = f"L / {bridge.width / delta:.0f}" if delta > 0 else "-"

        s = self.summary_labels
        s["Nodes / elements"].text = f"{bridge.n_nodes} / {len(bridge.elements)}"
        s["Total load"].text = f"{bridge.deck_load * bridge.width / 1e3:.1f} kN"
        s["Max deflection"].text = f"{delta * 1e3:.2f} mm"
        s["Deflection ratio"].text = ratio
        s["Max tension"].text = f"{max(N.max(), 0):.1f} kN"
        s["Max compression"].text = f"{min(N.min(), 0):.1f} kN"
        s["Max stress"].text = f"{max_stress:.1f} MPa"
        s["Utilisation"].text = f"{utilisation * 100:.0f} %"
        color = "#c62828" if utilisation > 1.0 else "#2e7d32"
        s["Utilisation"].style(f"color: {color}; font-weight: bold")
        s["Overloaded members"].text = f"{n_over} of {len(bridge.elements)}"
        s["Overloaded members"].style(f"color: {color}")


@ui.page("/")
def index():
    TrussBridgeApp()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Truss Bridge Designer")
