"""Qt application for the footbridge truss: analysis, design checks and design search.

Run with::

    python bridge_app_enchanced.py

Every engineering number comes from ``truss_model.py`` (``TrussBridge``) or
``design_checks.py`` (``line_load``, ``check_design``, ``design_search`` and
the spec data). The application itself does only display work: it converts
units for display, scales the displacements for drawing the deformed shape,
and picks each member's larger utilisation, max(U_yield, U_buckling), to
colour the member.

Compared with ``bridge_app.py`` this version adds:

* a menu bar (File, View, Tools, Help);
* model files: File > New, Open, Save and Save As. A model file is a JSON
  file holding the input parameters and the deformation display settings;
* deformation scale options: auto-scaling to a chosen fraction of the span
  (rounded to a 1-2-5 factor), a fixed factor, or true scale.
"""

import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
from qtpy.QtCore import QObject, Qt, QThread, Signal
from qtpy.QtGui import QAction, QActionGroup, QKeySequence
from qtpy.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.collections import LineCollection
from matplotlib.colors import CenteredNorm, Normalize
from matplotlib.figure import Figure
import matplotlib

import design_checks as dc
from truss_model import TRUSS_TYPES, TrussBridge

#: Number of designs listed after a search.
N_LISTED = 20

#: Model file format identifier and version.
MODEL_FORMAT = "footbridge-truss-model"
MODEL_VERSION = 1
MODEL_FILE_FILTER = "Footbridge model (*.bridge.json *.json);;All files (*)"

#: Deformation display modes (display only, no effect on any result).
SCALE_AUTO = "auto"
SCALE_FIXED = "fixed"
SCALE_TRUE = "true"
SCALE_MODE_LABELS = {
    SCALE_AUTO: "Auto (fraction of span)",
    SCALE_FIXED: "Fixed factor",
    SCALE_TRUE: "True scale (×1)",
}

#: A new model: the spec's values (D1, D3) and the first search values.
DEFAULT_MODEL = {
    "truss_type": "pratt",
    "L_m": dc.SPAN,
    "h_m": dc.H_VALUES[0],
    "n": dc.N_VALUES[0],
    "q_N_per_m2": dc.CROWD_LOAD,
    "chord": "SHS 100x5",
    "web": "SHS 80x4",
    "deformation": {
        "mode": SCALE_AUTO,
        "auto_percent_of_span": 3.0,
        "fixed_factor": 50.0,
    },
}


def nice_scale_below(x):
    """Return the largest 1-2-5 number (1, 2, 5, 10, 20, ...) not above x (display only)."""
    if x <= 0 or not math.isfinite(x):
        return 1.0
    exponent = math.floor(math.log10(x))
    for mantissa in (5.0, 2.0, 1.0):
        value = mantissa * 10.0 ** exponent
        if value <= x * (1 + 1e-12):
            return value
    return 10.0 ** exponent


def deformation_scale(settings, a_max, L):
    """Return the display scale factor for the deformed shape.

    * auto: the largest displacement is drawn as at most the chosen
      percentage of the span, and the factor is rounded down to 1-2-5;
    * fixed: the factor given by the user;
    * true: 1.
    """
    mode = settings["mode"]
    if mode == SCALE_TRUE:
        return 1.0
    if mode == SCALE_FIXED:
        return float(settings["fixed_factor"])
    if a_max <= 0:
        return 1.0
    return nice_scale_below(settings["auto_percent_of_span"] / 100.0 * L / a_max)


# ---------------------------------------------------------------------------
# Shared parameter panel
# ---------------------------------------------------------------------------

class ParameterPanel(QGroupBox):
    """Inputs shared by both tabs: truss type, L, h, n, deck load and sections."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__("Parameters", parent)
        form = QFormLayout(self)

        self.truss_type = QComboBox()
        self.truss_type.addItems([t.capitalize() for t in TRUSS_TYPES])

        self.L = self._double(1.0, 100.0, dc.SPAN, 0.5, " m")
        self.h = self._double(0.5, 20.0, dc.H_VALUES[0], 0.5, " m")

        self.n = QSpinBox()
        self.n.setRange(2, 30)
        self.n.setSingleStep(2)
        self.n.setValue(dc.N_VALUES[0])
        self.n.setToolTip("Number of panels (even)")

        self.q = self._double(0.0, 20.0, dc.CROWD_LOAD / 1e3, 0.5, " kN/m²")
        self.q.setToolTip("Crowd load on the deck (characteristic)")

        self.chord = QComboBox()
        self.web = QComboBox()
        names = [s.name for s in dc.SECTIONS]
        self.chord.addItems(names)
        self.web.addItems(names)
        self.chord.setCurrentText("SHS 100x5")
        self.web.setCurrentText("SHS 80x4")

        form.addRow("Truss type", self.truss_type)
        form.addRow("Span L", self.L)
        form.addRow("Height h", self.h)
        form.addRow("Panels n", self.n)
        form.addRow("Deck load q", self.q)
        form.addRow(QLabel(f"Deck width b = {dc.DECK_WIDTH:g} m (spec D2)"))
        form.addRow(QLabel(f"E = {dc.E_STEEL / 1e9:g} GPa, S355"))
        form.addRow("Chord section", self.chord)
        form.addRow("Web section", self.web)

        for w in (self.L, self.h, self.q):
            w.valueChanged.connect(self.changed)
        self.n.valueChanged.connect(self.changed)
        for w in (self.truss_type, self.chord, self.web):
            w.currentIndexChanged.connect(self.changed)

    @staticmethod
    def _double(lo, hi, value, step, suffix):
        box = QDoubleSpinBox()
        box.setRange(lo, hi)
        box.setDecimals(2)
        box.setSingleStep(step)
        box.setValue(value)
        box.setSuffix(suffix)
        return box

    def values(self):
        """Return the current inputs, in SI units."""
        return dict(
            truss_type=self.truss_type.currentText().lower(),
            L=self.L.value(),
            h=self.h.value(),
            n=self.n.value(),
            q=self.q.value() * 1e3,
            chord=dc.SECTIONS_BY_NAME[self.chord.currentText()],
            web=dc.SECTIONS_BY_NAME[self.web.currentText()],
        )

    def model_values(self):
        """Return the inputs as stored in a model file (SI units, section names)."""
        return {
            "truss_type": self.truss_type.currentText().lower(),
            "L_m": self.L.value(),
            "h_m": self.h.value(),
            "n": self.n.value(),
            "q_N_per_m2": self.q.value() * 1e3,
            "chord": self.chord.currentText(),
            "web": self.web.currentText(),
        }

    def set_model_values(self, m):
        """Set all inputs from model-file values and emit ``changed`` once."""
        widgets = (self.truss_type, self.L, self.h, self.n, self.q, self.chord, self.web)
        for w in widgets:
            w.blockSignals(True)
        self.truss_type.setCurrentText(m["truss_type"].capitalize())
        self.L.setValue(m["L_m"])
        self.h.setValue(m["h_m"])
        self.n.setValue(m["n"])
        self.q.setValue(m["q_N_per_m2"] / 1e3)
        self.chord.setCurrentText(m["chord"])
        self.web.setCurrentText(m["web"])
        for w in widgets:
            w.blockSignals(False)
        self.changed.emit()

    def set_design(self, d):
        """Load a design (DesignResult) into the inputs."""
        widgets = (self.truss_type, self.h, self.n, self.chord, self.web)
        for w in widgets:
            w.blockSignals(True)
        self.truss_type.setCurrentText(d.truss_type.capitalize())
        self.h.setValue(d.h)
        self.n.setValue(d.n)
        self.chord.setCurrentText(d.chord.name)
        self.web.setCurrentText(d.web.name)
        for w in widgets:
            w.blockSignals(False)
        self.changed.emit()


def _new_canvas():
    fig = Figure(figsize=(8, 4), layout="constrained")
    return fig, FigureCanvasQTAgg(fig)


def _show_error(ax, canvas, message):
    ax.clear()
    ax.set_axis_off()
    ax.text(0.5, 0.5, message, ha="center", va="center", color="tab:red",
            transform=ax.transAxes, wrap=True)
    canvas.draw_idle()


# ---------------------------------------------------------------------------
# Analysis tab
# ---------------------------------------------------------------------------

class AnalysisTab(QWidget):
    """Deformed shape under LC-full, members coloured by normal force."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig, self.canvas = _new_canvas()
        self.info = QLabel()
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._last_params = None

        # Deformation display controls (display only).
        self.scale_mode = QComboBox()
        for mode, label in SCALE_MODE_LABELS.items():
            self.scale_mode.addItem(label, mode)
        self.auto_percent = QDoubleSpinBox()
        self.auto_percent.setRange(0.1, 25.0)
        self.auto_percent.setDecimals(1)
        self.auto_percent.setSingleStep(0.5)
        self.auto_percent.setSuffix(" % of L")
        self.auto_percent.setToolTip(
            "Auto: the largest displacement is drawn as at most this fraction of the span. "
            "The factor is rounded down to 1, 2 or 5 × 10^k.")
        self.fixed_factor = QDoubleSpinBox()
        self.fixed_factor.setRange(0.1, 1.0e6)
        self.fixed_factor.setDecimals(1)
        self.fixed_factor.setPrefix("×")
        self.fixed_factor.setToolTip("Fixed: displacements are multiplied by this factor.")

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Deformation scale:"))
        controls.addWidget(self.scale_mode)
        controls.addWidget(self.auto_percent)
        controls.addWidget(self.fixed_factor)
        controls.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.info)

        self.set_deformation_settings(DEFAULT_MODEL["deformation"], emit=False)
        self.scale_mode.currentIndexChanged.connect(self._on_settings_changed)
        self.auto_percent.valueChanged.connect(self._on_settings_changed)
        self.fixed_factor.valueChanged.connect(self._on_settings_changed)

    def deformation_settings(self):
        """Return the deformation display settings as stored in a model file."""
        return {
            "mode": self.scale_mode.currentData(),
            "auto_percent_of_span": self.auto_percent.value(),
            "fixed_factor": self.fixed_factor.value(),
        }

    def set_deformation_settings(self, s, emit=True):
        for w in (self.scale_mode, self.auto_percent, self.fixed_factor):
            w.blockSignals(True)
        self.scale_mode.setCurrentIndex(self.scale_mode.findData(s["mode"]))
        self.auto_percent.setValue(s["auto_percent_of_span"])
        self.fixed_factor.setValue(s["fixed_factor"])
        for w in (self.scale_mode, self.auto_percent, self.fixed_factor):
            w.blockSignals(False)
        self._update_control_state()
        if emit:
            self._on_settings_changed()

    def set_scale_mode(self, mode):
        self.scale_mode.setCurrentIndex(self.scale_mode.findData(mode))

    def _update_control_state(self):
        mode = self.scale_mode.currentData()
        self.auto_percent.setEnabled(mode == SCALE_AUTO)
        self.fixed_factor.setEnabled(mode == SCALE_FIXED)

    def _on_settings_changed(self, *_):
        self._update_control_state()
        if self._last_params is not None:
            self.update_view(self._last_params)
        self.settings_changed.emit()

    def update_view(self, p):
        self._last_params = p
        self.fig.clear()
        ax = self.fig.add_subplot()
        try:
            bridge = TrussBridge(p["truss_type"], p["L"], p["h"], p["n"])
            w = dc.line_load(p["q"], dc.DECK_WIDTH)
            a, r, N, _N_max, _N_min = bridge.solve(dc.E_STEEL, p["chord"].A, p["web"].A, w)
        except ValueError as exc:
            self.info.setText("")
            _show_error(ax, self.canvas, str(exc))
            return

        coords = bridge.coords
        disp = a.reshape(-1, 2)
        a_max = np.abs(disp).max()
        # Display scaling only (View > Deformation scale).
        settings = self.deformation_settings()
        scale = deformation_scale(settings, a_max, bridge.L)
        deformed = coords + scale * disp

        elems = bridge.elements - 1
        undeformed_segs = coords[elems]
        deformed_segs = deformed[elems]
        N_kN = N / 1e3

        ax.add_collection(LineCollection(undeformed_segs, colors="lightgrey",
                                         linestyles="--", linewidths=1.0, zorder=1))
        halfrange = np.abs(N_kN).max() or 1.0
        lc = LineCollection(deformed_segs, cmap="RdBu_r",
                            norm=CenteredNorm(vcenter=0.0, halfrange=halfrange),
                            linewidths=3.0, zorder=2)
        lc.set_array(N_kN)
        ax.add_collection(lc)
        cbar = self.fig.colorbar(lc, ax=ax, shrink=0.8)
        cbar.set_label("Normal force N [kN]  (tension +, compression −)")

        ax.plot(deformed[:, 0], deformed[:, 1], "o", color="black", ms=3, zorder=3)
        for k in bridge.support_nodes:
            x, y = coords[k - 1]
            ax.plot(x, y, marker="^", color="dimgray", ms=12, zorder=0)

        ax.set_aspect("equal")
        ax.autoscale_view()
        ax.margins(0.05, 0.15)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title(f"{bridge.truss_type.capitalize()}, LC-full (crowd load on all panels)")
        if settings["mode"] == SCALE_AUTO:
            how = f"auto, ≤ {settings['auto_percent_of_span']:g} % of L"
        elif settings["mode"] == SCALE_FIXED:
            how = "fixed"
        else:
            how = "true scale"
        ax.text(0.01, 0.98, f"Deformation scale factor: ×{scale:,.6g}  ({how})",
                transform=ax.transAxes, va="top", fontsize=10,
                bbox=dict(fc="white", ec="grey", alpha=0.9))
        self.canvas.draw_idle()

        u_mid = a[2 * bridge.midspan_node - 1]
        self.info.setText(
            f"w = {w / 1e3:.3f} kN/m   |   midspan deflection u_y = {u_mid * 1e3:.2f} mm   |   "
            f"N from {N_kN.min():.2f} to {N_kN.max():.2f} kN   |   "
            f"{bridge.num_nodes} nodes, {bridge.num_elements} members"
        )


# ---------------------------------------------------------------------------
# Design search in a background thread
# ---------------------------------------------------------------------------

class _Cancelled(Exception):
    pass


class SearchWorker(QObject):
    """Runs dc.design_search in a worker thread."""

    progress = Signal(int, int)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, L, q):
        super().__init__()
        self.L = L
        self.q = q
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _on_progress(self, done, total):
        # Stop by raising from the progress callback, the only hook that
        # design_search offers.
        if self._cancel:
            raise _Cancelled()
        if done % 50 == 0 or done == total:
            self.progress.emit(done, total)

    def run(self):
        try:
            result = dc.design_search(L=self.L, q=self.q, progress=self._on_progress)
        except _Cancelled:
            self.failed.emit("Search cancelled.")
            return
        except Exception as exc:  # report any failure in the GUI
            self.failed.emit(f"Search failed: {exc}")
            return
        self.finished.emit(result)


# ---------------------------------------------------------------------------
# Engineering summary
# ---------------------------------------------------------------------------

def engineering_summary(result, L, q, n_listed=10):
    """Return a Markdown engineering summary of a design search result.

    All values come from design_checks (spec data and the DesignResult
    objects in ``result``). Units are converted for display only.
    """
    w = dc.line_load(q, dc.DECK_WIDTH)
    lines = [
        "# Footbridge truss: engineering summary",
        "",
        f"Date: {date.today().isoformat()}. Generated by bridge_app.py from design_checks.py "
        "and truss_model.py. Basis: bridge_spec_final.md.",
        "",
        "## Design basis",
        "",
        f"- Span L = {L:g} m, deck width b = {dc.DECK_WIDTH:g} m, two identical trusses.",
        f"- Crowd load q = {q / 1e3:g} kN/m² (characteristic), line load per truss "
        f"w = q·b/2 = {w / 1e3:g} kN/m. Self-weight ignored.",
        "- Load cases: full span (LC-full) and the envelope over all partial-span panel "
        "patterns, for yield and buckling. Deflection under LC-full.",
        f"- Steel S355 (f_y = 355 MPa for t ≤ 40 mm), E = {dc.E_STEEL / 1e9:g} GPa, "
        f"ρ = {dc.DENSITY:g} kg/m³.",
        f"- Partial factors γ_Q = {dc.GAMMA_Q:g}, γ_M0 = {dc.GAMMA_M0:g}, γ_M1 = {dc.GAMMA_M1:g} "
        "(characteristic, no factors).",
        "- C1 yield: |N| ≤ A·f_y. C2 buckling: elastic Euler, L_cr = member length, "
        "I = min(I_y, I_z). C3 deflection: |u_y(midspan)| ≤ L/400.",
        f"- Design space: {', '.join(t.capitalize() for t in dc.TRUSS_TYPE_ORDER)}; "
        f"n ∈ {{{', '.join(str(n) for n in dc.N_VALUES)}}}; "
        f"h = {dc.H_VALUES[0]:g} … {dc.H_VALUES[-1]:g} m; "
        f"{len(dc.SECTIONS)} sections for chords and web independently.",
        "",
        "## Result",
        "",
        f"{result.num_designs:,} designs checked, {len(result.passing):,} pass all checks.",
        "",
    ]

    if result.passing:
        best = result.lightest
        lines += [
            f"**Lightest passing design:** {best.truss_type.capitalize()} truss, n = {best.n}, "
            f"h = {best.h:g} m, chords {best.chord.name}, web {best.web.name}, "
            f"mass {best.mass:.1f} kg per truss.",
            "",
            f"## Lightest {min(n_listed, len(result.passing))} passing designs",
            "",
            "| # | Type | n | h [m] | Chord | Web | Mass [kg] | U_yield | U_buckling | U_defl | Governing |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for i, d in enumerate(result.passing[:n_listed], start=1):
            lines.append(
                f"| {i} | {d.truss_type.capitalize()} | {d.n} | {d.h:g} | {d.chord.name} | "
                f"{d.web.name} | {d.mass:.1f} | {d.U_yield_max:.3f} | {d.U_buckling_max:.3f} | "
                f"{d.U_deflection:.3f} | {_governing_text(d)} |"
            )
        lines += [
            "",
            "## Lightest design in detail",
            "",
            f"- Nodal loads: P = {best.P / 1e3:.3f} kN (interior), P_end = {best.P_end / 1e3:.3f} kN (supports).",
            f"- C1 yield: max utilisation {best.U_yield_max:.3f} "
            f"({'pass' if best.passes_yield else 'FAIL'}).",
            f"- C2 buckling: max utilisation {best.U_buckling_max:.3f} "
            f"({'pass' if best.passes_buckling else 'FAIL'}); "
            f"{int(best.compression.sum())} of {len(best.compression)} members are in "
            "compression in at least one load pattern.",
            f"- C3 deflection: u_y = {best.u_midspan * 1e3:.2f} mm, limit L/400 = "
            f"{L / dc.DEFLECTION_RATIO * 1e3:.1f} mm, utilisation {best.U_deflection:.3f} "
            f"({'pass' if best.passes_deflection else 'FAIL'}).",
            f"- Governing: {_governing_text(best)}, U_max = {best.U_max:.3f}.",
            f"- Steel mass: {best.mass:.1f} kg per truss, {2 * best.mass:.1f} kg for both trusses.",
        ]
    else:
        c = result.closest
        lines += [
            "**No design passes.**",
            "",
            f"Closest design: {c.truss_type.capitalize()}, n = {c.n}, h = {c.h:g} m, chords "
            f"{c.chord.name}, web {c.web.name}, U_max = {c.U_max:.3f} ({_governing_text(c)}).",
        ]

    lines += [
        "",
        "## Limitations",
        "",
        "- Not checked in this version (spec section 1): connections, fatigue, vibration and "
        "pedestrian comfort, wind and other lateral loads, deck and cross-beam design, bracing. "
        "Vibration often governs light footbridges of this span.",
        "- Euler buckling without imperfections overestimates the capacity of members with "
        "intermediate slenderness. The top chord is assumed laterally restrained at every node.",
        "- Characteristic loads without partial factors. This is not a code-compliant ULS design.",
        "",
    ]
    return "\n".join(lines)


def _governing_text(d):
    if d.governing_member is None:
        return d.governing_check
    group = d.member_groups[d.governing_member - 1]
    return f"{d.governing_check}, member {d.governing_member} ({group})"


class SummaryDialog(QDialog):
    """Shows the engineering summary and lets the user save it."""

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Engineering summary")
        self.resize(900, 650)
        self.text = text
        edit = QPlainTextEdit(text)
        edit.setReadOnly(True)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(edit)
        layout.addWidget(buttons)

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save engineering summary",
                                              "engineering_summary.md", "Markdown (*.md)")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.text)


# ---------------------------------------------------------------------------
# Design tab
# ---------------------------------------------------------------------------

def _pass_text(ok):
    return "<b style='color:#1a7f37'>PASS</b>" if ok else "<b style='color:#cf222e'>FAIL</b>"


class DesignTab(QWidget):
    """Design checks for the chosen sections, and the design search."""

    load_design = Signal(object)

    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self.panel = panel
        self.result = None
        self.result_inputs = None
        self.thread = None
        self.worker = None

        self.fig, self.canvas = _new_canvas()
        self.summary = QLabel()
        self.summary.setTextFormat(Qt.RichText)
        self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse)

        check_box = QWidget()
        cl = QVBoxLayout(check_box)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(self.canvas, 1)
        cl.addWidget(self.summary)

        # Search controls and results.
        self.run_button = QPushButton("Run design search")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.report_button = QPushButton("Engineering summary…")
        self.report_button.setEnabled(False)
        self.progress = QProgressBar()
        self.progress.setFormat("%v / %m designs")
        self.search_info = QLabel(
            "Searches all truss types, the spec's panel counts and heights, and all "
            f"{len(dc.SECTIONS)}² section combinations. Uses the current L and q.")
        self.search_info.setWordWrap(True)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["Type", "n", "h [m]", "Chord", "Web", "Mass [kg]", "U_max", "Governing", "Pass"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setToolTip("Double-click a design to load it into the parameters")
        self.table.cellDoubleClicked.connect(self._row_activated)

        buttons = QHBoxLayout()
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.report_button)
        buttons.addStretch(1)

        search_box = QGroupBox("Design search (spec 6.4)")
        sl = QVBoxLayout(search_box)
        sl.addLayout(buttons)
        sl.addWidget(self.progress)
        sl.addWidget(self.search_info)
        sl.addWidget(self.table, 1)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(check_box)
        splitter.addWidget(search_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        self.run_button.clicked.connect(self.start_search)
        self.cancel_button.clicked.connect(self.cancel_search)
        self.report_button.clicked.connect(self.show_summary)

    # -- design checks for the current parameters --------------------------

    def update_view(self, p):
        self.fig.clear()
        ax = self.fig.add_subplot()
        try:
            d = dc.check_design(p["truss_type"], p["h"], p["n"], p["chord"], p["web"],
                                L=p["L"], q=p["q"])
            bridge = TrussBridge(p["truss_type"], p["L"], p["h"], p["n"])
        except ValueError as exc:
            self.summary.setText("")
            _show_error(ax, self.canvas, str(exc))
            return

        coords = bridge.coords
        segs = coords[bridge.elements - 1]
        # Display only: colour each member by its larger utilisation.
        U_member = np.maximum(d.U_yield, d.U_buckling)

        cmap = matplotlib.colormaps["RdYlGn_r"].with_extremes(over="#7b2cbf")
        lc = LineCollection(segs, cmap=cmap, norm=Normalize(0.0, 1.0), linewidths=4.0, zorder=2)
        lc.set_array(U_member)

        if d.governing_member is not None:
            g = d.governing_member - 1
            ax.add_collection(LineCollection([segs[g]], colors="black", linewidths=9.0, zorder=1))
            mid = segs[g].mean(axis=0)
            ax.annotate(f"governing: member {d.governing_member}\n{d.governing_check}",
                        mid, xytext=(0, 28), textcoords="offset points", ha="center",
                        fontsize=9, arrowprops=dict(arrowstyle="->"),
                        bbox=dict(fc="white", ec="black"))
        ax.add_collection(lc)
        cbar = self.fig.colorbar(lc, ax=ax, shrink=0.8, extend="max")
        cbar.set_label("Member utilisation max(U_yield, U_buckling)")

        ax.plot(coords[:, 0], coords[:, 1], "o", color="black", ms=3, zorder=3)
        mid_node = coords[bridge.midspan_node - 1]
        if d.governing_member is None:
            ax.plot(*mid_node, marker="*", color="black", ms=18, zorder=4)
            ax.annotate(f"governing: {d.governing_check}", mid_node, xytext=(0, -30),
                        textcoords="offset points", ha="center", fontsize=9,
                        bbox=dict(fc="white", ec="black"))
        for k in bridge.support_nodes:
            ax.plot(*coords[k - 1], marker="^", color="dimgray", ms=12, zorder=0)

        ax.set_aspect("equal")
        ax.autoscale_view()
        ax.margins(0.05, 0.25)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title(f"{d.truss_type.capitalize()}, n = {d.n}, h = {d.h:g} m — "
                     f"chords {d.chord.name}, web {d.web.name}")
        self.canvas.draw_idle()

        self.summary.setText(
            "<table cellspacing='8'>"
            f"<tr><td>C1 yield (stress)</td><td>max U = {d.U_yield_max:.3f}</td>"
            f"<td>{_pass_text(d.passes_yield)}</td></tr>"
            f"<tr><td>C2 buckling</td><td>max U = {d.U_buckling_max:.3f}</td>"
            f"<td>{_pass_text(d.passes_buckling)}</td></tr>"
            f"<tr><td>C3 deflection</td><td>U = {d.U_deflection:.3f} "
            f"(u<sub>y</sub> = {d.u_midspan * 1e3:.2f} mm)</td>"
            f"<td>{_pass_text(d.passes_deflection)}</td></tr>"
            f"<tr><td><b>Overall</b></td><td>U<sub>max</sub> = {d.U_max:.3f}, "
            f"governing: {_governing_text(d)}</td><td>{_pass_text(d.passes)}</td></tr>"
            f"<tr><td>Steel mass</td><td>{d.mass:.1f} kg per truss</td><td></td></tr>"
            "</table>"
        )

    # -- design search -------------------------------------------------------

    def start_search(self):
        p = self.panel.values()
        self.result_inputs = (p["L"], p["q"])
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.report_button.setEnabled(False)
        self.table.setRowCount(0)
        self.search_info.setText("Searching…")

        self.thread = QThread(self)
        self.worker = SearchWorker(p["L"], p["q"])
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.start()

    def cancel_search(self):
        if self.worker is not None:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)

    def _on_progress(self, done, total):
        self.progress.setMaximum(total)
        self.progress.setValue(done)

    def _search_done(self):
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def _on_failed(self, message):
        self._search_done()
        self.search_info.setText(message)

    def _on_finished(self, result):
        self._search_done()
        self.result = result
        self.report_button.setEnabled(True)
        L, q = self.result_inputs
        shown = result.passing[:N_LISTED] if result.passing else [result.closest]
        self.table.setRowCount(len(shown))
        for row, d in enumerate(shown):
            cells = [d.truss_type.capitalize(), str(d.n), f"{d.h:g}", d.chord.name, d.web.name,
                     f"{d.mass:.1f}", f"{d.U_max:.3f}", _governing_text(d),
                     "yes" if d.passes else "no"]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col in (1, 2, 5, 6):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, item)
        self._shown = shown

        if result.passing:
            best = result.lightest
            self.search_info.setText(
                f"L = {L:g} m, q = {q / 1e3:g} kN/m²: {result.num_designs:,} designs checked, "
                f"{len(result.passing):,} pass. Lightest: {best.truss_type.capitalize()}, "
                f"n = {best.n}, h = {best.h:g} m, chords {best.chord.name}, web {best.web.name}, "
                f"{best.mass:.1f} kg per truss. Showing the {len(shown)} lightest.")
        else:
            self.search_info.setText(
                f"{result.num_designs:,} designs checked, none passes. "
                "Showing the design with the lowest U_max.")

    def _row_activated(self, row, _col):
        self.load_design.emit(self._shown[row])

    def show_summary(self):
        if self.result is None:
            return
        L, q = self.result_inputs
        SummaryDialog(engineering_summary(self.result, L, q), self).exec()

    def shutdown(self):
        """Stop a running search before the window closes."""
        if self.thread is not None and self.thread.isRunning():
            self.worker.cancel()
            self.thread.quit()
            self.thread.wait(5000)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class ModelFileError(Exception):
    """Raised when a model file cannot be read or is not valid."""


def model_to_json(model):
    """Return the model file text for a model dictionary."""
    data = {"format": MODEL_FORMAT, "version": MODEL_VERSION, **model}
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def model_from_json(text):
    """Parse and validate model file text. Return the model dictionary.

    Raises ModelFileError with a readable message if the file is not a valid
    model file. Numbers are only checked for type here. Invalid geometry,
    such as an odd n, is reported by the model when it is analysed.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelFileError(f"not a JSON file ({exc})") from exc
    if not isinstance(data, dict) or data.get("format") != MODEL_FORMAT:
        raise ModelFileError("not a footbridge model file (missing or wrong 'format')")
    if data.get("version") != MODEL_VERSION:
        raise ModelFileError(f"unsupported model file version {data.get('version')!r}")

    try:
        model = {
            "truss_type": str(data["truss_type"]).lower(),
            "L_m": float(data["L_m"]),
            "h_m": float(data["h_m"]),
            "n": int(data["n"]),
            "q_N_per_m2": float(data["q_N_per_m2"]),
            "chord": str(data["chord"]),
            "web": str(data["web"]),
        }
        d = data.get("deformation", DEFAULT_MODEL["deformation"])
        model["deformation"] = {
            "mode": str(d["mode"]),
            "auto_percent_of_span": float(d["auto_percent_of_span"]),
            "fixed_factor": float(d["fixed_factor"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ModelFileError(f"missing or invalid entry: {exc}") from exc

    if model["truss_type"] not in TRUSS_TYPES:
        raise ModelFileError(f"unknown truss type {model['truss_type']!r}")
    for key in ("chord", "web"):
        if model[key] not in dc.SECTIONS_BY_NAME:
            raise ModelFileError(f"unknown {key} section {model[key]!r} (not in spec table 4.1)")
    if model["deformation"]["mode"] not in SCALE_MODE_LABELS:
        raise ModelFileError(f"unknown deformation mode {model['deformation']['mode']!r}")
    return model


class MainWindow(QMainWindow):
    APP_TITLE = "Footbridge truss designer"

    def __init__(self):
        super().__init__()
        self.resize(1400, 850)
        self.file_path = None
        self.dirty = False

        self.panel = ParameterPanel()
        self.analysis = AnalysisTab()
        self.design = DesignTab(self.panel)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.analysis, "Analysis")
        self.tabs.addTab(self.design, "Design")

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(self.panel)
        ll.addStretch(1)

        central = QSplitter(Qt.Horizontal)
        central.addWidget(left)
        central.addWidget(self.tabs)
        central.setStretchFactor(1, 1)
        self.setCentralWidget(central)

        self._build_menus()

        self.panel.changed.connect(self._on_model_changed)
        self.analysis.settings_changed.connect(self._mark_dirty)
        self.design.load_design.connect(self._load_design)

        self._apply_model(DEFAULT_MODEL)
        self._set_clean(None)

    # -- menus ---------------------------------------------------------------

    def _action(self, menu, text, slot, shortcut=None, tip=None):
        act = QAction(text, self)
        if shortcut is not None:
            act.setShortcut(shortcut)
        if tip:
            act.setStatusTip(tip)
        act.triggered.connect(lambda _checked=False: slot())
        menu.addAction(act)
        return act

    def _build_menus(self):
        bar = self.menuBar()

        file_menu = bar.addMenu("&File")
        self._action(file_menu, "&New", self.file_new, QKeySequence.New,
                     "Start a new model with the spec's default values")
        self._action(file_menu, "&Open…", self.file_open, QKeySequence.Open,
                     "Open a model file")
        file_menu.addSeparator()
        self._action(file_menu, "&Save", self.file_save, QKeySequence.Save, "Save the model")
        self._action(file_menu, "Save &As…", self.file_save_as, QKeySequence.SaveAs,
                     "Save the model under a new name")
        file_menu.addSeparator()
        self.export_summary_action = self._action(
            file_menu, "Export &engineering summary…", self.design.show_summary,
            tip="Show and save the engineering summary of the last design search")
        file_menu.addSeparator()
        self._action(file_menu, "E&xit", self.close, QKeySequence.Quit)
        file_menu.aboutToShow.connect(self._update_menu_state)

        view_menu = bar.addMenu("&View")
        self._action(view_menu, "&Analysis tab",
                     lambda: self.tabs.setCurrentWidget(self.analysis), "Ctrl+1")
        self._action(view_menu, "&Design tab",
                     lambda: self.tabs.setCurrentWidget(self.design), "Ctrl+2")
        view_menu.addSeparator()
        scale_menu = view_menu.addMenu("Deformation &scale")
        self.scale_group = QActionGroup(self)
        self.scale_actions = {}
        for mode, label in SCALE_MODE_LABELS.items():
            act = QAction(label, self)
            act.setCheckable(True)
            act.triggered.connect(lambda _checked=False, m=mode: self._choose_scale_mode(m))
            self.scale_group.addAction(act)
            scale_menu.addAction(act)
            self.scale_actions[mode] = act
        scale_menu.addSeparator()
        for pct in (1.0, 2.0, 3.0, 5.0, 10.0):
            self._action(scale_menu, f"Auto, {pct:g} % of span",
                         lambda v=pct: self._choose_auto_percent(v))
        view_menu.aboutToShow.connect(self._update_menu_state)
        scale_menu.aboutToShow.connect(self._update_menu_state)

        tools_menu = bar.addMenu("&Tools")
        self.run_search_action = self._action(
            tools_menu, "&Run design search", self._run_search, "F5",
            "Search all designs in the spec's design space")
        self.cancel_search_action = self._action(
            tools_menu, "&Cancel design search", self.design.cancel_search)
        tools_menu.aboutToShow.connect(self._update_menu_state)

        help_menu = bar.addMenu("&Help")
        self._action(help_menu, "&About", self._about)

        self.statusBar()

    def _update_menu_state(self):
        mode = self.analysis.deformation_settings()["mode"]
        for m, act in self.scale_actions.items():
            act.setChecked(m == mode)
        self.export_summary_action.setEnabled(self.design.result is not None)
        self.run_search_action.setEnabled(self.design.run_button.isEnabled())
        self.cancel_search_action.setEnabled(self.design.cancel_button.isEnabled())

    def _choose_scale_mode(self, mode):
        self.analysis.set_scale_mode(mode)
        self.tabs.setCurrentWidget(self.analysis)

    def _choose_auto_percent(self, pct):
        s = self.analysis.deformation_settings()
        s.update(mode=SCALE_AUTO, auto_percent_of_span=pct)
        self.analysis.set_deformation_settings(s)
        self.tabs.setCurrentWidget(self.analysis)

    def _run_search(self):
        self.tabs.setCurrentWidget(self.design)
        if self.design.run_button.isEnabled():
            self.design.start_search()

    def _about(self):
        QMessageBox.about(
            self, "About",
            f"<b>{self.APP_TITLE}</b><p>2D truss footbridge analysis and design checks.</p>"
            "<p>Model: truss_model.py (CALFEM for Python). Checks and search: "
            "design_checks.py. Basis: bridge_spec_final.md.</p>")

    # -- model state ---------------------------------------------------------

    def current_model(self):
        """Return the current model as stored in a model file."""
        return {**self.panel.model_values(), "deformation": self.analysis.deformation_settings()}

    def _apply_model(self, model):
        # Deformation settings first, without redrawing, then the parameters.
        # Their changed signal redraws both tabs once.
        self.analysis.set_deformation_settings(model["deformation"], emit=False)
        self.panel.set_model_values(model)

    def _on_model_changed(self):
        self.refresh()
        self._mark_dirty()

    def _mark_dirty(self):
        if not self.dirty:
            self.dirty = True
            self._update_title()

    def _set_clean(self, path):
        self.file_path = path
        self.dirty = False
        self._update_title()

    def _update_title(self):
        name = Path(self.file_path).name if self.file_path else "Untitled"
        self.setWindowTitle(f"{name}{' *' if self.dirty else ''} — {self.APP_TITLE}")

    def _confirm_discard(self):
        """Ask to save unsaved changes. Return True if it is OK to continue."""
        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self, "Unsaved changes", "The model has unsaved changes. Save them first?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.file_save()
        return answer == QMessageBox.Discard

    # -- file actions --------------------------------------------------------

    def file_new(self):
        if not self._confirm_discard():
            return False
        self._apply_model(DEFAULT_MODEL)
        self._set_clean(None)
        self.statusBar().showMessage("New model", 3000)
        return True

    def file_open(self, path=None):
        if not self._confirm_discard():
            return False
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open model", "", MODEL_FILE_FILTER)
            if not path:
                return False
        try:
            model = model_from_json(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ModelFileError) as exc:
            QMessageBox.critical(self, "Open model", f"Could not open {path}:\n{exc}")
            return False
        self._apply_model(model)
        self._set_clean(path)
        self.statusBar().showMessage(f"Opened {path}", 3000)
        return True

    def file_save(self):
        if self.file_path is None:
            return self.file_save_as()
        return self._write(self.file_path)

    def file_save_as(self, path=None):
        if not path:
            start = self.file_path or "footbridge.bridge.json"
            path, _ = QFileDialog.getSaveFileName(self, "Save model as", start, MODEL_FILE_FILTER)
            if not path:
                return False
        return self._write(path)

    def _write(self, path):
        try:
            Path(path).write_text(model_to_json(self.current_model()), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Save model", f"Could not save {path}:\n{exc}")
            return False
        self._set_clean(path)
        self.statusBar().showMessage(f"Saved {path}", 3000)
        return True

    # -- views ---------------------------------------------------------------

    def refresh(self):
        p = self.panel.values()
        self.analysis.update_view(p)
        self.design.update_view(p)

    def _load_design(self, d):
        self.panel.set_design(d)
        self.tabs.setCurrentWidget(self.design)

    def closeEvent(self, event):
        if not self._confirm_discard():
            event.ignore()
            return
        self.design.shutdown()
        super().closeEvent(event)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
