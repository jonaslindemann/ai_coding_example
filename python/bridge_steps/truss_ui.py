"""
Interactive Qt (qtpy) explorer for the 2D truss bridge model.

Lets the user pick the truss type, change the geometry, material and load,
and see the deformed shape with members coloured by normal force. The plot
updates live as the parameters change.

The model module (truss_model.py) is used only through its public API:
TrussBridge(...), solve(), and the documented public attributes (a, r, N,
coords, elements, member_groups, support_nodes, loaded_nodes).

Units follow the spec: N, m and Pa throughout, with no unit conversion.

Run:
    python truss_ui.py
"""

import sys

import numpy as np

# Import qtpy before matplotlib's Qt backend, so both use the same binding
from qtpy.QtCore import QLocale, Qt, QTimer, Signal
from qtpy.QtGui import QDoubleValidator, QFont
from qtpy.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QSlider, QSpinBox, QVBoxLayout,
    QWidget,
)

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from matplotlib.patches import Circle

from truss_model import TrussBridge, TRUSS_TYPES

# Initial values in the UI: the Pratt benchmark given by the problem owner
# (L = 20 m, h = 3 m, n = 4, P = 10 kN, E = 210 GPa, A = 0.01 m²), in SI.
INITIAL = dict(truss_type="pratt", L=20.0, h=3.0, n=4, P=10e3, E=210e9, A=0.01)

# With auto-scaling, the largest displacement is drawn as this fraction of L.
# This is display-only and does not affect the analysis.
AUTO_SCALE_TARGET = 0.08

# Diverging colour map: blue = compression (N < 0), red = tension (N > 0)
CMAP = matplotlib.colormaps["RdBu_r"]

# Hover distance in pixels for picking a member under the mouse
PICK_PX = 8


# ----------------------------------------------------------------------
# Input widgets
# ----------------------------------------------------------------------

class FloatControl(QWidget):
    """Linked slider and spin box for a float value. Dragging the slider gives
    live updates, and the spin box allows exact input."""

    valueChanged = Signal(float)
    _STEPS = 1000

    def __init__(self, lo, hi, step, decimals, value, suffix=""):
        super().__init__()
        self._lo, self._hi = lo, hi

        self.spin = QDoubleSpinBox()
        self.spin.setRange(lo, hi)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(decimals)
        self.spin.setSuffix(suffix)
        self.spin.setLocale(QLocale.c())  # always '.' as decimal separator
        self.spin.setValue(value)
        self.spin.setMinimumWidth(95)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self._STEPS)
        self.slider.setValue(self._to_pos(value))

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.slider, 1)
        lay.addWidget(self.spin)

        self.spin.valueChanged.connect(self._from_spin)
        self.slider.valueChanged.connect(self._from_slider)

    def _to_pos(self, v):
        return round((v - self._lo) / (self._hi - self._lo) * self._STEPS)

    def _from_spin(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(self._to_pos(v))
        self.slider.blockSignals(False)
        self.valueChanged.emit(v)

    def _from_slider(self, pos):
        v = self._lo + (self._hi - self._lo) * pos / self._STEPS
        self.spin.setValue(v)  # emits valueChanged through _from_spin

    def value(self):
        return self.spin.value()


class PanelControl(QWidget):
    """Linked slider and spin box for the number of panels. The slider moves
    in even steps only. A value typed into the spin box is passed to the model
    as is, so the model's own validation reports odd n."""

    valueChanged = Signal(int)

    def __init__(self, lo, hi, value):
        super().__init__()
        self.spin = QSpinBox()
        self.spin.setRange(lo, hi)
        self.spin.setSingleStep(2)
        self.spin.setValue(value)
        self.spin.setMinimumWidth(95)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(lo // 2, hi // 2)  # slider position k means n = 2k
        self.slider.setValue(value // 2)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.slider, 1)
        lay.addWidget(self.spin)

        self.spin.valueChanged.connect(self._from_spin)
        self.slider.valueChanged.connect(lambda k: self.spin.setValue(2 * k))

    def _from_spin(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(v // 2)
        self.slider.blockSignals(False)
        self.valueChanged.emit(v)

    def value(self):
        return self.spin.value()


class SciEdit(QLineEdit):
    """Line edit for a float in scientific notation (for example 2.1e11).
    Emits valueChanged only for complete, valid numbers. Range checks are left
    to the model."""

    valueChanged = Signal(float)

    def __init__(self, value):
        super().__init__(f"{value:g}")
        v = QDoubleValidator()
        v.setNotation(QDoubleValidator.ScientificNotation)
        v.setLocale(QLocale.c())
        self.setValidator(v)
        self.textChanged.connect(self._changed)

    def _changed(self, text):
        try:
            self.valueChanged.emit(float(text))
        except ValueError:
            pass  # incomplete input such as "2e", wait for more typing

    def value(self):
        try:
            return float(self.text())
        except ValueError:
            return float("nan")  # the model rejects NaN with a clear message


# ----------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------

class TrussWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Truss Bridge Explorer")
        self.resize(1300, 720)

        self.truss = None       # last solved TrussBridge
        self.scale = 1.0        # deformation scale currently drawn
        self._segments = None   # deformed member segments (m, 2, 2) for hover
        self._hover = None      # hover annotation artist

        # Debounce: many valueChanged signals in a row (slider drag) cause a
        # single recompute once the event loop is idle.
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(15)
        self._timer.timeout.connect(self.recompute)

        self._build_controls()
        self._build_plot()

        central = QWidget()
        lay = QHBoxLayout(central)
        lay.addWidget(self.controls, 0)
        lay.addWidget(self.plot_panel, 1)
        self.setCentralWidget(central)

        self.recompute()

    # --- UI construction ---------------------------------------------

    def _build_controls(self):
        self.controls = QWidget()
        self.controls.setFixedWidth(380)
        col = QVBoxLayout(self.controls)

        # Truss type
        g_type = QGroupBox("Truss type")
        f = QFormLayout(g_type)
        self.cb_type = QComboBox()
        for t in TRUSS_TYPES:
            self.cb_type.addItem(t.capitalize(), t)
        self.cb_type.setCurrentIndex(TRUSS_TYPES.index(INITIAL["truss_type"]))
        f.addRow("Type", self.cb_type)
        col.addWidget(g_type)

        # Geometry (slider ranges are UI limits only, not model limits)
        g_geo = QGroupBox("Geometry")
        f = QFormLayout(g_geo)
        self.in_L = FloatControl(1.0, 200.0, 0.5, 2, INITIAL["L"], " m")
        self.in_h = FloatControl(0.1, 30.0, 0.1, 2, INITIAL["h"], " m")
        self.in_n = PanelControl(2, 40, INITIAL["n"])
        f.addRow("Span L", self.in_L)
        f.addRow("Height h", self.in_h)
        f.addRow("Panels n", self.in_n)
        col.addWidget(g_geo)

        # Material and load (SI, as in the spec)
        g_mat = QGroupBox("Material and load (SI)")
        f = QFormLayout(g_mat)
        self.in_E = SciEdit(INITIAL["E"])
        self.in_A = SciEdit(INITIAL["A"])
        self.in_P = FloatControl(-1e5, 1e5, 500.0, 1, INITIAL["P"], " N")
        f.addRow("E [Pa]", self.in_E)
        f.addRow("A [m²]", self.in_A)
        f.addRow("P (+ down)", self.in_P)
        col.addWidget(g_mat)

        # Display options
        g_disp = QGroupBox("Display")
        f = QFormLayout(g_disp)
        self.chk_auto = QCheckBox(f"Auto scale (max displacement = {AUTO_SCALE_TARGET:g}·L)")
        self.chk_auto.setChecked(True)
        self.in_scale = SciEdit(1.0)
        self.in_scale.setEnabled(False)
        self.chk_undeformed = QCheckBox("Show undeformed shape")
        self.chk_undeformed.setChecked(True)
        self.chk_labels = QCheckBox("Show member forces")
        self.chk_labels.setChecked(False)
        f.addRow(self.chk_auto)
        f.addRow("Scale factor", self.in_scale)
        f.addRow(self.chk_undeformed)
        f.addRow(self.chk_labels)
        self.lbl_scale = QLabel()
        self.lbl_scale.setStyleSheet("font-weight: bold;")
        f.addRow("Deformation scale", self.lbl_scale)
        col.addWidget(g_disp)

        # Results
        g_res = QGroupBox("Results")
        v = QVBoxLayout(g_res)
        self.lbl_results = QLabel()
        self.lbl_results.setFont(QFont("Consolas", 9))
        self.lbl_results.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_results.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        v.addWidget(self.lbl_results)
        col.addWidget(g_res, 1)

        # Live updates: every change schedules a (debounced) recompute
        self.cb_type.currentIndexChanged.connect(self.schedule)
        for w in (self.in_L, self.in_h, self.in_n, self.in_E, self.in_A, self.in_P,
                  self.in_scale):
            w.valueChanged.connect(self.schedule)
        for c in (self.chk_undeformed, self.chk_labels):
            c.toggled.connect(self.schedule)
        self.chk_auto.toggled.connect(self._auto_toggled)

    def _build_plot(self):
        self.plot_panel = QWidget()
        v = QVBoxLayout(self.plot_panel)
        # Fixed layout: a layout engine recomputed every frame is the main cost
        # of a redraw, so the axes positions are set once here.
        self.fig = Figure()
        self.canvas = FigureCanvasQTAgg(self.fig)
        v.addWidget(NavigationToolbar2QT(self.canvas, self.plot_panel))
        v.addWidget(self.canvas, 1)

        self.ax = self.fig.add_axes([0.07, 0.10, 0.80, 0.82])
        self.cax = self.fig.add_axes([0.90, 0.10, 0.018, 0.82])

        # Colorbar created once; each redraw only updates its norm
        from matplotlib.cm import ScalarMappable
        self._sm = ScalarMappable(norm=Normalize(-1, 1), cmap=CMAP)
        self.cbar = self.fig.colorbar(self._sm, cax=self.cax)
        self.cbar.set_label("Normal force N [N]   (− compression | + tension)")

        self.canvas.mpl_connect("motion_notify_event", self._on_hover)

        self.statusBar().showMessage("Ready")

    # --- Behaviour ---------------------------------------------------

    def _auto_toggled(self, checked):
        self.in_scale.setEnabled(not checked)
        if not checked:
            # Start manual mode from the scale currently shown
            self.in_scale.setText(f"{self.scale:.4g}")
        self.schedule()

    def schedule(self, *_):
        self._timer.start()

    def recompute(self):
        """Build and solve the model from the current inputs, then redraw."""
        try:
            truss = TrussBridge(self.cb_type.currentData(), self.in_L.value(),
                                self.in_h.value(), self.in_n.value())
            truss.solve(self.in_E.value(), self.in_A.value(), self.in_P.value())
        except (ValueError, TypeError, np.linalg.LinAlgError) as exc:
            # Keep the last valid picture and report the problem
            self.statusBar().setStyleSheet("color: #b00020;")
            self.statusBar().showMessage(f"Input error: {exc}")
            return

        self.truss = truss
        self.statusBar().setStyleSheet("")
        self.statusBar().showMessage(
            f"Solved: {truss.n_nodes} nodes, {truss.n_elements} members, "
            f"{truss.n_dofs} DOFs")
        self._update_scale()
        self._draw()
        self._update_results()

    def _update_scale(self):
        u = self.truss.a.reshape(-1, 2)
        umax = np.max(np.linalg.norm(u, axis=1))
        if self.chk_auto.isChecked():
            self.scale = AUTO_SCALE_TARGET * self.truss.L / umax if umax > 0 else 1.0
        else:
            s = self.in_scale.value()
            self.scale = s if np.isfinite(s) else 1.0
        self.lbl_scale.setText(f"× {self.scale:.4g}")

    # --- Drawing -----------------------------------------------------

    def _draw(self):
        t = self.truss
        ax = self.ax
        ax.clear()

        xy0 = t.coords
        xy = t.coords + self.scale * t.a.reshape(-1, 2)  # deformed node positions
        el = t.elements - 1                              # 0-based end nodes
        seg0 = np.stack([xy0[el[:, 0]], xy0[el[:, 1]]], axis=1)
        seg = np.stack([xy[el[:, 0]], xy[el[:, 1]]], axis=1)
        self._segments = seg

        # Colour scale symmetric about zero so white means N = 0
        nmax = float(np.max(np.abs(t.N)))
        if nmax < 1e-9 * max(abs(t.P), 1.0):
            nmax = 1.0  # all forces are zero (P = 0): any symmetric range works
        norm = Normalize(vmin=-nmax, vmax=nmax)

        if self.chk_undeformed.isChecked():
            ax.add_collection(LineCollection(seg0, colors="0.65", linewidths=1.0,
                                             linestyles="--", zorder=1))

        # Grey outline under each member so near-zero (white) members stay visible
        ax.add_collection(LineCollection(seg, colors="0.35", linewidths=5.0, zorder=2))
        lc = LineCollection(seg, cmap=CMAP, norm=norm, linewidths=3.5, zorder=3,
                            capstyle="round")
        lc.set_array(t.N)
        ax.add_collection(lc)
        ax.plot(xy[:, 0], xy[:, 1], "o", color="black", ms=3.5, zorder=4)

        # Supports at their (fixed) undeformed positions
        span = t.L
        s = 0.018 * span
        pin, roller = t.support_nodes
        xp, yp = xy0[pin - 1]
        xr, yr = xy0[roller - 1]
        ax.fill([xp, xp - s, xp + s], [yp, yp - 1.6 * s, yp - 1.6 * s],
                color="0.3", zorder=5)
        ax.add_patch(Circle((xr, yr - 0.8 * s), 0.8 * s, color="0.3", zorder=5))

        # Load arrows at the deformed loaded nodes, pointing in the load direction
        arrow = 0.08 * span * (1 if t.P >= 0 else -1)
        if t.P != 0:
            for node in t.loaded_nodes:
                x, y = xy[node - 1]
                ax.annotate("", xy=(x, y), xytext=(x, y + arrow),
                            arrowprops=dict(arrowstyle="-|>", color="#6a1b9a", lw=1.3),
                            zorder=6)

        # Optional force labels at member midpoints
        if self.chk_labels.isChecked():
            mid = seg.mean(axis=1)
            for (x, y), N in zip(mid, t.N):
                ax.text(x, y, f"{N:.4g}", fontsize=7, ha="center", va="center",
                        zorder=7, bbox=dict(boxstyle="round,pad=0.15", fc="white",
                                            ec="none", alpha=0.85))

        # Limits that include the deformed shape, supports and arrows
        pts = np.vstack([xy0, xy])
        xmin, ymin = pts.min(axis=0)
        xmax, ymax = pts.max(axis=0)
        ymin = min(ymin, -1.8 * s, -abs(arrow) if t.P < 0 else ymin)
        ymax = max(ymax, t.h + abs(arrow) if t.P > 0 else ymax)
        pad = 0.05 * max(xmax - xmin, ymax - ymin)
        ax.set_xlim(xmin - pad, xmax + pad)
        ax.set_ylim(ymin - pad, ymax + pad)
        # True proportions: shrink the axes box rather than override the limits
        ax.set_aspect("equal", adjustable="box", anchor="C")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.grid(True, lw=0.3, alpha=0.5)
        ax.set_title(f"{t.truss_type.capitalize()} truss: L = {t.L:g} m, "
                     f"h = {t.h:g} m, n = {t.n}, P = {t.P:g} N")

        # Scale factor shown on the plot itself
        ax.text(0.01, 0.98, f"Deformation scale × {self.scale:.4g}",
                transform=ax.transAxes, ha="left", va="top", fontsize=10,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.6"))

        self._sm.set_norm(norm)
        self.cbar.update_normal(self._sm)

        # Hover annotation, hidden until the mouse is over a member
        self._hover = ax.annotate(
            "", xy=(0, 0), xytext=(12, 12), textcoords="offset points", fontsize=8,
            bbox=dict(boxstyle="round", fc="lightyellow", ec="0.5"), zorder=10)
        self._hover.set_visible(False)

        self.canvas.draw_idle()

    def _update_results(self):
        t = self.truss
        a = t.a.reshape(-1, 2)
        r = t.r.reshape(-1, 2)
        pin, roller = t.support_nodes
        i_t = int(np.argmax(t.N))
        i_c = int(np.argmin(t.N))
        i_u = int(np.argmax(np.abs(a[:, 1])))
        lines = [
            "Reactions [N]",
            f"  pin    (node {pin}):  Rx = {r[pin - 1, 0]: .5g}",
            f"                     Ry = {r[pin - 1, 1]: .5g}",
            f"  roller (node {roller}):  Ry = {r[roller - 1, 1]: .5g}",
            f"  sum Ry = {r[pin - 1, 1] + r[roller - 1, 1]: .5g}"
            f"   (loads {(t.n - 1) * t.P:.5g})",
            "",
            "Normal forces [N]",
            f"  max tension     {t.N[i_t]: .5g}  (member {i_t + 1}, {t.member_groups[i_t]})",
            f"  max compression {t.N[i_c]: .5g}  (member {i_c + 1}, {t.member_groups[i_c]})",
            "",
            "Displacements [m]",
            f"  max |uy| at node {i_u + 1}: uy = {a[i_u, 1]: .5g}",
            f"  max |u| {np.max(np.linalg.norm(a, axis=1)): .5g}",
            "",
            "Hover over a member for its force.",
        ]
        self.lbl_results.setText("\n".join(lines))

    def _on_hover(self, event):
        """Show the force of the member under the mouse cursor."""
        if self._segments is None or self._hover is None:
            return
        if event.inaxes is not self.ax:
            if self._hover.get_visible():
                self._hover.set_visible(False)
                self.canvas.draw_idle()
            return

        # Point-to-segment distance in pixels, so picking feels the same at any zoom
        p = np.array([event.x, event.y])
        seg = self.ax.transData.transform(self._segments.reshape(-1, 2)).reshape(-1, 2, 2)
        a, b = seg[:, 0], seg[:, 1]
        ab = b - a
        tt = np.clip(np.einsum("ij,ij->i", p - a, ab) / np.maximum(
            np.einsum("ij,ij->i", ab, ab), 1e-12), 0, 1)
        dist = np.linalg.norm(a + tt[:, None] * ab - p, axis=1)
        i = int(np.argmin(dist))

        if dist[i] <= PICK_PX:
            t = self.truss
            N = t.N[i]
            kind = "tension" if N > 0 else "compression" if N < 0 else "zero force"
            n1, n2 = t.elements[i]
            self._hover.xy = (event.xdata, event.ydata)
            self._hover.set_text(f"Member {i + 1} ({t.member_groups[i]}), "
                                 f"nodes {n1}–{n2}\nN = {N:.5g} N ({kind})")
            self._hover.set_visible(True)
            self.canvas.draw_idle()
        elif self._hover.get_visible():
            self._hover.set_visible(False)
            self.canvas.draw_idle()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    win = TrussWindow()
    win.show()
    return app.exec_() if hasattr(app, "exec_") else app.exec()


if __name__ == "__main__":
    sys.exit(main())
