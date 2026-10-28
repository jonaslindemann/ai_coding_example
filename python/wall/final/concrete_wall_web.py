# -*- coding: utf-8 -*-
"""
Interactive web application for the parametric concrete wall in
concrete_wall.py, built with NiceGUI and Plotly.

Run with ``python concrete_wall_web.py`` and open http://localhost:8080.
Extra dependencies: ``pip install nicegui plotly``.

The input parameters are grouped in tabs on the left (geometry, openings,
material, loads & supports) and the results are shown in tabs on the right.

To keep the interaction responsive:
    - rapid parameter changes are coalesced with a short delay before the
      model is rebuilt and solved,
    - the model is solved in a background thread so the page stays
      interactive; results of outdated solves are discarded,
    - only the visible result tab is sent to the browser; the other tabs
      are generated when they are selected.

The mesh is a structured grid with the openings removed, so nodal stresses
can be placed back on the grid and drawn as Plotly contour plots.
"""

import asyncio
import time

import numpy as np
from nicegui import background_tasks, run, ui
from plotly.colors import get_colorscale, sample_colorscale

from concrete_wall import ConcreteWall

# Delay (s) after the last input change before the model is solved
DEBOUNCE = 0.25

# Number of distinct colours used for filled element plots
COLOR_LEVELS = 32

PLOT_CONFIG = {"displaylogo": False, "responsive": True}

VIRIDIS = get_colorscale("Viridis")
INFERNO = get_colorscale("Inferno")
RDBU_R = get_colorscale("RdBu_r")      # blue = compression, red = tension
TENSION, COMPRESSION = "rgb(214, 39, 40)", "rgb(31, 119, 180)"


class OpeningError(ValueError):
    """Invalid opening, ``row`` is its index in the openings list."""

    def __init__(self, row, error):
        super().__init__(str(error))
        self.row = row


def build_and_solve(params):
    """Create and solve a ConcreteWall from plain input values."""
    wall = ConcreteWall(**params["wall"])
    for row, o in enumerate(params["openings"]):
        try:
            if o["kind"] == "door":
                wall.add_door(o["x"], o["w"], o["h"])
            else:
                wall.add_window(o["x"], o["y"], o["w"], o["h"])
        except ValueError as error:
            raise OpeningError(row, error) from None
    if params["supports"] is None:
        wall.set_fully_supported()
    else:
        wall.set_freely_supported(**params["supports"])
    wall.solve()
    return wall


# ----------------------------------------------------------------------
# Plotly figure helpers
# ----------------------------------------------------------------------

def segment_xy(segments):
    """x and y lists drawing all segments in one trace, separated by None."""
    n = len(segments)
    xy = np.full((n, 3, 2), np.nan)
    xy[:, :2] = np.round(segments, 5)
    x, y = xy.reshape(-1, 2).T
    return ([None if np.isnan(v) else v for v in x],
            [None if np.isnan(v) else v for v in y])


def polygon_xy(polygons):
    """x and y lists drawing closed polygons in one trace, separated by None."""
    closed = np.concatenate([polygons, polygons[:, :1]], axis=1)
    xy = np.full((len(polygons), closed.shape[1] + 1, 2), np.nan)
    xy[:, :-1] = np.round(closed, 5)
    x, y = xy.reshape(-1, 2).T
    return ([None if np.isnan(v) else v for v in x],
            [None if np.isnan(v) else v for v in y])


def filled_elements(polygons, values, colorscale, vmin, vmax):
    """
    Traces filling each element polygon in the colour of its value.

    A Plotly trace has a single fill colour, so the values are binned into
    COLOR_LEVELS colours and each bin is drawn as one trace.
    """
    t = np.clip((values - vmin) / max(vmax - vmin, 1e-30), 0.0, 1.0)
    levels = np.round(t * (COLOR_LEVELS - 1)).astype(int)
    used = np.unique(levels)
    colors = sample_colorscale(colorscale, used / (COLOR_LEVELS - 1))

    traces = []
    for level, color in zip(used, colors):
        x, y = polygon_xy(polygons[levels == level])
        traces.append(dict(
            type="scatter", x=x, y=y, mode="lines", fill="toself",
            fillcolor=color, line=dict(color=color, width=0.5),
            hoverinfo="skip",
        ))
    return traces


def mesh_edges(wall, coords):
    """Unique element edges as an (n, 2, 2) array of segments."""
    edges = wall.topo[:, [0, 1, 1, 2, 2, 3, 3, 0]].reshape(-1, 2)
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    return coords[edges]


def grid_values(wall, nodal):
    """
    Place nodal values on the structured grid of the mesh.

    Grid points without a node (inside openings) are None so they show up
    as gaps in the contour plot.
    """
    x = np.round(wall.coords[:, 0], 9)
    y = np.round(wall.coords[:, 1], 9)
    xs, ys = np.unique(x), np.unique(y)
    z = np.full((len(ys), len(xs)), np.nan)
    z[np.searchsorted(ys, y), np.searchsorted(xs, x)] = nodal
    z = [[None if np.isnan(v) else round(float(v), 5) for v in row] for row in z]
    return xs.tolist(), ys.tolist(), z


def wall_shapes(wall, outline_only=False):
    """Wall outline, openings and support bearings as Plotly shapes."""
    if outline_only:
        line = dict(color="#888", width=1, dash="dash")
    else:
        line = dict(color="black", width=1)
    shapes = [dict(type="rect", x0=0, y0=0, x1=wall.width, y1=wall.height,
                   line=line, layer="above")]
    for o in wall.openings:
        # A white fill hides contour interpolation across the opening
        shapes.append(dict(
            type="rect", x0=o.x, y0=o.y, x1=o.x2, y1=o.y2, line=line,
            fillcolor="rgba(0,0,0,0)" if outline_only else "white",
            layer="above"))
    for x1, x2, _ in wall.support_segments():
        shapes.append(dict(type="line", x0=x1, y0=0, x1=x2, y1=0,
                           line=dict(color="black", width=5), layer="above"))
    return shapes


def support_markers(wall):
    """Triangles under discrete bearings (filled = pinned, open = roller)."""
    if wall.support_type != "free":
        return []
    segments = wall.support_segments()
    return [dict(
        type="scatter", mode="markers",
        x=[0.5 * (x1 + x2) for x1, x2, _ in segments],
        y=[-0.025 * max(wall.width, wall.height)] * len(segments),
        marker=dict(symbol="triangle-up", size=12,
                    color=["black" if pinned else "white"
                           for _, _, pinned in segments],
                    line=dict(color="black", width=1.5)),
        hovertext=[f"{'Pinned' if pinned else 'Roller'} bearing "
                   f"[{x1:.2f}, {x2:.2f}] m" for x1, x2, pinned in segments],
        hoverinfo="text",
    )]


def wall_layout(wall, title, shapes, legend=False):
    margin = 0.05 * max(wall.width, wall.height)
    return dict(
        title=dict(text=title, font=dict(size=14), x=0.01, xanchor="left"),
        xaxis=dict(range=[-margin, wall.width + margin], title="x (m)",
                   zeroline=False, gridcolor="#eee"),
        yaxis=dict(range=[-margin, wall.height + margin], scaleanchor="x",
                   scaleratio=1, title="y (m)", zeroline=False,
                   gridcolor="#eee"),
        shapes=shapes, margin=dict(l=50, r=10, t=40, b=40),
        plot_bgcolor="white", hovermode="closest", showlegend=legend,
        legend=dict(x=1, xanchor="right", y=1, bgcolor="rgba(255,255,255,0.8)"),
    )


def mesh_figure(wall):
    x, y = segment_xy(mesh_edges(wall, wall.coords))
    data = [dict(type="scatter", x=x, y=y, mode="lines",
                 line=dict(color="grey", width=0.6), hoverinfo="skip")]
    data += support_markers(wall)
    return data, wall_layout(
        wall, f"Mesh: {wall.n_elements} plani4e elements, {wall.n_nodes} nodes",
        wall_shapes(wall))


def deformed_figure(wall):
    scale = (0.05 * max(wall.width, wall.height)
             / max(wall.max_displacement, 1e-12))
    u = wall.a.reshape(-1, 2)
    xy = wall.coords + scale * u
    u_mag = np.linalg.norm(u, axis=1) * 1e3
    u_max = max(u_mag.max(), 1e-12)

    data = filled_elements(xy[wall.topo], u_mag[wall.topo].mean(axis=1),
                           VIRIDIS, 0.0, u_max)
    # Invisible node markers carry the colour bar and the hover information
    data.append(dict(
        type="scatter", mode="markers",
        x=np.round(xy[:, 0], 5).tolist(), y=np.round(xy[:, 1], 5).tolist(),
        marker=dict(size=6, opacity=0, color=u_mag.tolist(),
                    colorscale=VIRIDIS, cmin=0.0, cmax=u_max, showscale=True,
                    colorbar=dict(title=dict(text="|u| (mm)"), thickness=12)),
        hovertext=[f"|u| = {m:.3f} mm<br>ux = {ux * 1e3:.3f} mm<br>"
                   f"uy = {uy * 1e3:.3f} mm"
                   for m, (ux, uy) in zip(u_mag, u)],
        hoverinfo="text",
    ))
    data += support_markers(wall)
    return data, wall_layout(
        wall, f"Deformed shape (scale {scale:.0f}×, "
              f"max {wall.max_displacement * 1e3:.3f} mm)",
        wall_shapes(wall, outline_only=True))


def contour_figure(wall, values, title, label, colorscale, diverging=False):
    """Contour plot of element values averaged to the nodes (MPa)."""
    nodal = wall.nodal_values(values) / 1e6
    xs, ys, z = grid_values(wall, nodal)
    trace = dict(
        type="contour", x=xs, y=ys, z=z, colorscale=colorscale,
        ncontours=20, contours=dict(coloring="fill", showlines=False),
        line=dict(width=0), connectgaps=False,
        colorbar=dict(title=dict(text=label), thickness=12),
        hovertemplate=(f"x = %{{x:.2f}} m<br>y = %{{y:.2f}} m<br>"
                       f"{label} = %{{z:.2f}}<extra></extra>"),
    )
    if diverging:
        trace["zmid"] = 0.0
    return [trace] + support_markers(wall), wall_layout(
        wall, title, wall_shapes(wall))


def von_mises_figure(wall):
    return contour_figure(wall, wall.von_mises, "von Mises stress",
                          "σvM (MPa)", INFERNO)


def principal_figure(wall, which):
    s = wall.principal_stresses[0 if which == 1 else 1]
    name = "Major" if which == 1 else "Minor"
    return contour_figure(
        wall, s, f"{name} principal stress σ{which} "
                 f"(red = tension, blue = compression)",
        f"σ{which} (MPa)", RDBU_R, diverging=True)


def directions_figure(wall):
    """Principal stress crosses at a subset of element centroids."""
    s1, s2, theta = wall.principal_stresses
    spacing = max(wall.width, wall.height) / 25
    xc, yc = wall.ex.mean(axis=1), wall.ey.mean(axis=1)

    # Pick one element per spacing x spacing cell
    cell = np.column_stack([np.floor(xc / spacing), np.floor(yc / spacing)])
    _, pick = np.unique(cell, axis=0, return_index=True)

    # Scale on the 95th percentile so corner peaks don't shrink the rest
    sref = np.percentile(np.abs(np.concatenate([s1, s2])), 95)
    length = 0.9 * spacing / max(sref, 1e-12)
    segments = {1: [], -1: []}
    for s, ang in ((s1, theta), (s2, theta + np.pi / 2)):
        for sign in (1, -1):
            sel = pick[np.sign(s[pick]) == sign]
            mag = np.minimum(np.abs(s[sel]), sref)
            d = 0.5 * length * mag[:, None] * np.column_stack(
                [np.cos(ang[sel]), np.sin(ang[sel])])
            c = np.column_stack([xc[sel], yc[sel]])
            segments[sign].append(np.stack([c - d, c + d], axis=1))

    data = []
    for sign, color, name in ((1, TENSION, "tension"),
                              (-1, COMPRESSION, "compression")):
        x, y = segment_xy(np.concatenate(segments[sign]))
        data.append(dict(type="scatter", x=x, y=y, mode="lines", name=name,
                         line=dict(color=color, width=1.5), hoverinfo="skip"))
    data.append(dict(
        type="scatter", mode="markers", x=xc[pick].tolist(),
        y=yc[pick].tolist(), marker=dict(size=8, opacity=0),
        hovertext=[f"σ1 = {a / 1e6:.2f} MPa<br>σ2 = {b / 1e6:.2f} MPa<br>"
                   f"θ1 = {np.degrees(t):.0f}°"
                   for a, b, t in zip(s1[pick], s2[pick], theta[pick])],
        hoverinfo="text", showlegend=False,
    ))
    for trace in support_markers(wall):
        data.append(dict(trace, showlegend=False))
    return data, wall_layout(wall, "Principal stress directions",
                             wall_shapes(wall), legend=True)


RESULT_TABS = {
    "Mesh": mesh_figure,
    "Deformed": deformed_figure,
    "von Mises": von_mises_figure,
    "σ₁": lambda wall: principal_figure(wall, 1),
    "σ₂": lambda wall: principal_figure(wall, 2),
    "Principal directions": directions_figure,
}


# ----------------------------------------------------------------------
# User interface
# ----------------------------------------------------------------------

def number_input(label, value, minimum, maximum, step, decimals, suffix,
                 on_change, tooltip=None):
    field = ui.number(label=label, value=value, min=minimum, max=maximum,
                      step=step, format=f"%.{decimals}f", suffix=suffix,
                      on_change=on_change)
    field.props("dense outlined").classes("w-full")
    if tooltip:
        field.tooltip(tooltip)
    return field


class ConcreteWallApp:
    """Input tabs on the left, result tabs on the right."""

    def __init__(self):
        self.wall = None
        self.rendered_tab = None
        self._loading = True
        self._requested = 0      # counts debounced update requests
        self._solve_id = 0       # identifies the most recent solve

        # Example openings
        self.openings = [
            dict(kind="window", x=0.6, y=0.9, w=1.2, h=1.2),
            dict(kind="door", x=2.6, y=0.0, w=1.0, h=2.1),
            dict(kind="window", x=4.2, y=0.9, w=1.2, h=1.2),
        ]
        self.opening_rows = []

        with ui.header().classes("items-center bg-slate-800"):
            ui.label("Concrete Wall - CALFEM plani4e").classes(
                "text-lg font-semibold")

        with ui.element("div").classes(
                "w-full flex flex-col lg:flex-row gap-4 items-start"):
            with ui.card().classes("w-full lg:w-[480px] shrink-0 p-2"):
                self._build_input_panel()
            with ui.column().classes("w-full lg:flex-1 min-w-0 gap-3"):
                self._build_result_panel()

        self._loading = False
        ui.timer(0.1, self.update_model, once=True)

    # ------------------------------------------------------------------
    # Input panel
    # ------------------------------------------------------------------

    def _build_input_panel(self):
        with ui.tabs().props("dense no-caps align=left").classes("w-full") as tabs:
            geometry = ui.tab("Geometry")
            openings = ui.tab("Openings")
            material = ui.tab("Material")
            loads = ui.tab("Loads & supports")
        with ui.tab_panels(tabs, value=geometry).classes("w-full"):
            with ui.tab_panel(geometry).classes("gap-3"):
                self._geometry_tab()
            with ui.tab_panel(openings).classes("gap-2 px-1"):
                self._openings_tab()
            with ui.tab_panel(material).classes("gap-3"):
                self._material_tab()
            with ui.tab_panel(loads).classes("gap-3"):
                self._loads_tab()

        with ui.row().classes("w-full items-center justify-between px-4"):
            self.auto_update = ui.checkbox("Update automatically", value=True)
            ui.button("Solve", on_click=self.update_model).props("unelevated")

    def _geometry_tab(self):
        update = self.schedule_update
        self.width_input = number_input(
            "Width", 6.0, 0.5, 50.0, 0.1, 2, " m", update)
        self.height_input = number_input(
            "Height", 3.0, 0.5, 20.0, 0.1, 2, " m", update)
        self.thickness_input = number_input(
            "Thickness", 0.2, 0.05, 2.0, 0.01, 3, " m", update)
        self.el_size_input = number_input(
            "Element size", 0.1, 0.02, 1.0, 0.01, 3, " m", update,
            "Smaller elements give more accurate results but slower updates.")

    def _material_tab(self):
        update = self.schedule_update
        self.E_input = number_input(
            "Young's modulus E", 33.0, 1.0, 100.0, 1.0, 1, " GPa", update)
        self.nu_input = number_input(
            "Poisson's ratio ν", 0.2, 0.0, 0.49, 0.01, 3, "", update)
        self.density_input = number_input(
            "Density", 2500.0, 0.0, 10000.0, 50.0, 0, " kg/m³", update)

    def _loads_tab(self):
        update = self.schedule_update
        self.top_load_input = number_input(
            "Vertical top load", 100.0, -10000.0, 10000.0, 10.0, 1, " kN/m",
            update, "Positive values act downwards.")
        self.hor_load_input = number_input(
            "Horizontal top load", 20.0, -10000.0, 10000.0, 5.0, 1, " kN/m",
            update, "Positive values act to the right.")
        self.self_weight_check = ui.checkbox(
            "Include self weight", value=True, on_change=update)

        ui.label("Supports").classes("text-sm font-semibold mt-2")
        self.support_radio = ui.radio(
            {"fixed": "Fully supported bottom edge",
             "free": "Freely supported on bearings"},
            value="fixed", on_change=update)

        def free(value):
            return value == "free"

        self.ends_check = ui.checkbox(
            "Supports at both ends", value=True, on_change=update)
        self.positions_input = ui.input(
            "Intermediate supports (x)", value="2.3, 3.9",
            placeholder="e.g. 2.0, 4.5", on_change=update,
        ).props("dense outlined").classes("w-full")
        self.positions_input.tooltip(
            "Comma separated x-coordinates of the intermediate support centres.")
        self.support_length_input = number_input(
            "Bearing length", 0.3, 0.01, 5.0, 0.05, 2, " m", update)
        for field in (self.ends_check, self.positions_input,
                      self.support_length_input):
            field.bind_enabled_from(self.support_radio, "value", backward=free)
        ui.label("Freely supported: the leftmost bearing is pinned, the "
                 "others are rollers (vertical support only).").classes(
            "text-xs text-gray-500")

    def _openings_tab(self):
        with ui.row().classes("w-full no-wrap gap-1 text-xs text-gray-500 px-1"):
            for text, width in (("Type", "w-24"), ("x (m)", "w-[4.5rem]"),
                                ("y (m)", "w-[4.5rem]"), ("Width", "w-[4.5rem]"),
                                ("Height", "w-[4.5rem]")):
                ui.label(text).classes(width)
        self.openings_editor()
        with ui.row().classes("gap-2"):
            ui.button("Add window", icon="add", on_click=lambda: self._add_opening(
                dict(kind="window", x=0.5, y=0.9, w=1.0, h=1.2))).props("flat dense")
            ui.button("Add door", icon="add", on_click=lambda: self._add_opening(
                dict(kind="door", x=0.5, y=0.0, w=1.0, h=2.1))).props("flat dense")
        ui.label("x, y is the lower-left corner. Doors always start at y = 0."
                 ).classes("text-xs text-gray-500")

    @ui.refreshable_method
    def openings_editor(self):
        self.opening_rows = []
        for opening in self.openings:
            with ui.row().classes(
                    "w-full items-center no-wrap gap-1 rounded px-1") as row:
                ui.select(
                    ["window", "door"], value=opening["kind"],
                    on_change=lambda e, o=opening: self._set_kind(o, e.value),
                ).props("dense outlined").classes("w-24")
                for key in ("x", "y", "w", "h"):
                    field = ui.number(
                        value=opening[key], min=0.0, max=100.0, step=0.05,
                        format="%.2f",
                        on_change=lambda e, o=opening, k=key:
                            self._set_opening_value(o, k, e.value),
                    ).props("dense outlined").classes("w-[4.5rem]")
                    if key == "y" and opening["kind"] == "door":
                        field.disable()
                ui.button(icon="delete",
                          on_click=lambda o=opening: self._remove_opening(o)
                          ).props("flat dense round size=sm")
            self.opening_rows.append(row)

    def _add_opening(self, opening):
        self.openings.append(opening)
        self.openings_editor.refresh()
        self.schedule_update()

    def _remove_opening(self, opening):
        self.openings.remove(opening)
        self.openings_editor.refresh()
        self.schedule_update()

    def _set_kind(self, opening, kind):
        opening["kind"] = kind
        self.openings_editor.refresh()   # enable/disable the y field
        self.schedule_update()

    def _set_opening_value(self, opening, key, value):
        if value is not None:
            opening[key] = value
            self.schedule_update()

    def _highlight_opening(self, bad_row):
        """Mark the opening row that caused a validation error (None clears)."""
        for i, row in enumerate(self.opening_rows):
            if i == bad_row:
                row.classes(add="bg-red-100")
            else:
                row.classes(remove="bg-red-100")

    # ------------------------------------------------------------------
    # Result panel
    # ------------------------------------------------------------------

    def _build_result_panel(self):
        with ui.card().classes("w-full p-2 gap-1"):
            with ui.tabs(value="von Mises", on_change=self.render_current
                         ).props("dense no-caps align=left").classes("w-full") as tabs:
                for name in RESULT_TABS:
                    ui.tab(name)
            self.result_tabs = tabs
            self.plot = ui.plotly({"data": [], "config": PLOT_CONFIG}).classes(
                "w-full h-[60vh] min-h-[360px]")
            with ui.row().classes("items-center gap-2 px-2"):
                self.spinner = ui.spinner(size="sm")
                self.status = ui.label("Solving ...").classes("text-sm")
        with ui.card().classes("w-full p-3"):
            ui.label("Summary").classes("text-base font-semibold")
            self.summary = ui.label("-").classes(
                "whitespace-pre font-mono text-sm overflow-x-auto w-full")

    def render_current(self):
        """Send the figure of the visible result tab to the browser."""
        tab = self.result_tabs.value
        if self.wall is None or tab == self.rendered_tab:
            return
        data, layout = RESULT_TABS[tab](self.wall)
        self.plot.figure = {"data": data, "layout": layout,
                            "config": PLOT_CONFIG}
        self.plot.update()
        self.rendered_tab = tab

    # ------------------------------------------------------------------
    # Model update
    # ------------------------------------------------------------------

    def schedule_update(self, *_):
        if self._loading or not self.auto_update.value:
            return
        self._requested += 1
        background_tasks.create(self._debounced_update(self._requested))

    async def _debounced_update(self, request):
        await asyncio.sleep(DEBOUNCE)
        if request == self._requested:   # no newer change in the meantime
            await self.update_model()

    @staticmethod
    def _value(field):
        if field.value is None:
            raise ValueError(f"Enter a value for '{field.props['label']}'.")
        return float(field.value)

    def _parse_positions(self):
        text = (self.positions_input.value or "").replace(";", ",")
        try:
            return [float(v) for v in text.split(",") if v.strip()]
        except ValueError:
            raise ValueError(
                f"Invalid support positions: '{self.positions_input.value}'")

    def _read_inputs(self):
        """Current inputs as plain values for build_and_solve()."""
        v = self._value
        supports = None
        if self.support_radio.value == "free":
            supports = dict(
                positions=self._parse_positions(),
                ends=self.ends_check.value,
                support_length=v(self.support_length_input),
            )
        return dict(
            wall=dict(
                width=v(self.width_input),
                height=v(self.height_input),
                thickness=v(self.thickness_input),
                E=v(self.E_input) * 1e9,
                nu=v(self.nu_input),
                density=v(self.density_input),
                el_size=v(self.el_size_input),
                top_load=v(self.top_load_input) * 1e3,
                horizontal_load=v(self.hor_load_input) * 1e3,
                self_weight=self.self_weight_check.value,
            ),
            openings=[dict(o) for o in self.openings],
            supports=supports,
        )

    def _show_error(self, error):
        self._highlight_opening(getattr(error, "row", None))
        self.status.text = f"Not solved: {error}"
        self.status.classes(add="text-red-700")

    async def update_model(self):
        self._requested += 1     # supersedes pending debounced updates
        self._solve_id += 1
        solve_id = self._solve_id

        self.spinner.set_visibility(True)
        t0 = time.perf_counter()
        try:
            wall = await run.io_bound(build_and_solve, self._read_inputs())
        except Exception as error:   # keep the UI alive on invalid input
            if solve_id == self._solve_id:
                self.spinner.set_visibility(False)
                self._show_error(error)
            return
        if solve_id != self._solve_id:   # a newer solve has been started
            return
        t_solve = time.perf_counter() - t0
        self.spinner.set_visibility(False)

        self.wall = wall
        self.rendered_tab = None
        self._highlight_opening(None)
        self.summary.text = wall.summary_text()

        t0 = time.perf_counter()
        self.render_current()
        t_draw = time.perf_counter() - t0

        self.status.classes(remove="text-red-700")
        self.status.text = (
            f"{wall.n_elements} elements, {2 * wall.n_nodes} dofs  |  "
            f"solve {t_solve * 1e3:.0f} ms, draw {t_draw * 1e3:.0f} ms  |  "
            f"max |u| {wall.max_displacement * 1e3:.3f} mm, "
            f"max σvM {wall.von_mises.max() / 1e6:.2f} MPa"
        )


@ui.page("/")
def index():
    ConcreteWallApp()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Concrete Wall Designer")
