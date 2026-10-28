"""
Qt user interface for the parametric truss bridge in truss_bridge.py.

Every parameter change regenerates and re-solves the model and updates
the plots. To keep the interaction responsive:

- the matplotlib artists are created once and only their data is updated,
- rapid changes (e.g. dragging a slider) are coalesced with a short timer
  so that at most one solve is performed per redraw.
"""

import sys

import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QPlainTextEdit, QSlider,
    QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.patches import Polygon

from truss_bridge import TrussBridge


class SliderSpin(QWidget):
    """A slider and a spin box kept in sync, emitting float values."""

    valueChanged = Signal(float)

    def __init__(self, minimum, maximum, value, step, decimals=2, suffix=""):
        super().__init__()
        self._step = step

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(round(minimum / step), round(maximum / step))
        self.slider.setValue(round(value / step))

        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setDecimals(decimals)
        self.spin.setSingleStep(step)
        self.spin.setSuffix(suffix)
        self.spin.setValue(value)
        self.spin.setKeyboardTracking(False)
        self.spin.setMinimumWidth(110)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)

        self.slider.valueChanged.connect(self._on_slider)
        self.spin.valueChanged.connect(self._on_spin)

    def value(self):
        return self.spin.value()

    def _on_slider(self, ivalue):
        value = ivalue * self._step
        if abs(value - self.spin.value()) > 1e-12:
            self.spin.blockSignals(True)
            self.spin.setValue(value)
            self.spin.blockSignals(False)
            self.valueChanged.emit(self.spin.value())

    def _on_spin(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(round(value / self._step))
        self.slider.blockSignals(False)
        self.valueChanged.emit(value)


class BridgeCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas showing forces/deformation and utilisation."""

    def __init__(self):
        self.fig = Figure(figsize=(10, 7), layout="constrained")
        super().__init__(self.fig)

        gs = self.fig.add_gridspec(2, 1, height_ratios=[1.4, 1])
        self.ax_truss = self.fig.add_subplot(gs[0])
        self.ax_util = self.fig.add_subplot(gs[1])

        # Truss axes: undeformed (dashed) and deformed coloured by N
        self.lc_undeformed = LineCollection([], colors="0.7", linewidths=1.0,
                                            linestyles="--")
        self.lc_forces = LineCollection([], cmap="coolwarm_r", linewidths=4)
        self.lc_forces.set_clim(-1, 1)
        self.ax_truss.add_collection(self.lc_undeformed)
        self.ax_truss.add_collection(self.lc_forces)
        (self.nodes_plot,) = self.ax_truss.plot([], [], "o", color="k", ms=3)
        self.support_left = Polygon(np.zeros((3, 2)), closed=True, fc="0.6", ec="k")
        self.support_right = Polygon(np.zeros((3, 2)), closed=True, fc="white", ec="k")
        self.ax_truss.add_patch(self.support_left)
        self.ax_truss.add_patch(self.support_right)
        self.ax_truss.set_aspect("equal")
        self.ax_truss.set_xlabel("x [m]")
        self.ax_truss.set_ylabel("y [m]")
        self.colorbar = self.fig.colorbar(self.lc_forces, ax=self.ax_truss,
                                          location="bottom", shrink=0.6, aspect=40,
                                          label="Normal force [kN] (+ tension)")

        # Utilisation axes
        self.bars = None
        self._needs_layout = True
        self.ax_util.axhline(100, color="k", ls="--", lw=1)
        self.ax_util.set_xlabel("Element")
        self.ax_util.set_ylabel("Utilisation [%]")
        self.ax_util.set_title("Member utilisation |σ| / fy")

    def update_plot(self, bridge, scale):
        coords = bridge.coords
        disp = bridge.displacements
        deformed = coords + scale * disp
        elements = bridge.elements

        # --- Truss: forces on deformed shape ---
        Nk = bridge.N / 1e3
        nmax = max(np.abs(Nk).max(), 1e-9)
        self.lc_undeformed.set_segments(coords[elements])
        self.lc_forces.set_segments(deformed[elements])
        self.lc_forces.set_array(Nk)
        self.lc_forces.set_clim(-nmax, nmax)
        self.nodes_plot.set_data(deformed[:, 0], deformed[:, 1])

        s = 0.04 * bridge.width
        for patch, node in ((self.support_left, bridge.bottom_nodes[0]),
                            (self.support_right, bridge.bottom_nodes[-1])):
            x, y = coords[node]
            patch.set_xy([[x, y], [x - s / 2, y - s], [x + s / 2, y - s]])

        margin = 0.06 * bridge.width
        ymin = min(deformed[:, 1].min(), 0.0) - 1.5 * s
        ymax = max(deformed[:, 1].max(), bridge.height) + margin
        self.ax_truss.set_xlim(-margin, bridge.width + margin)
        self.ax_truss.set_ylim(ymin, ymax)
        self.ax_truss.set_title(f"{bridge.truss_type.capitalize()} truss - "
                                f"normal forces on deformed shape (scale {scale:.3g}x)")

        # --- Utilisation bars ---
        util = bridge.utilisation * 100
        colors = ["tab:red" if u > 100 else "tab:orange" if u > 80 else "tab:green"
                  for u in util]
        if self.bars is None or len(self.bars) != len(util):
            if self.bars is not None:
                self.bars.remove()
            self.bars = self.ax_util.bar(np.arange(len(util)), util, color=colors)
            self.ax_util.set_xlim(-0.75, len(util) - 0.25)
            self._needs_layout = True
        else:
            for bar, u, c in zip(self.bars, util, colors):
                bar.set_height(u)
                bar.set_color(c)
        self.ax_util.set_ylim(0, max(110, util.max() * 1.1))

        if self._needs_layout:
            self._apply_layout()
        self.draw_idle()

    def _apply_layout(self):
        # Constrained layout is expensive (~100 ms), so it is computed only
        # when needed (first draw, resize, changed tick labels) instead of
        # on every redraw.
        self.fig.set_layout_engine("constrained")
        self.fig.get_layout_engine().execute(self.fig)
        self.fig.set_layout_engine("none")
        self._needs_layout = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_layout()


class TrussBridgeWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Truss Bridge Designer - CALFEM")
        self.resize(1400, 850)

        self.bridge = TrussBridge()

        # Coalesce rapid parameter changes into a single update
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(15)
        self.update_timer.timeout.connect(self.update_model)

        self._build_ui()
        self.update_model()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        b = self.bridge

        # Geometry
        self.type_combo = QComboBox()
        self.type_combo.addItems([t.capitalize() for t in TrussBridge.TRUSS_TYPES])
        self.width_ctrl = SliderSpin(5.0, 120.0, b.width, 0.5, 1, " m")
        self.height_ctrl = SliderSpin(0.5, 20.0, b.height, 0.1, 1, " m")
        self.panels_spin = QSpinBox()
        self.panels_spin.setRange(2, 40)
        self.panels_spin.setValue(b.n_panels)
        self.panels_note = QLabel("")
        self.panels_note.setStyleSheet("color: gray; font-size: 11px;")

        geo_box = QGroupBox("Geometry")
        geo = QFormLayout(geo_box)
        geo.addRow("Truss type", self.type_combo)
        geo.addRow("Width (span)", self.width_ctrl)
        geo.addRow("Height", self.height_ctrl)
        geo.addRow("Panels", self.panels_spin)
        geo.addRow("", self.panels_note)

        # Material and sections
        self.E_ctrl = SliderSpin(10.0, 300.0, b.E / 1e9, 1.0, 0, " GPa")
        self.fy_ctrl = SliderSpin(100.0, 700.0, b.fy / 1e6, 5.0, 0, " MPa")
        self.A_chord_ctrl = SliderSpin(5.0, 500.0, b.A_chord * 1e4, 1.0, 0, " cm²")
        self.A_web_ctrl = SliderSpin(5.0, 500.0, b.A_web * 1e4, 1.0, 0, " cm²")

        mat_box = QGroupBox("Material and sections")
        mat = QFormLayout(mat_box)
        mat.addRow("E-modulus", self.E_ctrl)
        mat.addRow("Yield strength", self.fy_ctrl)
        mat.addRow("Chord area", self.A_chord_ctrl)
        mat.addRow("Web area", self.A_web_ctrl)

        # Loads
        self.load_ctrl = SliderSpin(0.0, 300.0, b.deck_load / 1e3, 1.0, 0, " kN/m")
        self.point_ctrl = SliderSpin(0.0, 2000.0, 0.0, 10.0, 0, " kN")
        self.point_pos_ctrl = SliderSpin(0.0, 1.0, 0.5, 0.01, 2, "")

        load_box = QGroupBox("Loads")
        load = QFormLayout(load_box)
        load.addRow("Deck load", self.load_ctrl)
        load.addRow("Point load", self.point_ctrl)
        load.addRow("Point load pos. (x/L)", self.point_pos_ctrl)

        # Display
        self.auto_scale_check = QCheckBox("Automatic deformation scale")
        self.auto_scale_check.setChecked(True)
        self.scale_ctrl = SliderSpin(1.0, 500.0, 20.0, 1.0, 0, "x")
        self.scale_ctrl.setEnabled(False)

        disp_box = QGroupBox("Display")
        disp = QFormLayout(disp_box)
        disp.addRow(self.auto_scale_check)
        disp.addRow("Scale", self.scale_ctrl)

        # Summary
        self.summary_text = QPlainTextEdit()
        self.summary_text.setReadOnly(True)
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(9)
        self.summary_text.setFont(font)
        sum_box = QGroupBox("Summary")
        sum_layout = QVBoxLayout(sum_box)
        sum_layout.addWidget(self.summary_text)

        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        for box in (geo_box, mat_box, load_box, disp_box):
            panel_layout.addWidget(box)
        panel_layout.addWidget(sum_box, 1)
        panel.setMinimumWidth(380)

        self.canvas = BridgeCanvas()

        splitter = QSplitter()
        splitter.addWidget(panel)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([420, 980])
        self.setCentralWidget(splitter)

        # Signals
        for ctrl in (self.width_ctrl, self.height_ctrl, self.E_ctrl, self.fy_ctrl,
                     self.A_chord_ctrl, self.A_web_ctrl, self.load_ctrl,
                     self.point_ctrl, self.point_pos_ctrl, self.scale_ctrl):
            ctrl.valueChanged.connect(self.schedule_update)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.panels_spin.valueChanged.connect(self.schedule_update)
        self.auto_scale_check.toggled.connect(self._on_auto_scale)
        self._on_type_changed()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_type_changed(self):
        # Pratt and Howe trusses require an even number of panels
        needs_even = self.type_combo.currentText().lower() in ("pratt", "howe")
        self.panels_spin.setSingleStep(2 if needs_even else 1)
        self.panels_spin.setMinimum(2 if needs_even else 1)
        if needs_even and self.panels_spin.value() % 2:
            self.panels_spin.setValue(self.panels_spin.value() + 1)
        self.panels_note.setText("Even number of panels required" if needs_even else "")
        self.schedule_update()

    def _on_auto_scale(self, checked):
        self.scale_ctrl.setEnabled(not checked)
        self.schedule_update()

    def schedule_update(self, *args):
        self.update_timer.start()

    # ------------------------------------------------------------------
    # Model update
    # ------------------------------------------------------------------

    def update_model(self):
        b = self.bridge
        b.truss_type = self.type_combo.currentText().lower()
        b.width = self.width_ctrl.value()
        b.height = self.height_ctrl.value()
        n = self.panels_spin.value()
        if b.truss_type in ("pratt", "howe") and n % 2:
            n += 1
        b.n_panels = n
        b.E = self.E_ctrl.value() * 1e9
        b.fy = self.fy_ctrl.value() * 1e6
        b.A_chord = self.A_chord_ctrl.value() * 1e-4
        b.A_web = self.A_web_ctrl.value() * 1e-4
        b.deck_load = self.load_ctrl.value() * 1e3

        try:
            b.point_loads = []
            b.generate()
            P = self.point_ctrl.value() * 1e3
            if P > 0:
                # Apply point load at the bottom chord node closest to x/L
                idx = round(self.point_pos_ctrl.value() * b.n_panels)
                b.add_point_load(b.bottom_nodes[idx], Fy=-P)
            b.solve()
        except Exception as exc:
            self.summary_text.setPlainText(f"Error: {exc}")
            return

        if self.auto_scale_check.isChecked():
            scale = 0.1 * b.height / max(b.max_deflection, 1e-12)
            self.scale_ctrl.blockSignals(True)
            self.scale_ctrl.spin.blockSignals(True)
            self.scale_ctrl.spin.setValue(min(scale, self.scale_ctrl.spin.maximum()))
            self.scale_ctrl.slider.blockSignals(True)
            self.scale_ctrl.slider.setValue(round(self.scale_ctrl.spin.value()))
            self.scale_ctrl.slider.blockSignals(False)
            self.scale_ctrl.spin.blockSignals(False)
            self.scale_ctrl.blockSignals(False)
        else:
            scale = self.scale_ctrl.value()

        self.canvas.update_plot(b, scale)
        self.summary_text.setPlainText(self._summary(b))

    def _summary(self, b):
        util = b.utilisation
        n_over = int(np.sum(util > 1.0))
        status = "OK" if n_over == 0 else f"{n_over} member(s) exceed yield!"
        return (b.summary()
                + f"\n  Max stress (abs)     : {np.abs(b.stresses).max() / 1e6:.1f} MPa"
                + f"\n  Status               : {status}")


def main():
    app = QApplication(sys.argv)
    window = TrussBridgeWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
