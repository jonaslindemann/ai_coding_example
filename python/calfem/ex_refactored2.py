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

Function-based restructuring of ex1_original.py - results are identical.
"""

from dataclasses import dataclass, field

import numpy as np
import calfem.core as cfc
import calfem.geometry as cfg
import calfem.mesh as cfm
import calfem.vis_mpl as cfv
import calfem.utils as cfu

UPSTREAM_MARKER = 90  # top surface, left of the pile
DOWNSTREAM_MARKER = 80  # top surface, right of the pile

EL_TYPE_QUAD4 = 3  # 4-node quadrilateral
DOFS_PER_NODE = 1  # scalar field (hydraulic head)


@dataclass
class SheetPileParams:
    """Physical and numerical input for the sheet pile seepage model."""

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
        """Element properties for flw2i4e/flw2i4s: [thickness, int. order]."""
        return [self.element_thickness, self.integration_order]


@dataclass
class Mesh:
    """Mesh data returned by CALFEM, with element coordinates extracted."""

    coords: np.ndarray
    edof: np.ndarray
    dofs: np.ndarray
    bdofs: dict
    element_markers: list
    ex: np.ndarray
    ey: np.ndarray

    @property
    def n_dofs(self):
        return np.size(self.dofs)


def build_geometry(params):
    """Create the soil domain with the sheet pile cut out from the top."""
    w = params.domain_width
    h = params.domain_height
    pile_left = w / 2 - params.pile_width / 2
    pile_right = w / 2 + params.pile_width / 2
    pile_bottom = h - params.pile_depth

    g = cfg.Geometry()

    # Points are numbered from 0, counter-clockwise from the bottom-left corner
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
    g.spline([2, 3], marker=DOWNSTREAM_MARKER)  # top surface, right of pile
    g.spline([3, 4])  # pile, right face
    g.spline([4, 5])  # pile, bottom (tip)
    g.spline([5, 6])  # pile, left face
    g.spline([6, 7], marker=UPSTREAM_MARKER)  # top surface, left of pile
    g.spline([7, 0])  # left end

    g.surface([0, 1, 2, 3, 4, 5, 6, 7])

    return g


def create_mesh(geometry, params):
    """Mesh the geometry with 4-node quadrilaterals, one dof per node."""
    gmsh_mesh = cfm.GmshMesh(geometry)
    gmsh_mesh.el_size_factor = params.el_size_factor
    gmsh_mesh.el_type = EL_TYPE_QUAD4
    gmsh_mesh.dofs_per_node = DOFS_PER_NODE

    coords, edof, dofs, bdofs, element_markers = gmsh_mesh.create()
    ex, ey = cfc.coordxtr(edof, coords, dofs)

    return Mesh(coords, edof, dofs, bdofs, element_markers, ex, ey)


def assemble_stiffness(mesh, params):
    """Assemble the global flow stiffness matrix K."""
    K = np.zeros([mesh.n_dofs, mesh.n_dofs])

    for el_dofs, el_x, el_y in zip(mesh.edof, mesh.ex, mesh.ey):
        Ke = cfc.flw2i4e(el_x, el_y, params.element_props, params.permeability)
        cfc.assem(el_dofs, K, Ke)

    return K


def boundary_conditions(mesh, params):
    """Return prescribed dofs and their head values."""
    bc_dofs = np.array([], int)
    bc_values = np.array([], float)

    bc_dofs, bc_values = cfu.applybc(
        mesh.bdofs, bc_dofs, bc_values, DOWNSTREAM_MARKER, params.downstream_head
    )
    bc_dofs, bc_values = cfu.applybc(
        mesh.bdofs, bc_dofs, bc_values, UPSTREAM_MARKER, params.upstream_head
    )

    return bc_dofs, bc_values


def solve_head(mesh, params):
    """Assemble and solve for nodal head. Returns (head, reactions)."""
    K = assemble_stiffness(mesh, params)
    f = np.zeros([mesh.n_dofs, 1])  # no internal sources
    bc_dofs, bc_values = boundary_conditions(mesh, params)

    return cfc.solveq(K, f, bc_dofs, bc_values)


def compute_flow_magnitude(mesh, params, head):
    """Flow magnitude |q| in each element from Darcy's law."""
    el_head = cfc.extract_eldisp(mesh.edof, head)

    flow_magnitude = []

    for el_x, el_y, el_a in zip(mesh.ex, mesh.ey, el_head):
        flow, _gradient, _eval_coords = cfc.flw2i4s(
            el_x, el_y, params.element_props, params.permeability, el_a
        )
        flow_magnitude.append(np.linalg.norm(flow[0, :]))

    return flow_magnitude


def plot_results(geometry, mesh, head, flow_magnitude):
    """Show geometry, element flow magnitudes and nodal head."""
    cfv.figure()
    cfv.draw_geometry(geometry, title="Geometry")

    cfv.figure()
    cfv.draw_element_values(
        flow_magnitude, mesh.coords, mesh.edof, DOFS_PER_NODE, EL_TYPE_QUAD4,
        None, title="Flow magnitude"
    )

    cfv.figure()
    cfv.draw_nodal_values(
        head, mesh.coords, mesh.edof, dofs_per_node=DOFS_PER_NODE,
        el_type=EL_TYPE_QUAD4
    )

    cfv.showAndWait()


def main():
    params = SheetPileParams()

    geometry = build_geometry(params)
    mesh = create_mesh(geometry, params)
    head, _reactions = solve_head(mesh, params)
    flow_magnitude = compute_flow_magnitude(mesh, params, head)

    plot_results(geometry, mesh, head, flow_magnitude)


if __name__ == "__main__":
    main()
