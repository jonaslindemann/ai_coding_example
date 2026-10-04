# -*- coding: utf-8 -*-
"""
Parametric 2D concrete wall analysed with CALFEM plani4e elements.

The wall is modelled in plane stress with 4-node isoparametric quadrilateral
elements on a structured grid. Rectangular openings (windows and doors) are
cut out of the grid; the grid lines are snapped to the opening edges so the
openings are represented exactly.

Loading:
    - vertical line load on the top edge (e.g. floor slab above)
    - horizontal line load on the top edge (e.g. wind / stabilising force)
    - self weight (optional)

Boundary conditions (bottom edge):
    - "fixed"  - fully supported along the whole bottom edge, except where a
                 door interrupts it (set_fully_supported)
    - "free"   - freely supported on discrete bearings at the ends and/or at
                 specified positions. The leftmost bearing is pinned, the
                 others are rollers (set_freely_supported)

Results include displacements, element stresses, von Mises stress and the
principal stresses with their directions.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection, PolyCollection
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
import calfem.core as cfc


class Opening:
    """Rectangular opening with lower-left corner (x, y), width w and height h."""

    def __init__(self, x, y, w, h, kind="window"):
        self.x, self.y, self.w, self.h, self.kind = x, y, w, h, kind

    @property
    def x2(self):
        return self.x + self.w

    @property
    def y2(self):
        return self.y + self.h

    def contains(self, px, py):
        return (self.x < px < self.x2) and (self.y < py < self.y2)

    def overlaps(self, other):
        return not (self.x2 <= other.x or other.x2 <= self.x
                    or self.y2 <= other.y or other.y2 <= self.y)

    def __repr__(self):
        return (f"{self.kind}(x={self.x:.2f}, y={self.y:.2f}, "
                f"w={self.w:.2f}, h={self.h:.2f})")


class ConcreteWall:
    """
    Parametric concrete wall with openings.

    Parameters
    ----------
    width : float
        Total wall width (m).
    height : float
        Total wall height (m).
    thickness : float
        Wall thickness (m).
    E : float
        Young's modulus (Pa).
    nu : float
        Poisson's ratio.
    density : float
        Density (kg/m^3), used for self weight.
    el_size : float
        Target element size (m).
    top_load : float
        Vertical line load on the top edge, acting downwards (N/m).
    horizontal_load : float
        Horizontal line load on the top edge, acting in +x (N/m).
    self_weight : bool
        Include self weight as a body force.
    """

    G = 9.81

    def __init__(
        self,
        width=6.0,
        height=3.0,
        thickness=0.2,
        E=33e9,
        nu=0.2,
        density=2500.0,
        el_size=0.1,
        top_load=100e3,
        horizontal_load=20e3,
        self_weight=True,
    ):
        self.width           = width
        self.height          = height
        self.thickness       = thickness
        self.E               = E
        self.nu              = nu
        self.density         = density
        self.el_size         = el_size
        self.top_load        = top_load
        self.horizontal_load = horizontal_load
        self.self_weight     = self_weight

        self.openings = []

        # Supports - see set_fully_supported() / set_freely_supported()
        self.support_type      = "fixed"
        self.support_positions = []
        self.support_ends      = True
        self.support_length    = 0.2

        # Mesh - populated by build()
        self.coords = None    # (n_nodes, 2)
        self.topo   = None    # (n_elements, 4) node indices, counter-clockwise
        self.edof   = None
        self.ex     = None
        self.ey     = None

        # Results - populated by solve()
        self.a  = None
        self.r  = None
        self.ed = None
        self.es = None        # element stresses [sigx, sigy, tauxy] (centroid)

    # ------------------------------------------------------------------
    # Openings
    # ------------------------------------------------------------------

    def add_opening(self, x, y, w, h, kind="window"):
        """Add a rectangular opening. Returns the created Opening."""
        op = Opening(x, y, w, h, kind)
        if w <= 0 or h <= 0:
            raise ValueError(f"{op}: width and height must be positive.")
        if x <= 0 or op.x2 >= self.width:
            raise ValueError(f"{op}: must lie strictly inside the wall horizontally.")
        if y < 0 or op.y2 >= self.height:
            raise ValueError(f"{op}: must lie below the top edge of the wall.")
        for other in self.openings:
            if op.overlaps(other):
                raise ValueError(f"{op} overlaps {other}.")
        self.openings.append(op)
        try:
            self._check_supports()
        except ValueError:
            self.openings.remove(op)
            raise
        self._invalidate()
        return op

    def add_window(self, x, sill_height, w, h):
        """Add a window with lower-left corner at (x, sill_height)."""
        if sill_height <= 0:
            raise ValueError("Window sill height must be > 0, use add_door() instead.")
        return self.add_opening(x, sill_height, w, h, kind="window")

    def add_door(self, x, w, h):
        """Add a door starting at the bottom edge of the wall."""
        return self.add_opening(x, 0.0, w, h, kind="door")

    def clear_openings(self):
        self.openings = []
        self._invalidate()

    # ------------------------------------------------------------------
    # Supports
    # ------------------------------------------------------------------

    def set_fully_supported(self):
        """Support the entire bottom edge in both directions (default)."""
        self.support_type = "fixed"
        self._invalidate()

    def set_freely_supported(self, positions=(), ends=True, support_length=0.2):
        """
        Support the wall on discrete bearings along the bottom edge.

        Parameters
        ----------
        positions : sequence of float
            x-coordinates of the centres of intermediate supports (m).
        ends : bool
            Add supports at the left and right ends of the wall.
        support_length : float
            Length of each bearing (m). A finite length avoids the stress
            singularity of a true point support.

        The leftmost bearing is pinned (x and y fixed), all others are
        rollers (only y fixed), so the wall can expand freely.
        """
        if support_length <= 0:
            raise ValueError("support_length must be positive.")
        previous = (self.support_type, self.support_positions,
                    self.support_ends, self.support_length)
        self.support_type      = "free"
        self.support_positions = sorted(positions)
        self.support_ends      = ends
        self.support_length    = support_length
        try:
            self._check_supports()
        except ValueError:
            (self.support_type, self.support_positions,
             self.support_ends, self.support_length) = previous
            raise
        self._invalidate()

    def support_segments(self):
        """
        Supported intervals on the bottom edge.

        Returns
        -------
        list of (x1, x2, pinned)
            pinned is True if both x and y are fixed, False for a roller.
        """
        doors = sorted((o.x, o.x2) for o in self.openings if o.kind == "door")

        if self.support_type == "fixed":
            segments, x = [], 0.0
            for d1, d2 in doors:
                segments.append((x, d1, True))
                x = d2
            segments.append((x, self.width, True))
            return segments

        L, W = self.support_length, self.width
        intervals = [(max(0.0, p - L / 2), min(W, p + L / 2))
                     for p in self.support_positions]
        if self.support_ends:
            intervals += [(0.0, min(L, W)), (max(0.0, W - L), W)]
        intervals.sort()
        return [(x1, x2, i == 0) for i, (x1, x2) in enumerate(intervals)]

    def _check_supports(self):
        segments = self.support_segments()
        if not segments:
            raise ValueError("No supports defined.")
        for x1, x2, _ in segments:
            for o in self.openings:
                if o.kind == "door" and x1 < o.x2 and o.x < x2:
                    raise ValueError(
                        f"Support [{x1:.2f}, {x2:.2f}] lies under {o}.")

    def _invalidate(self):
        self.coords = None
        self.a = None

    # ------------------------------------------------------------------
    # Mesh
    # ------------------------------------------------------------------

    def _grid_lines(self, length, breaks):
        """Grid coordinates including all break points, spaced <= el_size."""
        pts = np.unique(np.round([0.0, length, *breaks], 10))
        lines = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            n = max(1, int(np.ceil((b - a) / self.el_size - 1e-9)))
            lines.extend(np.linspace(a, b, n + 1)[1:])
        return np.array(lines)

    def build(self):
        """Generate a structured quad mesh with the openings removed."""
        self._check_supports()
        x_breaks = [c for o in self.openings for c in (o.x, o.x2)]
        x_breaks += [c for x1, x2, _ in self.support_segments() for c in (x1, x2)]
        xs = self._grid_lines(self.width, x_breaks)
        ys = self._grid_lines(self.height, [c for o in self.openings for c in (o.y, o.y2)])
        nx, ny = len(xs), len(ys)

        def node(i, j):
            return j * nx + i

        quads = []
        for j in range(ny - 1):
            yc = 0.5 * (ys[j] + ys[j + 1])
            for i in range(nx - 1):
                xc = 0.5 * (xs[i] + xs[i + 1])
                if any(o.contains(xc, yc) for o in self.openings):
                    continue
                quads.append([node(i, j), node(i + 1, j),
                              node(i + 1, j + 1), node(i, j + 1)])
        quads = np.array(quads)

        # Remove nodes that are not used by any element and renumber
        X, Y = np.meshgrid(xs, ys)
        all_coords = np.column_stack([X.ravel(), Y.ravel()])
        used = np.unique(quads)
        renumber = -np.ones(nx * ny, dtype=int)
        renumber[used] = np.arange(len(used))

        self.coords = all_coords[used]
        self.topo   = renumber[quads]

        dofs = np.column_stack([2 * self.topo + 1, 2 * self.topo + 2])  # 1-based
        self.edof = dofs[:, [0, 4, 1, 5, 2, 6, 3, 7]]
        self.ex = self.coords[self.topo, 0]
        self.ey = self.coords[self.topo, 1]

    @property
    def n_nodes(self):
        return self.coords.shape[0]

    @property
    def n_elements(self):
        return self.topo.shape[0]

    def _edge_nodes(self, y_edge):
        """Node indices on a horizontal edge y = y_edge, sorted by x."""
        idx = np.where(np.isclose(self.coords[:, 1], y_edge))[0]
        return idx[np.argsort(self.coords[idx, 0])]

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _support_nodes(self):
        """Bottom edge nodes with fixed x and fixed y displacement."""
        bottom = self._edge_nodes(0.0)
        x = self.coords[bottom, 0]
        fix_x, fix_y = [], []
        tol = 1e-9
        for x1, x2, pinned in self.support_segments():
            nodes = bottom[(x >= x1 - tol) & (x <= x2 + tol)]
            fix_y.append(nodes)
            if pinned:
                fix_x.append(nodes)
        empty = np.array([], dtype=int)
        return (np.concatenate(fix_x) if fix_x else empty,
                np.concatenate(fix_y) if fix_y else empty)

    @property
    def ep(self):
        return [1, self.thickness, 2]   # plane stress, 2x2 Gauss points

    @property
    def D(self):
        return cfc.hooke(1, self.E, self.nu)

    def solve(self):
        """Assemble, apply loads and boundary conditions, and solve."""
        if self.coords is None:
            self.build()

        n_dofs = 2 * self.n_nodes
        f = np.zeros(n_dofs)
        D, ep = self.D, self.ep
        eq = [0.0, -self.density * self.G] if self.self_weight else [0.0, 0.0]

        # Elements on the structured grid only differ in size, so element
        # matrices are cached on (dx, dy) to avoid recomputing them.
        cache = {}
        rows, cols, vals = [], [], []
        for dofs, elx, ely in zip(self.edof, self.ex, self.ey):
            key = (round(elx[1] - elx[0], 9), round(ely[2] - ely[1], 9))
            if key not in cache:
                Ke, fe = cfc.plani4e(elx, ely, ep, D, eq)
                cache[key] = (np.asarray(Ke), np.asarray(fe).ravel())
            Ke, fe = cache[key]
            idx = dofs - 1
            rows.append(np.repeat(idx, 8))
            cols.append(np.tile(idx, 8))
            vals.append(Ke.ravel())
            f[idx] += fe

        K = coo_matrix(
            (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
            shape=(n_dofs, n_dofs),
        ).tocsr()

        # Line loads on the top edge, consistent (linear) nodal loads
        top = self._edge_nodes(self.height)
        for n1, n2 in zip(top[:-1], top[1:]):
            L = self.coords[n2, 0] - self.coords[n1, 0]
            for n in (n1, n2):
                f[2 * n]     += 0.5 * L * self.horizontal_load
                f[2 * n + 1] -= 0.5 * L * self.top_load

        # Supports on the bottom edge
        fix_x, fix_y = self._support_nodes()
        fixed = np.unique(np.concatenate([2 * fix_x, 2 * fix_y + 1]))
        free = np.setdiff1d(np.arange(n_dofs), fixed)

        a = np.zeros(n_dofs)
        a[free] = spsolve(K[free][:, free], f[free])
        r = K @ a - f

        self.a = a.reshape(-1, 1)
        self.r = r.reshape(-1, 1)
        self.ed = cfc.extract_eldisp(self.edof, self.a)

        # Element stresses, mean of the Gauss point values
        self.es = np.array([
            cfc.plani4s(elx, ely, ep, D, eld)[0].mean(axis=0)
            for elx, ely, eld in zip(self.ex, self.ey, self.ed)
        ])

    # ------------------------------------------------------------------
    # Stress measures
    # ------------------------------------------------------------------

    def _ensure_solved(self):
        if self.a is None:
            self.solve()

    @property
    def von_mises(self):
        """Element von Mises stress, plane stress (Pa)."""
        self._ensure_solved()
        sx, sy, txy = self.es.T
        return np.sqrt(sx**2 + sy**2 - sx * sy + 3 * txy**2)

    @property
    def principal_stresses(self):
        """
        Element principal stresses.

        Returns
        -------
        s1, s2 : ndarray
            Major and minor principal stress (Pa), s1 >= s2.
        theta : ndarray
            Angle of the s1 direction to the x-axis (rad).
        """
        self._ensure_solved()
        sx, sy, txy = self.es.T
        centre = 0.5 * (sx + sy)
        radius = np.sqrt((0.5 * (sx - sy))**2 + txy**2)
        theta = 0.5 * np.arctan2(2 * txy, sx - sy)
        return centre + radius, centre - radius, theta

    def nodal_values(self, element_values):
        """Average element values to the nodes for smooth contour plots."""
        total = np.zeros(self.n_nodes)
        count = np.zeros(self.n_nodes)
        for nodes, v in zip(self.topo, element_values):
            total[nodes] += v
            count[nodes] += 1
        return total / count

    @property
    def max_displacement(self):
        self._ensure_solved()
        u = self.a.reshape(-1, 2)
        return np.max(np.linalg.norm(u, axis=1))

    def summary_text(self):
        """Summary of model and results as a multi-line string."""
        self._ensure_solved()
        s1, s2, _ = self.principal_stresses
        bottom = self._edge_nodes(0.0)
        lines = [
            f"Wall (w x h x t)    : {self.width:.2f} x {self.height:.2f} "
            f"x {self.thickness:.2f} m",
            f"Openings            : {len(self.openings)}",
        ]
        lines += [f"    {o}" for o in self.openings]
        if self.support_type == "fixed":
            lines.append("Supports            : fully supported bottom edge")
        else:
            lines.append(f"Supports            : freely supported, "
                         f"bearing length {self.support_length:.2f} m")
            lines += [f"    {'pinned' if pinned else 'roller'} [{x1:.2f}, {x2:.2f}]"
                      for x1, x2, pinned in self.support_segments()]
        lines += [
            f"Nodes / elements    : {self.n_nodes} / {self.n_elements}",
            f"Top load (vert/hor) : {self.top_load / 1e3:.1f} / "
            f"{self.horizontal_load / 1e3:.1f} kN/m",
            f"Sum of reactions    : Rx = {self.r[2 * bottom, 0].sum() / 1e3:.1f} kN, "
            f"Ry = {self.r[2 * bottom + 1, 0].sum() / 1e3:.1f} kN",
            f"Max displacement    : {self.max_displacement * 1e3:.3f} mm",
            f"Max von Mises       : {self.von_mises.max() / 1e6:.2f} MPa",
            f"Max principal (s1)  : {s1.max() / 1e6:.2f} MPa (tension)",
            f"Min principal (s2)  : {s2.min() / 1e6:.2f} MPa (compression)",
        ]
        return "\n".join(lines)

    def summary(self):
        print(self.summary_text())

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def _triangulation(self, displaced=False, scale=1.0):
        """Split each quad into two triangles for matplotlib's tri plotting."""
        xy = self.coords
        if displaced:
            xy = xy + scale * self.a.reshape(-1, 2)
        tris = np.vstack([self.topo[:, [0, 1, 2]], self.topo[:, [0, 2, 3]]])
        return mtri.Triangulation(xy[:, 0], xy[:, 1], tris)

    def _decorate(self, ax, title):
        ax.plot([0, self.width, self.width, 0, 0],
                [0, 0, self.height, self.height, 0], "k-", lw=0.8)
        for o in self.openings:
            ax.add_patch(Rectangle((o.x, o.y), o.w, o.h, fill=False,
                                   ec="k", lw=0.8))
        # Supports: thick line along each bearing, plus a triangle marker
        # for discrete bearings (filled = pinned, open = roller)
        for x1, x2, pinned in self.support_segments():
            ax.plot([x1, x2], [0, 0], color="k", lw=4,
                    solid_capstyle="butt", zorder=0)
            if self.support_type == "free":
                ax.plot(0.5 * (x1 + x2), -0.025 * max(self.width, self.height),
                        marker="^", ms=9, mec="k", mfc="k" if pinned else "w")
        ax.set_aspect("equal")
        margin = 0.05 * max(self.width, self.height)
        ax.set_xlim(-margin, self.width + margin)
        ax.set_ylim(-margin, self.height + margin)
        ax.set_title(title)

    def _contour(self, ax, values, title, label, cmap="viridis", norm=None,
                 levels=20):
        tri = self._triangulation()
        nodal = self.nodal_values(values) / 1e6
        if norm is not None:
            levels = np.linspace(norm.vmin, norm.vmax, levels + 1)
        cs = ax.tricontourf(tri, nodal, levels=levels, cmap=cmap, norm=norm)
        ax.figure.colorbar(cs, ax=ax, label=label, shrink=0.8)
        self._decorate(ax, title)
        return cs

    def plot_mesh(self, ax=None):
        if self.coords is None:
            self.build()
        ax = ax or plt.figure(figsize=(9, 5)).gca()
        polys = PolyCollection(np.stack([self.ex, self.ey], axis=-1),
                               facecolors="lightgrey", edgecolors="grey", lw=0.3)
        ax.add_collection(polys)
        self._decorate(ax, f"Mesh: {self.n_elements} plani4e elements")
        return ax

    def plot_deformed(self, ax=None, scale=None):
        self._ensure_solved()
        ax = ax or plt.figure(figsize=(9, 5)).gca()
        if scale is None:
            scale = 0.05 * max(self.width, self.height) / max(self.max_displacement, 1e-12)
        u = np.linalg.norm(self.a.reshape(-1, 2), axis=1) * 1e3
        tri = self._triangulation(displaced=True, scale=scale)
        cs = ax.tripcolor(tri, u, shading="gouraud", cmap="viridis")
        ax.figure.colorbar(cs, ax=ax, label="|u| (mm)", shrink=0.8)
        self._decorate(ax, f"Deformed shape (scale {scale:.0f}x, "
                           f"max {self.max_displacement * 1e3:.3f} mm)")
        return ax

    def plot_von_mises(self, ax=None):
        ax = ax or plt.figure(figsize=(9, 5)).gca()
        self._contour(ax, self.von_mises, "von Mises stress",
                      "$\\sigma_{vM}$ (MPa)", cmap="inferno")
        return ax

    def plot_principal_stress(self, which=1, ax=None):
        """
        Contour plot of the major (which=1) or minor (which=2) principal
        stress on a diverging scale: red = tension, blue = compression.
        """
        ax = ax or plt.figure(figsize=(9, 5)).gca()
        s = self.principal_stresses[0 if which == 1 else 1]
        nodal = self.nodal_values(s) / 1e6
        eps = 1e-6 * max(abs(nodal).max(), 1e-12)
        norm = mcolors.TwoSlopeNorm(vmin=min(nodal.min(), -eps), vcenter=0.0,
                                    vmax=max(nodal.max(), eps))
        name = "Major" if which == 1 else "Minor"
        self._contour(ax, s, f"{name} principal stress $\\sigma_{which}$",
                      f"$\\sigma_{which}$ (MPa)", cmap="RdBu_r", norm=norm)
        return ax

    def plot_principal_directions(self, ax=None, spacing=None):
        """Draw principal stress crosses at a subset of element centroids."""
        ax = ax or plt.figure(figsize=(9, 5)).gca()
        s1, s2, theta = self.principal_stresses
        spacing = spacing or max(self.width, self.height) / 25
        xc, yc = self.ex.mean(axis=1), self.ey.mean(axis=1)

        # Pick one element per spacing x spacing cell
        cell = np.column_stack([np.floor(xc / spacing), np.floor(yc / spacing)])
        _, pick = np.unique(cell, axis=0, return_index=True)

        # Scale on the 95th percentile so corner peaks don't shrink the rest
        sref = np.percentile(np.abs(np.concatenate([s1, s2])), 95)
        length = 0.9 * spacing / max(sref, 1e-12)
        for s, ang in ((s1, theta), (s2, theta + np.pi / 2)):
            for sign, color in ((1, "tab:red"), (-1, "tab:blue")):
                sel = pick[np.sign(s[pick]) == sign]
                mag = np.minimum(np.abs(s[sel]), sref)
                d = 0.5 * length * mag[:, None] * np.column_stack(
                    [np.cos(ang[sel]), np.sin(ang[sel])])
                c = np.column_stack([xc[sel], yc[sel]])
                ax.add_collection(LineCollection(
                    np.stack([c - d, c + d], axis=1), colors=color, lw=1.2))
        ax.plot([], [], color="tab:red", label="tension")
        ax.plot([], [], color="tab:blue", label="compression")
        ax.legend(loc="upper right", fontsize=8)
        self._decorate(ax, "Principal stress directions")
        return ax

    def plot_principal_stresses(self, arrows=True, arrow_spacing=None):
        """
        Plot the major and minor principal stresses as contour plots, plus a
        vector plot of principal directions (red = tension, blue = compression).
        """
        fig, axes = plt.subplots(3 if arrows else 2, 1, figsize=(9, 13 if arrows else 9))
        self.plot_principal_stress(1, axes[0])
        self.plot_principal_stress(2, axes[1])
        if arrows:
            self.plot_principal_directions(axes[2], arrow_spacing)
        fig.tight_layout()
        return fig

    def plot(self):
        """Overview: mesh, deformed shape and von Mises stress."""
        fig, axes = plt.subplots(3, 1, figsize=(9, 13))
        self.plot_mesh(axes[0])
        self.plot_deformed(axes[1])
        self.plot_von_mises(axes[2])
        fig.tight_layout()
        return fig


def main():
    wall = ConcreteWall(
        width=6.0,
        height=3.0,
        thickness=0.2,
        el_size=0.05,
        top_load=100e3,
        horizontal_load=20e3,
    )
    wall.add_window(x=0.6, sill_height=0.9, w=1.2, h=1.2)
    wall.add_door(x=2.6, w=1.0, h=2.1)
    wall.add_window(x=4.2, sill_height=0.9, w=1.2, h=1.2)

    # Fully supported along the bottom edge (default)
    wall.set_fully_supported()
    wall.solve()
    wall.summary()
    wall.plot()
    wall.plot_principal_stresses()
    print()

    # Freely supported at the ends and on each side of the door
    wall.set_freely_supported(positions=[2.3, 3.9], ends=True, support_length=0.3)
    wall.solve()
    wall.summary()
    wall.plot()
    wall.plot_principal_stresses()

    plt.show()


if __name__ == "__main__":
    main()
