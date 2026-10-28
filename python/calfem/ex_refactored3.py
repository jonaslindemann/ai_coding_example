# -*- coding: utf-8 -*-
"""
Steady-state seepage under a sheet pile wall (2D potential flow).

A rectangular soil domain has an impermeable sheet pile driven halfway
down from the middle of the top surface. The hydraulic head is prescribed
on the top surface on each side of the pile; all other boundaries
(bottom, ends, pile faces) are impermeable (zero flux, natural BC).

Solved with CALFEM using 4-node quadrilateral flow elements. Results are
plotted as element flow magnitudes and nodal head values.

All quantities are dimensionless; use any consistent unit system.

Object-oriented version of ex1_original.py - results are identical.

Responsibilities:
    SheetPileParams     model input (geometry, material, BCs, numerics)
    SheetPileGeometry   problem-specific geometry and boundary markers
    FlowMesh            mesh data and its creation from a geometry
    FlowSolver          generic FEM assembly and solution for 2D flow
    FlowPostProcessor   derived element quantities (flow magnitude)
    FlowResults         solution container
    ResultPlotter       visualisation
    SheetPileAnalysis   runs the steps above in order

Example
-------
>>> analysis = SheetPileAnalysis(SheetPileParams(pile_depth=7.0))
>>> results = analysis.run()
>>> max(results.flow_magnitude)
"""

from dataclasses import dataclass, field

import numpy as np
import calfem.core as cfc
import calfem.geometry as cfg
import calfem.mesh as cfm
import calfem.vis_mpl as cfv
import calfem.utils as cfu

EL_TYPE_QUAD4 = 3  # 4-node quadrilateral
DOFS_PER_NODE = 1  # scalar field (hydraulic head)


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


@dataclass
class SheetPileParams:
    """
    Physical and numerical input for the sheet pile seepage model.

    Attributes
    ----------
    domain_width : float
        Horizontal extent of the soil domain.
    domain_height : float
        Depth of the soil domain. The bottom is an impermeable layer.
    pile_width : float
        Thickness of the sheet pile (width of the slot cut from the domain).
    pile_depth : float
        How far the pile extends down from the top surface. Must be less
        than `domain_height`.
    permeability : ndarray, shape (2, 2)
        Permeability (constitutive) matrix D in Darcy's law q = -D grad(phi).
        Defaults to the identity matrix (isotropic, k = 1).
    upstream_head : float
        Prescribed head on the top surface left of the pile.
    downstream_head : float
        Prescribed head on the top surface right of the pile.
    element_thickness : float
        Out-of-plane thickness used by the elements. Flows are per unit
        of this thickness.
    integration_order : int
        Gauss integration order per direction (1, 2 or 3). The default 1
        reproduces the original script; 2 is usual for 4-node quads.
    el_size_factor : float
        Gmsh element size factor. Smaller values give a finer mesh.
    """

    domain_width: float = 100.0
    domain_height: float = 10.0
    pile_width: float = 1.0
    pile_depth: float = 5.0

    # Isotropic permeability (identity matrix -> k = 1 in x and y)
    permeability: np.ndarray = field(
        default_factory=lambda: np.identity(2, "float")
    )

    upstream_head: float = 10.0
    downstream_head: float = 0.0

    element_thickness: float = 1.0
    integration_order: int = 1  # 1x1 Gauss (2 is usual for 4-node quads)
    el_size_factor: float = 1.0

    @property
    def element_props(self):
        """
        Element property list in the format CALFEM expects.

        Returns
        -------
        list
            ``[element_thickness, integration_order]``, as used by
            ``flw2i4e`` and ``flw2i4s``.
        """
        return [self.element_thickness, self.integration_order]


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


class SheetPileGeometry:
    """
    Soil domain with a sheet pile cut out from the middle of the top.

    The pile is modelled as a rectangular slot in the domain, so its faces
    are domain boundaries with the default zero-flux condition.

    Parameters
    ----------
    params : SheetPileParams
        Model input. Only the geometry and head values are used.

    Attributes
    ----------
    UPSTREAM_MARKER : int
        Boundary marker for the top surface left of the pile.
    DOWNSTREAM_MARKER : int
        Boundary marker for the top surface right of the pile.
    """

    UPSTREAM_MARKER = 90  # top surface, left of the pile
    DOWNSTREAM_MARKER = 80  # top surface, right of the pile

    def __init__(self, params):
        self.params = params

    def build(self):
        """
        Create the CALFEM geometry for the domain.

        The boundary is defined counter-clockwise from the bottom-left
        corner, going around the pile slot. The two top-surface segments
        are tagged with `UPSTREAM_MARKER` and `DOWNSTREAM_MARKER`.

        Returns
        -------
        calfem.geometry.Geometry
            Geometry with 8 points, 8 boundary lines and one surface.
        """
        p = self.params
        w = p.domain_width
        h = p.domain_height
        pile_left = w / 2 - p.pile_width / 2
        pile_right = w / 2 + p.pile_width / 2
        pile_bottom = h - p.pile_depth

        g = cfg.Geometry()

        # Points numbered from 0, counter-clockwise from the bottom-left corner
        g.point([0, 0])  # 0: bottom left
        g.point([w, 0])  # 1: bottom right
        g.point([w, h])  # 2: top right
        g.point([pile_right, h])  # 3: pile, top right
        g.point([pile_right, pile_bottom])  # 4: pile, bottom right
        g.point([pile_left, pile_bottom])  # 5: pile, bottom left
        g.point([pile_left, h])  # 6: pile, top left
        g.point([0, h])  # 7: top left

        g.spline([0, 1])  # bottom
        g.spline([1, 2])  # right end
        g.spline([2, 3], marker=self.DOWNSTREAM_MARKER)  # top, right of pile
        g.spline([3, 4])  # pile, right face
        g.spline([4, 5])  # pile, bottom (tip)
        g.spline([5, 6])  # pile, left face
        g.spline([6, 7], marker=self.UPSTREAM_MARKER)  # top, left of pile
        g.spline([7, 0])  # left end

        g.surface([0, 1, 2, 3, 4, 5, 6, 7])

        return g

    def prescribed_heads(self):
        """
        Essential boundary conditions for this geometry.

        Returns
        -------
        dict of {int: float}
            Boundary marker mapped to the head prescribed on it. Boundaries
            not listed get the natural condition (zero flux).
        """
        return {
            self.DOWNSTREAM_MARKER: self.params.downstream_head,
            self.UPSTREAM_MARKER: self.params.upstream_head,
        }


# ---------------------------------------------------------------------------
# Mesh
# ---------------------------------------------------------------------------


@dataclass
class FlowMesh:
    """
    Finite element mesh for a scalar 2D flow problem.

    Attributes
    ----------
    coords : ndarray, shape (n_nodes, 2)
        Node coordinates.
    edof : ndarray, shape (n_elements, 4)
        Element topology: the global dofs of each element's nodes
        (1-based, as used throughout CALFEM).
    dofs : ndarray, shape (n_nodes, 1)
        Global dof number of each node.
    bdofs : dict of {int: list of int}
        Boundary marker mapped to the dofs on that boundary.
    element_markers : list of int
        Surface marker of each element (not used in this model).
    ex, ey : ndarray, shape (n_elements, 4)
        x and y coordinates of each element's nodes.
    """

    coords: np.ndarray
    edof: np.ndarray
    dofs: np.ndarray
    bdofs: dict
    element_markers: list
    ex: np.ndarray
    ey: np.ndarray

    @classmethod
    def create(cls, geometry, el_size_factor):
        """
        Mesh a geometry with Gmsh using 4-node quads and one dof per node.

        Parameters
        ----------
        geometry : calfem.geometry.Geometry
            Geometry to mesh.
        el_size_factor : float
            Gmsh element size factor. Smaller values give a finer mesh.

        Returns
        -------
        FlowMesh
            The generated mesh with element coordinates extracted.
        """
        gmsh_mesh = cfm.GmshMesh(geometry)
        gmsh_mesh.el_size_factor = el_size_factor
        gmsh_mesh.el_type = EL_TYPE_QUAD4
        gmsh_mesh.dofs_per_node = DOFS_PER_NODE

        coords, edof, dofs, bdofs, element_markers = gmsh_mesh.create()
        ex, ey = cfc.coordxtr(edof, coords, dofs)

        return cls(coords, edof, dofs, bdofs, element_markers, ex, ey)

    @property
    def n_dofs(self):
        """int: Total number of degrees of freedom in the mesh."""
        return np.size(self.dofs)


# ---------------------------------------------------------------------------
# Solution
# ---------------------------------------------------------------------------


@dataclass
class FlowResults:
    """
    Solution of the flow problem.

    Attributes
    ----------
    head : ndarray, shape (n_dofs, 1)
        Nodal head (the primary unknown).
    reactions : ndarray, shape (n_dofs, 1)
        Nodal flows needed to hold the prescribed heads. Non-zero only at
        prescribed dofs; their sum over one boundary is the total flow
        through it.
    flow_magnitude : list of float, optional
        Flow magnitude |q| per element. Set by `FlowPostProcessor`;
        ``None`` until post-processing has been run.
    """

    head: np.ndarray  # nodal head
    reactions: np.ndarray  # nodal flow at prescribed dofs
    flow_magnitude: list = None  # |q| per element


class FlowSolver:
    """
    FEM assembly and solution for 2D steady-state flow.

    Solves div(D grad(phi)) = 0 with 4-node isoparametric flow elements
    (CALFEM ``flw2i4e``) and prescribed heads on marked boundaries.

    Parameters
    ----------
    mesh : FlowMesh
        Mesh to solve on.
    element_props : list
        ``[thickness, integration_order]`` for ``flw2i4e``.
    permeability : ndarray, shape (2, 2)
        Permeability matrix D.
    """

    def __init__(self, mesh, element_props, permeability):
        self.mesh = mesh
        self.element_props = element_props
        self.permeability = permeability

    def assemble_stiffness(self):
        """
        Assemble the global flow stiffness matrix.

        Returns
        -------
        ndarray, shape (n_dofs, n_dofs)
            Dense global stiffness matrix K.
        """
        n_dofs = self.mesh.n_dofs
        K = np.zeros([n_dofs, n_dofs])

        for el_dofs, el_x, el_y in zip(self.mesh.edof, self.mesh.ex, self.mesh.ey):
            Ke = cfc.flw2i4e(el_x, el_y, self.element_props, self.permeability)
            cfc.assem(el_dofs, K, Ke)

        return K

    def boundary_conditions(self, prescribed_heads):
        """
        Convert marker-based heads to prescribed dofs and values.

        Parameters
        ----------
        prescribed_heads : dict of {int: float}
            Boundary marker mapped to the head prescribed on it.

        Returns
        -------
        bc_dofs : ndarray of int
            Prescribed dofs, sorted and unique.
        bc_values : ndarray of float
            Head value for each entry in `bc_dofs`.
        """
        bc_dofs = np.array([], int)
        bc_values = np.array([], float)

        for marker, head in prescribed_heads.items():
            bc_dofs, bc_values = cfu.applybc(
                self.mesh.bdofs, bc_dofs, bc_values, marker, head
            )

        return bc_dofs, bc_values

    def solve(self, prescribed_heads):
        """
        Assemble and solve for the nodal head field.

        No internal sources are applied (zero load vector).

        Parameters
        ----------
        prescribed_heads : dict of {int: float}
            Boundary marker mapped to the head prescribed on it.

        Returns
        -------
        FlowResults
            Nodal head and reactions. `flow_magnitude` is left as ``None``.
        """
        K = self.assemble_stiffness()
        f = np.zeros([self.mesh.n_dofs, 1])
        bc_dofs, bc_values = self.boundary_conditions(prescribed_heads)

        head, reactions = cfc.solveq(K, f, bc_dofs, bc_values)

        return FlowResults(head=head, reactions=reactions)


class FlowPostProcessor:
    """
    Element quantities derived from a solved head field.

    Parameters
    ----------
    mesh : FlowMesh
        Mesh the head field was solved on.
    element_props : list
        ``[thickness, integration_order]`` for ``flw2i4s``. Should be the
        same as used by the solver.
    permeability : ndarray, shape (2, 2)
        Permeability matrix D. Should be the same as used by the solver.
    """

    def __init__(self, mesh, element_props, permeability):
        self.mesh = mesh
        self.element_props = element_props
        self.permeability = permeability

    def flow_magnitude(self, head):
        """
        Compute the flow magnitude in each element from Darcy's law.

        The flow vector q = -D grad(phi) is evaluated at the first Gauss
        point of each element (the only one with 1x1 integration), and its
        Euclidean norm is returned.

        Parameters
        ----------
        head : ndarray, shape (n_dofs, 1)
            Nodal head from `FlowSolver.solve`.

        Returns
        -------
        list of float
            Flow magnitude |q| for each element, in `mesh.edof` order.
        """
        el_head = cfc.extract_eldisp(self.mesh.edof, head)

        magnitudes = []

        for el_x, el_y, el_a in zip(self.mesh.ex, self.mesh.ey, el_head):
            flow, _gradient, _eval_coords = cfc.flw2i4s(
                el_x, el_y, self.element_props, self.permeability, el_a
            )
            magnitudes.append(np.linalg.norm(flow[0, :]))

        return magnitudes


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------


class ResultPlotter:
    """
    Plots geometry, element flow magnitudes and nodal head.

    Parameters
    ----------
    geometry : calfem.geometry.Geometry
        Geometry to draw.
    mesh : FlowMesh
        Mesh the results are defined on.
    """

    def __init__(self, geometry, mesh):
        self.geometry = geometry
        self.mesh = mesh

    def plot_geometry(self):
        """Draw the geometry (points, lines and markers) in a new figure."""
        cfv.figure()
        cfv.draw_geometry(self.geometry, title="Geometry")

    def plot_flow_magnitude(self, flow_magnitude):
        """
        Draw element flow magnitudes in a new figure.

        Parameters
        ----------
        flow_magnitude : list of float
            Value per element, in `mesh.edof` order.
        """
        cfv.figure()
        cfv.draw_element_values(
            flow_magnitude, self.mesh.coords, self.mesh.edof, DOFS_PER_NODE,
            EL_TYPE_QUAD4, None, title="Flow magnitude"
        )

    def plot_head(self, head):
        """
        Draw the nodal head field as a contour plot in a new figure.

        Parameters
        ----------
        head : ndarray, shape (n_dofs, 1)
            Nodal head values.
        """
        cfv.figure()
        cfv.draw_nodal_values(
            head, self.mesh.coords, self.mesh.edof,
            dofs_per_node=DOFS_PER_NODE, el_type=EL_TYPE_QUAD4
        )

    def show(self, results):
        """
        Draw all plots and block until the windows are closed.

        Parameters
        ----------
        results : FlowResults
            Results with both `head` and `flow_magnitude` set.
        """
        self.plot_geometry()
        self.plot_flow_magnitude(results.flow_magnitude)
        self.plot_head(results.head)
        cfv.showAndWait()


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


class SheetPileAnalysis:
    """
    Runs the sheet pile seepage analysis from geometry to results.

    Parameters
    ----------
    params : SheetPileParams, optional
        Model input. Defaults to ``SheetPileParams()``.

    Attributes
    ----------
    geometry : calfem.geometry.Geometry or None
        Set by `run`.
    mesh : FlowMesh or None
        Set by `run`.
    results : FlowResults or None
        Set by `run`.
    """

    def __init__(self, params=None):
        self.params = params if params is not None else SheetPileParams()
        self.geometry = None
        self.mesh = None
        self.results = None

    def run(self):
        """
        Build the geometry and mesh, solve, and post-process.

        Does not open any plot windows; call `plot` afterwards for that.

        Returns
        -------
        FlowResults
            Head, reactions and element flow magnitudes.
        """
        p = self.params
        sheet_pile = SheetPileGeometry(p)

        self.geometry = sheet_pile.build()
        self.mesh = FlowMesh.create(self.geometry, p.el_size_factor)

        solver = FlowSolver(self.mesh, p.element_props, p.permeability)
        self.results = solver.solve(sheet_pile.prescribed_heads())

        post = FlowPostProcessor(self.mesh, p.element_props, p.permeability)
        self.results.flow_magnitude = post.flow_magnitude(self.results.head)

        return self.results

    def plot(self):
        """
        Show the geometry, flow magnitude and head plots.

        `run` must be called first.
        """
        ResultPlotter(self.geometry, self.mesh).show(self.results)


def main():
    """Run the analysis with default parameters and show the plots."""
    analysis = SheetPileAnalysis()
    analysis.run()
    analysis.plot()


if __name__ == "__main__":
    main()
