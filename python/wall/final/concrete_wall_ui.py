# -*- coding: utf-8 -*-
"""
Interactive Qt (qtpy) user interface for the parametric concrete wall in
concrete_wall.py.

The input parameters are grouped in tabs on the left (geometry, openings,
material, loads & supports) and the results are shown in tabs on the right.

To keep the interaction responsive:
    - rapid parameter changes are coalesced with a short timer before the
      model is rebuilt and solved,
    - only the visible result tab is redrawn; the other tabs are redrawn
      lazily when they are selected.
"""

import sys
import time

from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox,
    QDoubleSpinBox, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QPushButton, QRadioButton,
    QSplitter, QTableWidget, QTabWidget, QVBoxLayout, QWidget,
)

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg, NavigationToolbar2QT,
)
from matplotlib.figure import Figure

from concrete_wall import ConcreteWall


def spin_box(minimum, maximum, value, decimals=2, step=0.1, suffix=""):
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setSingleStep(step)
    spin.setValue(value)
    spin.setSuffix(suffix)
    spin.setKeyboardTracking(False)
    return spin


class PlotTab(QWidget):
    """A matplotlib canvas with toolbar, drawn by a callback ``draw(wall, ax)``."""

    def __init__(self, draw):
        super().__init__()
        self.draw = draw
        self.dirty = True

        self.figure = Figure(figsize=(8, 5), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))
        layout.addWidget(self.canvas, 1)

    def redraw(self, wall):
        self.figure.clear()
        self.draw(wall, self.figure.add_subplot(111))
        self.canvas.draw_idle()
        self.dirty = False


class OpeningsTable(QWidget):
    """Editable table of windows and doors."""

    COLUMNS = ["Type", "x (m)", "y (m)", "Width (m)", "Height (m)"]

    def __init__(self, on_change):
        super().__init__()
        self.on_change = on_change

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        add_window = QPushButton("Add window")
        add_door = QPushButton("Add door")
        remove = QPushButton("Remove selected")
        add_window.clicked.connect(lambda: self.add_row("window", 0.5, 0.9, 1.0, 1.2))
        add_door.clicked.connect(lambda: self.add_row("door", 0.5, 0.0, 1.0, 2.1))
        remove.clicked.connect(self.remove_selected)

        buttons = QHBoxLayout()
        buttons.addWidget(add_window)
        buttons.addWidget(add_door)
        buttons.addWidget(remove)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        layout.addWidget(QLabel(
            "x, y is the lower-left corner. Doors always start at y = 0."))

    def add_row(self, kind, x, y, w, h, notify=True):
        row = self.table.rowCount()
        self.table.insertRow(row)

        combo = QComboBox()
        combo.addItems(["window", "door"])
        combo.setCurrentText(kind)
        combo.currentTextChanged.connect(self._on_type_changed)
        self.table.setCellWidget(row, 0, combo)

        for col, value in enumerate((x, y, w, h), start=1):
            spin = spin_box(0.0, 100.0, value, step=0.05)
            spin.setFrame(False)
            spin.valueChanged.connect(self.on_change)
            self.table.setCellWidget(row, col, spin)

        self._update_row_state(row)
        if notify:
            self.on_change()

    def remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows and self.table.rowCount():
            rows = [self.table.rowCount() - 1]
        for row in rows:
            self.table.removeRow(row)
        self.on_change()

    def _on_type_changed(self):
        for row in range(self.table.rowCount()):
            self._update_row_state(row)
        self.on_change()

    def _update_row_state(self, row):
        is_door = self.table.cellWidget(row, 0).currentText() == "door"
        y_spin = self.table.cellWidget(row, 2)
        y_spin.setEnabled(not is_door)

    def openings(self):
        """List of (kind, x, y, w, h)."""
        result = []
        for row in range(self.table.rowCount()):
            kind = self.table.cellWidget(row, 0).currentText()
            x, y, w, h = (self.table.cellWidget(row, c).value() for c in range(1, 5))
            result.append((kind, x, 0.0 if kind == "door" else y, w, h))
        return result

    def highlight(self, bad_row):
        """Mark the row that caused a validation error (None clears)."""
        for row in range(self.table.rowCount()):
            style = "background: #f8d7da;" if row == bad_row else ""
            for col in range(5):
                self.table.cellWidget(row, col).setStyleSheet(style)


class WallWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Concrete wall - CALFEM plani4e")
        self.resize(1400, 850)

        self.wall = None
        self._loading = True

        # Debounce timer: rebuild/solve shortly after the last change
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.update_model)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_input_panel())
        splitter.addWidget(self._build_result_panel())
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([440, 960])
        self.setCentralWidget(splitter)

        self.status = QLabel()
        self.statusBar().addWidget(self.status, 1)

        # Example openings
        self.openings.add_row("window", 0.6, 0.9, 1.2, 1.2, notify=False)
        self.openings.add_row("door", 2.6, 0.0, 1.0, 2.1, notify=False)
        self.openings.add_row("window", 4.2, 0.9, 1.2, 1.2, notify=False)

        self._loading = False
        self.update_model()

    # ------------------------------------------------------------------
    # Input panel
    # ------------------------------------------------------------------

    def _build_input_panel(self):
        tabs = QTabWidget()
        tabs.addTab(self._geometry_tab(), "Geometry")
        self.openings = OpeningsTable(self.schedule_update)
        tabs.addTab(self.openings, "Openings")
        tabs.addTab(self._material_tab(), "Material")
        tabs.addTab(self._loads_tab(), "Loads && supports")

        self.auto_update = QCheckBox("Update automatically")
        self.auto_update.setChecked(True)
        solve = QPushButton("Solve")
        solve.clicked.connect(self.update_model)

        bottom = QHBoxLayout()
        bottom.addWidget(self.auto_update)
        bottom.addStretch(1)
        bottom.addWidget(solve)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(tabs, 1)
        layout.addLayout(bottom)
        return panel

    def _form_tab(self, rows):
        widget = QWidget()
        form = QFormLayout(widget)
        for label, field in rows:
            form.addRow(label, field)
            self._connect(field)
        return widget

    def _connect(self, field):
        if isinstance(field, QDoubleSpinBox):
            field.valueChanged.connect(self.schedule_update)
        elif isinstance(field, QCheckBox):
            field.toggled.connect(self.schedule_update)
        elif isinstance(field, QLineEdit):
            field.editingFinished.connect(self.schedule_update)

    def _geometry_tab(self):
        self.width_spin = spin_box(0.5, 50.0, 6.0, suffix=" m")
        self.height_spin = spin_box(0.5, 20.0, 3.0, suffix=" m")
        self.thickness_spin = spin_box(0.05, 2.0, 0.2, decimals=3, step=0.01, suffix=" m")
        self.el_size_spin = spin_box(0.01, 1.0, 0.1, decimals=3, step=0.01, suffix=" m")
        self.el_size_spin.setToolTip("Smaller elements give more accurate results "
                                     "but slower updates.")
        return self._form_tab([
            ("Width", self.width_spin),
            ("Height", self.height_spin),
            ("Thickness", self.thickness_spin),
            ("Element size", self.el_size_spin),
        ])

    def _material_tab(self):
        self.E_spin = spin_box(1.0, 100.0, 33.0, decimals=1, step=1.0, suffix=" GPa")
        self.nu_spin = spin_box(0.0, 0.49, 0.2, decimals=3, step=0.01)
        self.density_spin = spin_box(0.0, 10000.0, 2500.0, decimals=0, step=50.0,
                                     suffix=" kg/m³")
        return self._form_tab([
            ("Young's modulus E", self.E_spin),
            ("Poisson's ratio ν", self.nu_spin),
            ("Density", self.density_spin),
        ])

    def _loads_tab(self):
        self.top_load_spin = spin_box(-10000.0, 10000.0, 100.0, decimals=1, step=10.0,
                                      suffix=" kN/m")
        self.top_load_spin.setToolTip("Positive values act downwards.")
        self.hor_load_spin = spin_box(-10000.0, 10000.0, 20.0, decimals=1, step=5.0,
                                      suffix=" kN/m")
        self.hor_load_spin.setToolTip("Positive values act to the right.")
        self.self_weight_check = QCheckBox("Include self weight")
        self.self_weight_check.setChecked(True)

        self.fixed_radio = QRadioButton("Fully supported bottom edge")
        self.free_radio = QRadioButton("Freely supported on bearings")
        self.fixed_radio.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.fixed_radio)
        group.addButton(self.free_radio)
        self.free_radio.toggled.connect(self._update_support_state)
        self.free_radio.toggled.connect(self.schedule_update)

        self.ends_check = QCheckBox("Supports at both ends")
        self.ends_check.setChecked(True)
        self.positions_edit = QLineEdit("2.3, 3.9")
        self.positions_edit.setPlaceholderText("e.g. 2.0, 4.5")
        self.positions_edit.setToolTip("Comma separated x-coordinates of the "
                                       "intermediate support centres.")
        self.support_length_spin = spin_box(0.01, 5.0, 0.3, decimals=2, step=0.05,
                                            suffix=" m")

        widget = self._form_tab([
            ("Vertical top load", self.top_load_spin),
            ("Horizontal top load", self.hor_load_spin),
            ("", self.self_weight_check),
            (QLabel("<b>Supports</b>"), QWidget()),
            ("", self.fixed_radio),
            ("", self.free_radio),
            ("", self.ends_check),
            ("Intermediate supports (x)", self.positions_edit),
            ("Bearing length", self.support_length_spin),
        ])
        widget.layout().addRow(QLabel(
            "Freely supported: the leftmost bearing is pinned,\n"
            "the others are rollers (vertical support only)."))
        self._update_support_state()
        return widget

    def _update_support_state(self):
        free = self.free_radio.isChecked()
        for w in (self.ends_check, self.positions_edit, self.support_length_spin):
            w.setEnabled(free)

    # ------------------------------------------------------------------
    # Result panel
    # ------------------------------------------------------------------

    def _build_result_panel(self):
        self.result_tabs = QTabWidget()
        self.plot_tabs = [
            ("Mesh", PlotTab(lambda w, ax: w.plot_mesh(ax))),
            ("Deformed", PlotTab(lambda w, ax: w.plot_deformed(ax))),
            ("von Mises", PlotTab(lambda w, ax: w.plot_von_mises(ax))),
            ("σ₁", PlotTab(lambda w, ax: w.plot_principal_stress(1, ax))),
            ("σ₂", PlotTab(lambda w, ax: w.plot_principal_stress(2, ax))),
            ("Principal directions",
             PlotTab(lambda w, ax: w.plot_principal_directions(ax))),
        ]
        for name, tab in self.plot_tabs:
            self.result_tabs.addTab(tab, name)

        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        self.summary.setFont(font)
        self.result_tabs.addTab(self.summary, "Summary")

        self.result_tabs.setCurrentIndex(2)
        self.result_tabs.currentChanged.connect(self.redraw_current)
        return self.result_tabs

    # ------------------------------------------------------------------
    # Model update
    # ------------------------------------------------------------------

    def schedule_update(self, *_):
        if not self._loading and self.auto_update.isChecked():
            self.timer.start()

    def _parse_positions(self):
        text = self.positions_edit.text().replace(";", ",")
        try:
            return [float(v) for v in text.split(",") if v.strip()]
        except ValueError:
            raise ValueError(f"Invalid support positions: '{self.positions_edit.text()}'")

    def build_wall(self):
        """Create a ConcreteWall from the current inputs (may raise ValueError)."""
        wall = ConcreteWall(
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            thickness=self.thickness_spin.value(),
            E=self.E_spin.value() * 1e9,
            nu=self.nu_spin.value(),
            density=self.density_spin.value(),
            el_size=self.el_size_spin.value(),
            top_load=self.top_load_spin.value() * 1e3,
            horizontal_load=self.hor_load_spin.value() * 1e3,
            self_weight=self.self_weight_check.isChecked(),
        )
        self.openings.highlight(None)
        for row, (kind, x, y, w, h) in enumerate(self.openings.openings()):
            try:
                if kind == "door":
                    wall.add_door(x, w, h)
                else:
                    wall.add_window(x, y, w, h)
            except ValueError:
                self.openings.highlight(row)
                raise
        if self.free_radio.isChecked():
            wall.set_freely_supported(
                positions=self._parse_positions(),
                ends=self.ends_check.isChecked(),
                support_length=self.support_length_spin.value(),
            )
        else:
            wall.set_fully_supported()
        return wall

    def update_model(self):
        self.timer.stop()
        t0 = time.perf_counter()
        try:
            wall = self.build_wall()
            wall.solve()
        except Exception as e:  # keep the UI alive on invalid input
            self.status.setStyleSheet("color: #b00020;")
            self.status.setText(f"Not solved: {e}")
            return
        t_solve = time.perf_counter() - t0

        self.wall = wall
        for _, tab in self.plot_tabs:
            tab.dirty = True
        self.summary.setPlainText(wall.summary_text())

        t0 = time.perf_counter()
        self.redraw_current()
        t_draw = time.perf_counter() - t0

        self.status.setStyleSheet("")
        self.status.setText(
            f"{wall.n_elements} elements, {2 * wall.n_nodes} dofs  |  "
            f"solve {t_solve * 1e3:.0f} ms, draw {t_draw * 1e3:.0f} ms  |  "
            f"max |u| {wall.max_displacement * 1e3:.3f} mm, "
            f"max σvM {wall.von_mises.max() / 1e6:.2f} MPa"
        )

    def redraw_current(self, *_):
        if self.wall is None:
            return
        tab = self.result_tabs.currentWidget()
        if isinstance(tab, PlotTab) and tab.dirty:
            tab.redraw(self.wall)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = WallWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
