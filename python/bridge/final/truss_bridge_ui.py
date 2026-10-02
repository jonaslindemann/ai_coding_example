# -*- coding: utf-8 -*-
"""
Interactive Qt user interface for the parametric truss bridge in
truss_bridge.py.

Every parameter change rebuilds and re-solves the model and updates the
plots immediately. To keep the interaction responsive the matplotlib
artists are created once and only their data is updated, and rapid
changes (e.g. dragging a slider) are coalesced with a short timer.
"""

import sys

import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QSlider, QSpinBox,
    QVBoxLayout, QWidget,
)

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.colors as mcolors
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure

from truss_bridge import TrussBridge


class SliderSpinBox(QWidget):
    """
    A slider and a spin box kept in sync, emitting ``valueChanged(float)``.

    The slider gives fast, continuous feedback while the spin box allows
    precise input.
    """

    valueChanged = Signal(float)

    STEPS = 1000

    def __init__(self, minimum, maximum, value, decimals=2, suffix=""):
        super().__init__()
        self._min, self._max = minimum, maximum

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self.STEPS)

        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setDecimals(decimals)
        self.spin.setSingleStep(10 ** -decimals if decimals else 1)
        self.spin.setSuffix(suffix)
        self.spin.setKeyboardTracking(False)
        self.spin.setFixedWidth(110)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)

        self.slider.valueChanged.connect(self._on_slider)
        self.spin.valueChanged.connect(self._on_spin)
        self.setValue(value)

    def value(self):
        return self.spin.value()

    def setValue(self, value):
        self.spin.setValue(value)

    def _on_slider(self, pos):
        value = self._min + (self._max - self._min) * pos / self.STEPS
        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)
        self.valueChanged.emit(self.spin.value())

    def _on_spin(self, value):
        pos = round((value - self._min) / (self._max - self._min) * self.STEPS)
        self.slider.blockSignals(True)
        self.slider.setValue(pos)
        self.slider.blockSignals(False)
        self.valueChanged.emit(value)


class BridgeCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas showing the deformed shape and normal forces."""

    def __init__(self):
        # A fixed layout is used instead of constrained layout, which is
        # far too slow to recompute on every interactive update.
        self.figure = Figure(figsize=(9, 7))
        super().__init__(self.figure)

        self.ax_def = self.figure.add_axes([0.05, 0.69, 0.82, 0.27])
        self.ax_force = self.figure.add_axes([0.05, 0.365, 0.82, 0.27])
        self.ax_util = self.figure.add_axes([0.05, 0.04, 0.82, 0.27])
        force_cbar_ax = self.figure.add_axes([0.90, 0.40, 0.015, 0.20])
        util_cbar_ax = self.figure.add_axes([0.90, 0.075, 0.015, 0.20])
        self.cmap = matplotlib.colormaps["coolwarm"]
        self.norm = mcolors.TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0)

        # Deformed shape: undeformed reference + deformed bars + nodes
        self.undeformed = LineCollection([], colors="0.6", linestyles="--", lw=1)
        self.deformed = LineCollection([], cmap=self.cmap, norm=self.norm, lw=2)
        self.ax_def.add_collection(self.undeformed)
        self.ax_def.add_collection(self.deformed)
        self.nodes, = self.ax_def.plot([], [], "ko", ms=3)
        self.supports, = self.ax_def.plot([], [], "k^", ms=10)

        # Normal forces on the undeformed geometry
        self.forces = LineCollection([], cmap=self.cmap, norm=self.norm, lw=4)
        self.ax_force.add_collection(self.forces)
        self.ax_force.set_title("Normal forces (red = tension, blue = compression)")

        self.colorbar = self.figure.colorbar(
            self.forces, cax=force_cbar_ax, label="Normal force (kN)",
        )

        # Utilisation on a fixed 0-100 % scale; overloaded members get a
        # distinct "over" colour so they stand out immediately.
        util_cmap = matplotlib.colormaps["RdYlGn_r"].with_extremes(over="#7b1fa2")
        util_norm = mcolors.Normalize(vmin=0.0, vmax=100.0)
        self.utilisation = LineCollection([], cmap=util_cmap, norm=util_norm, lw=4)
        self.ax_util.add_collection(self.utilisation)
        self.figure.colorbar(
            self.utilisation, cax=util_cbar_ax, extend="max",
            label="Utilisation (%)",
        )

        self.force_labels = []
        self.util_labels = []

        for ax in (self.ax_def, self.ax_force, self.ax_util):
            ax.set_aspect("equal", adjustable="box")
            ax.grid(True, alpha=0.3)

    def update_plot(self, bridge, fy, scale, show_undeformed, show_labels):
        coords = bridge.coords
        conn = np.array([(i, j) for i, j, _ in bridge.elements])
        u = bridge.a.reshape(-1, 2)
        def_coords = coords + scale * u

        N = bridge.normal_forces / 1e3
        nmax = max(np.max(np.abs(N)), 1e-9)
        self.norm.vmin, self.norm.vmax = -nmax, nmax

        segments = coords[conn]
        self.undeformed.set_segments(segments)
        self.undeformed.set_visible(show_undeformed)
        self.deformed.set_segments(def_coords[conn])
        self.deformed.set_array(N)
        self.nodes.set_data(def_coords[:, 0], def_coords[:, 1])
        supports = coords[[bridge.bottom_node(0), bridge.bottom_node(bridge.n_panels)]]
        self.supports.set_data(supports[:, 0], supports[:, 1] - 0.04 * bridge.height)

        self.forces.set_segments(segments)
        self.forces.set_array(N)
        self.colorbar.update_normal(self.forces)

        util = 100.0 * bridge.utilisation(fy)
        self.utilisation.set_segments(segments)
        self.utilisation.set_array(util)
        n_over = np.count_nonzero(util > 100.0)
        self.ax_util.set_title(
            f"Utilisation |σ| / fy (max {util.max():.0f} %, "
            f"{n_over} member{'s' if n_over != 1 else ''} overloaded)"
        )

        mids = segments.mean(axis=1)
        self.force_labels = self._set_labels(
            self.ax_force, self.force_labels, mids,
            [f"{n:.0f}" for n in N] if show_labels else [])
        self.util_labels = self._set_labels(
            self.ax_util, self.util_labels, mids,
            [f"{u:.0f}%" for u in util] if show_labels else [])

        self.ax_def.set_title(
            f"{bridge.truss_type.capitalize()} truss - deformed shape "
            f"(scale {scale:.0f}x, max deflection {bridge.max_deflection * 1e3:.1f} mm)"
        )

        margin_x = 0.05 * bridge.width
        y_min = min(-0.15 * bridge.height, def_coords[:, 1].min() - 0.1 * bridge.height)
        for ax in (self.ax_def, self.ax_force, self.ax_util):
            ax.set_xlim(-margin_x, bridge.width + margin_x)
        self.ax_def.set_ylim(y_min, 1.15 * bridge.height)
        for ax in (self.ax_force, self.ax_util):
            ax.set_ylim(-0.15 * bridge.height, 1.15 * bridge.height)

        self.draw_idle()

    @staticmethod
    def _set_labels(ax, old_labels, positions, texts):
        """Replace the element value labels in ``ax``."""
        for label in old_labels:
            label.remove()
        return [
            ax.text(x, y, text, fontsize=7, ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
            for (x, y), text in zip(positions, texts)
        ]


class TrussBridgeWindow(QMainWindow):
    """Main window: parameter controls on the left, plots on the right."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Truss Bridge Designer")

        # Coalesce rapid parameter changes into a single update
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(10)
        self.update_timer.timeout.connect(self.update_model)

        self.canvas = BridgeCanvas()

        controls = QWidget()
        controls.setFixedWidth(440)
        control_layout = QVBoxLayout(controls)
        control_layout.addWidget(self._create_geometry_group())
        control_layout.addWidget(self._create_material_group())
        control_layout.addWidget(self._create_view_group())
        control_layout.addWidget(self._create_summary_group())
        control_layout.addStretch()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(controls)
        layout.addWidget(self.canvas, 1)
        self.setCentralWidget(central)

        self.update_model()

    # ------------------------------------------------------------------
    # Control groups
    # ------------------------------------------------------------------

    def _create_geometry_group(self):
        group = QGroupBox("Geometry")
        form = QFormLayout(group)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Pratt", "Howe", "Warren"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Truss type", self.type_combo)

        self.width_input = SliderSpinBox(5.0, 200.0, 40.0, 1, " m")
        self.height_input = SliderSpinBox(0.5, 30.0, 5.0, 2, " m")
        form.addRow("Width (span)", self.width_input)
        form.addRow("Height", self.height_input)

        panels = QWidget()
        panels_layout = QHBoxLayout(panels)
        panels_layout.setContentsMargins(0, 0, 0, 0)
        self.panels_slider = QSlider(Qt.Horizontal)
        self.panels_spin = QSpinBox()
        for w in (self.panels_slider, self.panels_spin):
            w.setRange(2, 60)
            w.setSingleStep(2)
        self.panels_spin.setFixedWidth(110)
        self.panels_slider.valueChanged.connect(self.panels_spin.setValue)
        self.panels_spin.valueChanged.connect(self.panels_slider.setValue)
        self.panels_spin.valueChanged.connect(self._on_panels_changed)
        panels_layout.addWidget(self.panels_slider, 1)
        panels_layout.addWidget(self.panels_spin)
        self.panels_spin.setValue(8)
        form.addRow("Panels", panels)

        for w in (self.width_input, self.height_input):
            w.valueChanged.connect(self.schedule_update)
        return group

    def _create_material_group(self):
        group = QGroupBox("Material, sections and load")
        form = QFormLayout(group)

        self.E_input = SliderSpinBox(1.0, 250.0, 210.0, 1, " GPa")
        self.fy_input = SliderSpinBox(100.0, 700.0, 355.0, 0, " MPa")
        self.A_chord_input = SliderSpinBox(1.0, 500.0, 100.0, 1, " cm²")
        self.A_vert_input = SliderSpinBox(1.0, 500.0, 40.0, 1, " cm²")
        self.A_diag_input = SliderSpinBox(1.0, 500.0, 60.0, 1, " cm²")
        self.load_input = SliderSpinBox(0.0, 500.0, 50.0, 1, " kN/m")

        form.addRow("E-modulus", self.E_input)
        form.addRow("Yield strength", self.fy_input)
        form.addRow("A chord", self.A_chord_input)
        form.addRow("A vertical", self.A_vert_input)
        form.addRow("A diagonal", self.A_diag_input)
        form.addRow("Deck load", self.load_input)

        for w in (self.E_input, self.fy_input, self.A_chord_input,
                  self.A_vert_input, self.A_diag_input, self.load_input):
            w.valueChanged.connect(self.schedule_update)
        return group

    def _create_view_group(self):
        group = QGroupBox("View")
        form = QFormLayout(group)

        self.auto_scale_check = QCheckBox("Automatic deformation scale")
        self.auto_scale_check.setChecked(True)
        self.scale_input = SliderSpinBox(1.0, 1000.0, 10.0, 0, "x")
        self.scale_input.setEnabled(False)
        self.auto_scale_check.toggled.connect(
            lambda on: self.scale_input.setEnabled(not on))

        self.undeformed_check = QCheckBox("Show undeformed shape")
        self.undeformed_check.setChecked(True)
        self.labels_check = QCheckBox("Show element values (kN / %)")

        form.addRow(self.auto_scale_check)
        form.addRow("Scale", self.scale_input)
        form.addRow(self.undeformed_check)
        form.addRow(self.labels_check)

        self.auto_scale_check.toggled.connect(self.schedule_update)
        self.scale_input.valueChanged.connect(self.schedule_update)
        self.undeformed_check.toggled.connect(self.schedule_update)
        self.labels_check.toggled.connect(self.schedule_update)
        return group

    def _create_summary_group(self):
        group = QGroupBox("Summary")
        form = QFormLayout(group)
        self.summary_labels = {}
        for key in ("Nodes / elements", "Total load", "Max deflection",
                    "Deflection ratio", "Max tension", "Max compression",
                    "Max stress", "Utilisation", "Overloaded members"):
            label = QLabel("-")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.summary_labels[key] = label
            form.addRow(key, label)
        return group

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _requires_even_panels(self):
        return self.type_combo.currentText().lower() in ("pratt", "howe")

    def _on_type_changed(self):
        step = 2 if self._requires_even_panels() else 1
        self.panels_slider.setSingleStep(step)
        self.panels_spin.setSingleStep(step)
        self._on_panels_changed(self.panels_spin.value())

    def _on_panels_changed(self, value):
        # Pratt and Howe need an even number of panels - round up
        if self._requires_even_panels() and value % 2:
            self.panels_spin.setValue(value + 1)
            return
        self.schedule_update()

    def schedule_update(self, *args):
        self.update_timer.start()

    def update_model(self):
        bridge = TrussBridge(
            width=self.width_input.value(),
            height=self.height_input.value(),
            n_panels=self.panels_spin.value(),
            truss_type=self.type_combo.currentText().lower(),
            E=self.E_input.value() * 1e9,
            A_chord=self.A_chord_input.value() * 1e-4,
            A_vertical=self.A_vert_input.value() * 1e-4,
            A_diagonal=self.A_diag_input.value() * 1e-4,
            deck_load=self.load_input.value() * 1e3,
        )
        bridge.solve()

        if self.auto_scale_check.isChecked():
            scale = 0.1 * bridge.height / max(bridge.max_deflection, 1e-12)
            scale = min(scale, 1e6)
            self.scale_input.blockSignals(True)
            self.scale_input.setValue(min(scale, 1000.0))
            self.scale_input.blockSignals(False)
        else:
            scale = self.scale_input.value()

        self.canvas.update_plot(
            bridge, self.fy_input.value() * 1e6, scale,
            self.undeformed_check.isChecked(),
            self.labels_check.isChecked(),
        )
        self._update_summary(bridge)

    def _update_summary(self, bridge):
        stresses = bridge.stresses() / 1e6
        N = bridge.normal_forces / 1e3
        max_stress = np.max(np.abs(stresses))
        element_util = bridge.utilisation(self.fy_input.value() * 1e6)
        utilisation = element_util.max()
        n_over = np.count_nonzero(element_util > 1.0)
        delta = bridge.max_deflection
        ratio = f"L / {bridge.width / delta:.0f}" if delta > 0 else "-"

        s = self.summary_labels
        s["Nodes / elements"].setText(f"{bridge.n_nodes} / {len(bridge.elements)}")
        s["Total load"].setText(f"{bridge.deck_load * bridge.width / 1e3:.1f} kN")
        s["Max deflection"].setText(f"{delta * 1e3:.2f} mm")
        s["Deflection ratio"].setText(ratio)
        s["Max tension"].setText(f"{max(N.max(), 0):.1f} kN")
        s["Max compression"].setText(f"{min(N.min(), 0):.1f} kN")
        s["Max stress"].setText(f"{max_stress:.1f} MPa")
        s["Utilisation"].setText(f"{utilisation * 100:.0f} %")
        color = "#c62828" if utilisation > 1.0 else "#2e7d32"
        s["Utilisation"].setStyleSheet(f"color: {color}; font-weight: bold;")
        s["Overloaded members"].setText(f"{n_over} of {len(bridge.elements)}")
        s["Overloaded members"].setStyleSheet(f"color: {color};")


def main():
    app = QApplication(sys.argv)
    window = TrussBridgeWindow()
    window.resize(1400, 850)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
