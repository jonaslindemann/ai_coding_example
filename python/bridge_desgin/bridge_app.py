"""Qt application for the footbridge truss: analysis, design checks and design search.

Run with::

    python bridge_app.py

Every engineering number comes from ``truss_model.py`` (``TrussBridge``) or
``design_checks.py`` (``line_load``, ``check_design``, ``design_search`` and
the spec data). The application itself does only display work: it converts
units for display, scales the displacements for drawing the deformed shape,
and picks each member's larger utilisation, max(U_yield, U_buckling), to
colour the member.
"""

import sys
from datetime import date

import numpy as np
from qtpy.QtCore import QObject, Qt, QThread, Signal
from qtpy.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QPlainTextEdit,
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

#: The deformed shape is drawn so that the largest displacement appears as
#: this fraction of the span (display only).
DEFORMATION_DISPLAY_FRACTION = 0.08


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig, self.canvas = _new_canvas()
        self.info = QLabel()
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.info)

    def update_view(self, p):
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
        # Display scaling only: the largest displacement is drawn as a fixed
        # fraction of the span.
        scale = DEFORMATION_DISPLAY_FRACTION * bridge.L / a_max if a_max > 0 else 0.0
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
        ax.text(0.01, 0.98, f"Deformation scale factor: ×{scale:,.0f}",
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Footbridge truss designer")
        self.resize(1400, 850)

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

        self.panel.changed.connect(self.refresh)
        self.design.load_design.connect(self._load_design)
        self.refresh()

    def refresh(self):
        p = self.panel.values()
        self.analysis.update_view(p)
        self.design.update_view(p)

    def _load_design(self, d):
        self.panel.set_design(d)
        self.tabs.setCurrentWidget(self.design)

    def closeEvent(self, event):
        self.design.shutdown()
        super().closeEvent(event)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
