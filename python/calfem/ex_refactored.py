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

Readability refactor of ex1_original.py - results are identical.
"""

import numpy as np
import calfem.core as cfc
import calfem.geometry as cfg
import calfem.mesh as cfm
import calfem.vis_mpl as cfv
import calfem.utils as cfu

# ---------------------------------------------------------------------------
# Input parameters
# ---------------------------------------------------------------------------

# Domain and pile geometry
domain_width = 100.0
domain_height = 10.0
pile_width = 1.0
pile_depth = domain_height / 2

# Material: isotropic permeability (identity matrix -> k = 1 in x and y)
permeability = np.identity(2, "float")

# Element properties for flw2i4e/flw2i4s: [thickness, integration order]
element_thickness = 1.0
integration_order = 1  # 1x1 Gauss (2 is the usual choice for 4-node quads)
element_props = [element_thickness, integration_order]

# Boundary markers and prescribed heads
upstream_marker = 90  # top surface, left of the pile
downstream_marker = 80  # top surface, right of the pile
upstream_head = 10.0
downstream_head = 0.0

# Mesh settings
el_type = 3  # 4-node quadrilateral
dofs_per_node = 1  # scalar field (hydraulic head)
el_size_factor = 1.0

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

pile_left = domain_width / 2 - pile_width / 2
pile_right = domain_width / 2 + pile_width / 2
pile_bottom = domain_height - pile_depth

g = cfg.Geometry()

# Points are numbered from 0, counter-clockwise from the bottom-left corner
g.point([0, 0])  # 0: bottom left
g.point([domain_width, 0])  # 1: bottom right
g.point([domain_width, domain_height])  # 2: top right
g.point([pile_right, domain_height])  # 3: pile, top right
g.point([pile_right, pile_bottom])  # 4: pile, bottom right
g.point([pile_left, pile_bottom])  # 5: pile, bottom left
g.point([pile_left, domain_height])  # 6: pile, top left
g.point([0, domain_height])  # 7: top left

g.spline([0, 1])  # bottom
g.spline([1, 2])  # right end
g.spline([2, 3], marker=downstream_marker)  # top surface, right of pile
g.spline([3, 4])  # pile, right face
g.spline([4, 5])  # pile, bottom (tip)
g.spline([5, 6])  # pile, left face
g.spline([6, 7], marker=upstream_marker)  # top surface, left of pile
g.spline([7, 0])  # left end

g.surface([0, 1, 2, 3, 4, 5, 6, 7])

# ---------------------------------------------------------------------------
# Mesh
# ---------------------------------------------------------------------------

mesh = cfm.GmshMesh(g)
mesh.el_size_factor = el_size_factor
mesh.el_type = el_type
mesh.dofs_per_node = dofs_per_node

coords, edof, dofs, bdofs, element_markers = mesh.create()

n_dofs = np.size(dofs)
ex, ey = cfc.coordxtr(edof, coords, dofs)

# ---------------------------------------------------------------------------
# Assemble global stiffness matrix
# ---------------------------------------------------------------------------

K = np.zeros([n_dofs, n_dofs])

for el_dofs, el_x, el_y in zip(edof, ex, ey):
    Ke = cfc.flw2i4e(el_x, el_y, element_props, permeability)
    cfc.assem(el_dofs, K, Ke)

f = np.zeros([n_dofs, 1])  # no internal sources

# ---------------------------------------------------------------------------
# Boundary conditions and solution
# ---------------------------------------------------------------------------

bc_dofs = np.array([], int)
bc_values = np.array([], float)

bc_dofs, bc_values = cfu.applybc(
    bdofs, bc_dofs, bc_values, downstream_marker, downstream_head
)
bc_dofs, bc_values = cfu.applybc(
    bdofs, bc_dofs, bc_values, upstream_marker, upstream_head
)

head, reactions = cfc.solveq(K, f, bc_dofs, bc_values)

# ---------------------------------------------------------------------------
# Post-processing: flow magnitude in each element (Darcy's law)
# ---------------------------------------------------------------------------

el_head = cfc.extract_eldisp(edof, head)

flow_magnitude = []

for el_x, el_y, el_a in zip(ex, ey, el_head):
    flow, _gradient, _eval_coords = cfc.flw2i4s(
        el_x, el_y, element_props, permeability, el_a
    )
    flow_magnitude.append(np.linalg.norm(flow[0, :]))

# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

cfv.figure()
cfv.draw_geometry(g, title="Geometry")

cfv.figure()
cfv.draw_element_values(
    flow_magnitude, coords, edof, dofs_per_node, el_type, None,
    title="Flow magnitude"
)

cfv.figure()
cfv.draw_nodal_values(
    head, coords, edof, dofs_per_node=dofs_per_node, el_type=el_type
)

cfv.showAndWait()
