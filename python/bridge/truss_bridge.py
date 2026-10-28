"""
Parametric truss bridge analysed with CALFEM bar2 elements.

The TrussBridge class generates the geometry and topology for a simply
supported planar truss bridge (Pratt, Howe or Warren), assembles and
solves the system using CALFEM and computes normal forces, stresses and
utilisation of the members.

Units: SI (m, N, Pa) throughout.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib import colors, cm

import calfem.core as cfc


class TrussBridge:
    """Parametric planar truss bridge.

    Parameters
    ----------
    width : float
        Total span of the bridge [m].
    height : float
        Height of the truss (distance between chords) [m].
    n_panels : int
        Number of panels along the span. Must be even for Pratt and Howe.
    truss_type : str
        'pratt', 'howe' or 'warren'.
    E : float
        Young's modulus [Pa].
    fy : float
        Yield strength used for the utilisation check [Pa].
    A_chord : float
        Cross-section area of top and bottom chord members [m^2].
    A_web : float
        Cross-section area of diagonals and verticals [m^2].
    deck_load : float
        Uniformly distributed deck load acting on the bottom chord [N/m]
        (positive downwards).
    """

    TRUSS_TYPES = ("pratt", "howe", "warren")

    def __init__(self, width=40.0, height=5.0, n_panels=8, truss_type="pratt",
                 E=210e9, fy=355e6, A_chord=8.0e-3, A_web=4.0e-3,
                 deck_load=50e3):
        self.width = width
        self.height = height
        self.n_panels = n_panels
        self.truss_type = truss_type.lower()
        self.E = E
        self.fy = fy
        self.A_chord = A_chord
        self.A_web = A_web
        self.deck_load = deck_load

        self.point_loads = []   # list of (node, Fx, Fy)

        self.coords = None
        self.elements = None    # (n_el, 2) node indices (0-based)
        self.groups = None      # member group for each element
        self.bottom_nodes = None
        self.top_nodes = None

        self.a = None
        self.r = None
        self.N = None
        self.solved = False

        self.generate()

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def _validate(self):
        if self.truss_type not in self.TRUSS_TYPES:
            raise ValueError(f"Unknown truss type '{self.truss_type}', "
                             f"choose one of {self.TRUSS_TYPES}")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if self.truss_type in ("pratt", "howe"):
            if self.n_panels < 2 or self.n_panels % 2 != 0:
                raise ValueError("Pratt and Howe trusses need an even "
                                 "number of panels >= 2")
        elif self.n_panels < 1:
            raise ValueError("n_panels must be >= 1")

    def generate(self):
        """Create node coordinates and element topology."""
        self._validate()

        n = self.n_panels
        dx = self.width / n
        coords = []
        elements = []
        groups = []

        def add_node(x, y):
            coords.append((x, y))
            return len(coords) - 1

        def add_element(n1, n2, group):
            elements.append((n1, n2))
            groups.append(group)

        bottom = [add_node(i * dx, 0.0) for i in range(n + 1)]

        if self.truss_type == "warren":
            top = [add_node((i + 0.5) * dx, self.height) for i in range(n)]

            for i in range(n):
                add_element(bottom[i], bottom[i + 1], "bottom")
            for i in range(n - 1):
                add_element(top[i], top[i + 1], "top")
            for i in range(n):
                add_element(bottom[i], top[i], "diagonal")
                add_element(top[i], bottom[i + 1], "diagonal")
        else:
            # Top nodes above interior bottom nodes, inclined end posts
            top = {i: add_node(i * dx, self.height) for i in range(1, n)}
            mid = n // 2

            for i in range(n):
                add_element(bottom[i], bottom[i + 1], "bottom")
            for i in range(1, n - 1):
                add_element(top[i], top[i + 1], "top")

            # End posts
            add_element(bottom[0], top[1], "diagonal")
            add_element(bottom[n], top[n - 1], "diagonal")

            # Verticals
            for i in range(1, n):
                add_element(bottom[i], top[i], "vertical")

            # Interior diagonals
            for i in range(1, mid):
                if self.truss_type == "pratt":
                    # Slope downwards towards midspan -> tension
                    add_element(top[i], bottom[i + 1], "diagonal")
                    add_element(top[n - i], bottom[n - i - 1], "diagonal")
                else:
                    # Howe: slope upwards towards midspan -> compression
                    add_element(bottom[i], top[i + 1], "diagonal")
                    add_element(bottom[n - i], top[n - i - 1], "diagonal")

            top = [top[i] for i in range(1, n)]

        self.coords = np.array(coords, dtype=float)
        self.elements = np.array(elements, dtype=int)
        self.groups = groups
        self.bottom_nodes = bottom
        self.top_nodes = top
        self.solved = False

    # ------------------------------------------------------------------
    # Model data
    # ------------------------------------------------------------------

    @property
    def n_nodes(self):
        return self.coords.shape[0]

    @property
    def n_elements(self):
        return self.elements.shape[0]

    @property
    def n_dofs(self):
        return 2 * self.n_nodes

    def node_dofs(self, node):
        """Return CALFEM (1-based) dofs for a 0-based node index."""
        return np.array([2 * node + 1, 2 * node + 2])

    @property
    def edof(self):
        return np.array([np.concatenate((self.node_dofs(n1), self.node_dofs(n2)))
                         for n1, n2 in self.elements])

    @property
    def areas(self):
        return np.array([self.A_chord if g in ("top", "bottom") else self.A_web
                         for g in self.groups])

    def element_coords(self):
        ex = self.coords[self.elements, 0]
        ey = self.coords[self.elements, 1]
        return ex, ey

    def add_point_load(self, node, Fx=0.0, Fy=0.0):
        """Add a nodal point load [N] (Fy positive upwards)."""
        self.point_loads.append((node, Fx, Fy))
        self.solved = False

    def load_vector(self):
        f = np.zeros((self.n_dofs, 1))

        # Distribute deck load to bottom chord nodes by tributary length
        dx = self.width / self.n_panels
        for i, node in enumerate(self.bottom_nodes):
            trib = dx / 2 if i in (0, self.n_panels) else dx
            f[2 * node + 1] -= self.deck_load * trib

        for node, Fx, Fy in self.point_loads:
            f[2 * node] += Fx
            f[2 * node + 1] += Fy

        return f

    def boundary_conditions(self):
        """Pinned support at left end, roller at right end."""
        left = self.bottom_nodes[0]
        right = self.bottom_nodes[-1]
        bc = np.array([2 * left + 1, 2 * left + 2, 2 * right + 2])
        return bc, np.zeros(bc.size)

    # ------------------------------------------------------------------
    # Solution
    # ------------------------------------------------------------------

    def solve(self):
        """Assemble and solve the truss using CALFEM bar2 elements.

        The geometry is regenerated so that parameter changes made after
        construction are taken into account.
        """
        self.generate()

        edof = self.edof
        ex, ey = self.element_coords()
        areas = self.areas

        K = np.zeros((self.n_dofs, self.n_dofs))
        for i in range(self.n_elements):
            Ke = cfc.bar2e(ex[i], ey[i], [self.E, areas[i]])
            cfc.assem(edof[i], K, Ke)

        f = self.load_vector()
        bc, bc_val = self.boundary_conditions()

        a, r = cfc.solveq(K, f, bc, bc_val)
        ed = cfc.extract_ed(edof, a)

        N = np.zeros(self.n_elements)
        for i in range(self.n_elements):
            es = cfc.bar2s(ex[i], ey[i], [self.E, areas[i]], ed[i])
            N[i] = np.asarray(es).ravel()[0]

        self.a = a.ravel()
        self.r = r.ravel()
        self.N = N
        self.solved = True
        return self.a, self.N

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _require_solution(self):
        if not self.solved:
            self.solve()

    @property
    def displacements(self):
        """Nodal displacements as (n_nodes, 2) array [m]."""
        self._require_solution()
        return self.a.reshape(-1, 2)

    @property
    def stresses(self):
        """Normal stresses in the members [Pa]."""
        self._require_solution()
        return self.N / self.areas

    @property
    def utilisation(self):
        """Utilisation |sigma| / fy for each member."""
        return np.abs(self.stresses) / self.fy

    @property
    def max_deflection(self):
        return np.max(np.abs(self.displacements[:, 1]))

    @property
    def reactions(self):
        """Support reactions (left Rx, left Ry, right Ry) [N]."""
        self._require_solution()
        bc, _ = self.boundary_conditions()
        return self.r[bc - 1]

    def summary(self):
        self._require_solution()
        sigma = self.stresses
        util = self.utilisation
        total_load = self.deck_load * self.width - sum(p[2] for p in self.point_loads)
        lines = [
            f"Truss bridge ({self.truss_type.capitalize()})",
            f"  Span x height        : {self.width:.2f} m x {self.height:.2f} m",
            f"  Panels               : {self.n_panels}",
            f"  Nodes / elements     : {self.n_nodes} / {self.n_elements}",
            f"  Total vertical load  : {total_load / 1e3:.1f} kN",
            f"  Reactions (Rx,Ry,Ry) : " + ", ".join(f"{v / 1e3:.1f}" for v in self.reactions) + " kN",
            f"  Max deflection       : {self.max_deflection * 1e3:.2f} mm "
            f"(L/{self.width / self.max_deflection:.0f})",
            f"  Max tension          : {self.N.max() / 1e3:.1f} kN, "
            f"sigma = {sigma.max() / 1e6:.1f} MPa",
            f"  Max compression      : {self.N.min() / 1e3:.1f} kN, "
            f"sigma = {sigma.min() / 1e6:.1f} MPa",
            f"  Max utilisation      : {util.max() * 100:.1f} % (element {util.argmax()})",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def _segments(self, coords):
        return coords[self.elements]

    def plot_geometry(self, ax=None, show_numbers=False):
        ax = ax or plt.gca()
        lc = LineCollection(self._segments(self.coords), colors="k", linewidths=1.5)
        ax.add_collection(lc)
        ax.plot(self.coords[:, 0], self.coords[:, 1], "o", color="k", ms=3)
        if show_numbers:
            for i, (n1, n2) in enumerate(self.elements):
                xm, ym = self.coords[[n1, n2]].mean(axis=0)
                ax.text(xm, ym, str(i), fontsize=7, color="tab:blue",
                        ha="center", va="center")
        self._plot_supports(ax)
        self._format_axes(ax, "Geometry")
        return ax

    def plot_deformed(self, ax=None, scale=None):
        self._require_solution()
        ax = ax or plt.gca()
        if scale is None:
            scale = 0.1 * self.height / max(self.max_deflection, 1e-12)
        deformed = self.coords + scale * self.displacements
        ax.add_collection(LineCollection(self._segments(self.coords), colors="0.75",
                                         linewidths=1.0, linestyles="--"))
        ax.add_collection(LineCollection(self._segments(deformed), colors="tab:blue",
                                         linewidths=1.8))
        self._plot_supports(ax)
        self._format_axes(ax, f"Deformed shape (scale {scale:.0f}x)")
        return ax

    def plot_normal_forces(self, ax=None):
        self._require_solution()
        ax = ax or plt.gca()
        Nk = self.N / 1e3
        nmax = max(np.abs(Nk).max(), 1e-12)
        norm = colors.TwoSlopeNorm(vmin=-nmax, vcenter=0.0, vmax=nmax)
        lc = LineCollection(self._segments(self.coords), cmap="coolwarm_r",
                            norm=norm, linewidths=4)
        lc.set_array(Nk)
        ax.add_collection(lc)
        plt.colorbar(lc, ax=ax, label="Normal force [kN] (+ tension)",
                     orientation="horizontal", pad=0.15, shrink=0.8)
        self._plot_supports(ax)
        self._format_axes(ax, "Normal forces")
        return ax

    def plot_utilisation(self, ax=None):
        self._require_solution()
        ax = ax or plt.gca()
        util = self.utilisation * 100
        cols = ["tab:red" if u > 100 else "tab:green" for u in util]
        ax.bar(np.arange(self.n_elements), util, color=cols)
        ax.axhline(100, color="k", ls="--", lw=1)
        ax.set_xlabel("Element")
        ax.set_ylabel("Utilisation [%]")
        ax.set_title("Member utilisation (|σ| / fy)")
        return ax

    def _plot_supports(self, ax):
        s = 0.04 * self.width
        for node, filled in ((self.bottom_nodes[0], True), (self.bottom_nodes[-1], False)):
            x, y = self.coords[node]
            tri = plt.Polygon([[x, y], [x - s / 2, y - s], [x + s / 2, y - s]],
                              closed=True, fc="0.6" if filled else "white", ec="k")
            ax.add_patch(tri)

    def _format_axes(self, ax, title):
        ax.set_aspect("equal")
        ax.autoscale_view()
        margin = 0.08 * self.width
        ax.set_xlim(-margin, self.width + margin)
        ax.set_ylim(-0.15 * self.width, self.height + 0.08 * self.width)
        ax.set_title(title)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")

    def plot_all(self):
        fig, axes = plt.subplots(2, 2, figsize=(14, 8))
        self.plot_geometry(axes[0, 0], show_numbers=True)
        self.plot_deformed(axes[0, 1])
        self.plot_normal_forces(axes[1, 0])
        self.plot_utilisation(axes[1, 1])
        fig.suptitle(f"{self.truss_type.capitalize()} truss bridge, "
                     f"L = {self.width} m, h = {self.height} m")
        fig.tight_layout()
        return fig


if __name__ == "__main__":
    for truss_type in TrussBridge.TRUSS_TYPES:
        bridge = TrussBridge(width=40.0, height=5.0, n_panels=8,
                             truss_type=truss_type, deck_load=50e3)
        bridge.solve()
        print(bridge.summary())
        print()

    bridge = TrussBridge(width=40.0, height=5.0, n_panels=8, truss_type="pratt")
    bridge.add_point_load(bridge.bottom_nodes[4], Fy=-200e3)
    bridge.solve()
    bridge.plot_all()
    plt.show()
