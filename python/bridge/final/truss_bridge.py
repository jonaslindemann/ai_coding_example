# -*- coding: utf-8 -*-
"""
Parametric 2D truss bridge analysed with CALFEM bar2 elements.

The bridge consists of a bottom chord (the deck), a top chord, vertical
posts and diagonals. The layout of the diagonals is selected with
``truss_type``:

    "pratt"  - diagonals slope down towards the centre (tension diagonals)
    "howe"   - diagonals slope up towards the centre (compression diagonals)
    "warren" - alternating diagonals, no vertical posts

The bridge is simply supported: pinned at the bottom-left node and
roller-supported (vertical only) at the bottom-right node. A uniform deck
load is applied as point loads on the bottom chord nodes.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import calfem.core as cfc
import calfem.vis_mpl as cfv


class TrussBridge:
    """
    Parametric truss bridge model.

    Parameters
    ----------
    width : float
        Total span of the bridge (m).
    height : float
        Height of the truss, distance between bottom and top chord (m).
    n_panels : int
        Number of panels along the span. Must be even for symmetric
        Pratt/Howe layouts.
    truss_type : str
        "pratt", "howe" or "warren".
    E : float
        Young's modulus (Pa).
    A_chord : float
        Cross-section area of top and bottom chords (m^2).
    A_vertical : float
        Cross-section area of vertical posts (m^2).
    A_diagonal : float
        Cross-section area of diagonals (m^2).
    deck_load : float
        Uniformly distributed deck load acting downwards (N/m).
    """

    CHORD, VERTICAL, DIAGONAL = 0, 1, 2

    def __init__(
        self,
        width=40.0,
        height=5.0,
        n_panels=8,
        truss_type="pratt",
        E=210e9,
        A_chord=100e-4,
        A_vertical=40e-4,
        A_diagonal=60e-4,
        deck_load=50e3,
    ):
        if n_panels < 2:
            raise ValueError("n_panels must be at least 2.")
        if truss_type not in ("pratt", "howe", "warren"):
            raise ValueError(f"Unknown truss_type '{truss_type}'.")
        if truss_type in ("pratt", "howe") and n_panels % 2 != 0:
            raise ValueError("Pratt and Howe trusses require an even n_panels.")

        self.width      = width
        self.height     = height
        self.n_panels   = n_panels
        self.truss_type = truss_type
        self.E          = E
        self.A_chord    = A_chord
        self.A_vertical = A_vertical
        self.A_diagonal = A_diagonal
        self.deck_load  = deck_load

        # Geometry/topology - populated by build()
        self.coords   = None   # (n_nodes, 2)
        self.elements = []     # list of (node_i, node_j, member_group)
        self.edof     = None
        self.ex       = None
        self.ey       = None

        # Results - populated by solve()
        self.a = None          # global displacement vector
        self.r = None          # reaction forces
        self.normal_forces = None

        self.build()

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    @property
    def panel_length(self):
        return self.width / self.n_panels

    @property
    def n_nodes(self):
        return self.coords.shape[0]

    def bottom_node(self, i):
        """Index of bottom chord node i (0..n_panels)."""
        return i

    def top_node(self, i):
        """
        Index of top chord node i.

        Pratt/Howe: top nodes sit above bottom nodes 1..n_panels-1.
        Warren: top nodes sit above the panel midpoints 0..n_panels-1.
        """
        return self.n_panels + 1 + i

    def build(self):
        """Generate nodes, elements and topology for the chosen truss type."""
        n, dx, h = self.n_panels, self.panel_length, self.height

        bottom = [[i * dx, 0.0] for i in range(n + 1)]
        if self.truss_type == "warren":
            top = [[(i + 0.5) * dx, h] for i in range(n)]
        else:
            top = [[i * dx, h] for i in range(1, n)]
        self.coords = np.array(bottom + top)

        self.elements = []
        add = self.elements.append
        B, T = self.bottom_node, self.top_node

        # Bottom chord
        for i in range(n):
            add((B(i), B(i + 1), self.CHORD))

        if self.truss_type == "warren":
            for i in range(n - 1):
                add((T(i), T(i + 1), self.CHORD))
            for i in range(n):
                add((B(i), T(i), self.DIAGONAL))
                add((T(i), B(i + 1), self.DIAGONAL))
        else:
            # Top chord, including inclined end posts
            add((B(0), T(0), self.CHORD))
            for i in range(n - 2):
                add((T(i), T(i + 1), self.CHORD))
            add((T(n - 2), B(n), self.CHORD))

            # Vertical posts (top node k sits above bottom node k+1)
            for k in range(n - 1):
                add((B(k + 1), T(k), self.VERTICAL))

            # Interior diagonals
            mid = n // 2
            for p in range(1, n - 1):        # panels between bottom nodes p and p+1
                left_half = p < mid
                if self.truss_type == "pratt":
                    # Top towards the support, bottom towards the centre
                    nodes = (T(p - 1), B(p + 1)) if left_half else (B(p), T(p))
                else:  # howe
                    nodes = (B(p), T(p)) if left_half else (T(p - 1), B(p + 1))
                add((*nodes, self.DIAGONAL))

        # Topology: 2 dofs per node, 1-based as CALFEM expects
        self.edof = np.array([
            [2 * i + 1, 2 * i + 2, 2 * j + 1, 2 * j + 2]
            for i, j, _ in self.elements
        ])
        self.ex = np.array([self.coords[[i, j], 0] for i, j, _ in self.elements])
        self.ey = np.array([self.coords[[i, j], 1] for i, j, _ in self.elements])

    def element_area(self, group):
        return {
            self.CHORD: self.A_chord,
            self.VERTICAL: self.A_vertical,
            self.DIAGONAL: self.A_diagonal,
        }[group]

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def solve(self):
        """Assemble, apply loads and boundary conditions, and solve."""
        n_dofs = 2 * self.n_nodes
        K = np.zeros((n_dofs, n_dofs))
        f = np.zeros((n_dofs, 1))

        for (i, j, group), eltopo, elx, ely in zip(
            self.elements, self.edof, self.ex, self.ey
        ):
            Ke = cfc.bar2e(elx, ely, [self.E, self.element_area(group)])
            cfc.assem(eltopo, K, Ke)

        # Deck load lumped to bottom chord nodes (half load at the ends)
        P = self.deck_load * self.panel_length
        for i in range(self.n_panels + 1):
            factor = 0.5 if i in (0, self.n_panels) else 1.0
            f[2 * self.bottom_node(i) + 1] -= factor * P

        # Pinned left support, roller at right support (1-based dofs)
        left, right = self.bottom_node(0), self.bottom_node(self.n_panels)
        bc = np.array([2 * left + 1, 2 * left + 2, 2 * right + 2])

        self.a, self.r = cfc.solveq(K, f, bc)

        ed = cfc.extract_eldisp(self.edof, self.a)
        self.normal_forces = np.array([
            cfc.bar2s(elx, ely, [self.E, self.element_area(group)], eld)[0, 0]
            for (_, _, group), elx, ely, eld in zip(self.elements, self.ex, self.ey, ed)
        ])
        self.ed = ed

    @property
    def max_deflection(self):
        return np.max(np.abs(self.a[1::2]))

    def stresses(self):
        areas = np.array([self.element_area(g) for _, _, g in self.elements])
        return self.normal_forces / areas

    def utilisation(self, fy):
        """
        Utilisation ratio |sigma| / fy for each element.

        Only the material strength is checked; buckling of compression
        members is not considered.
        """
        return np.abs(self.stresses()) / fy

    def summary(self):
        s = self.stresses()
        print(f"Truss type        : {self.truss_type}")
        print(f"Span x height     : {self.width:.2f} m x {self.height:.2f} m")
        print(f"Panels            : {self.n_panels}")
        print(f"Nodes / elements  : {self.n_nodes} / {len(self.elements)}")
        print(f"Total deck load   : {self.deck_load * self.width / 1e3:.1f} kN")
        print(f"Max deflection    : {self.max_deflection * 1e3:.2f} mm")
        print(f"Max tension       : {self.normal_forces.max() / 1e3:.1f} kN "
              f"({s.max() / 1e6:.1f} MPa)")
        print(f"Max compression   : {self.normal_forces.min() / 1e3:.1f} kN "
              f"({s.min() / 1e6:.1f} MPa)")

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def plot(self, scale=None):
        """Plot geometry, deformed shape and normal forces."""
        fig, axes = plt.subplots(3, 1, figsize=(10, 10))

        plt.sca(axes[0])
        cfv.eldraw2(self.ex, self.ey, [1, 2, 1])
        axes[0].plot(self.coords[:, 0], self.coords[:, 1], "ko", ms=4)
        axes[0].set_title(f"{self.truss_type.capitalize()} truss geometry")

        if self.a is None:
            self.solve()

        plt.sca(axes[1])
        if scale is None:
            scale = 0.1 * self.height / max(self.max_deflection, 1e-12)
        cfv.eldraw2(self.ex, self.ey, [2, 1, 0])
        cfv.eldisp2(self.ex, self.ey, self.ed, [1, 4, 0], scale)
        axes[1].set_title(
            f"Deformed shape (scale {scale:.0f}x, "
            f"max {self.max_deflection * 1e3:.2f} mm)"
        )

        ax = axes[2]
        N = self.normal_forces / 1e3
        nmax = np.max(np.abs(N))
        norm = mcolors.TwoSlopeNorm(vmin=-nmax, vcenter=0.0, vmax=nmax)
        cmap = plt.get_cmap("coolwarm")
        for elx, ely, Ni in zip(self.ex, self.ey, N):
            ax.plot(elx, ely, color=cmap(norm(Ni)), lw=3)
        fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax,
                     orientation="horizontal", fraction=0.08, pad=0.15,
                     label="Normal force (kN), + tension")
        ax.set_title("Normal forces")

        for ax in axes:
            ax.set_aspect("equal")
            ax.set_xlim(-0.05 * self.width, 1.05 * self.width)

        fig.tight_layout()
        plt.show()


def main():
    for truss_type in ("pratt", "howe", "warren"):
        bridge = TrussBridge(
            width=40.0,
            height=5.0,
            n_panels=8,
            truss_type=truss_type,
        )
        bridge.solve()
        bridge.summary()
        print()

    bridge = TrussBridge(width=40.0, height=5.0, n_panels=8, truss_type="pratt")
    bridge.solve()
    bridge.plot()


if __name__ == "__main__":
    main()
