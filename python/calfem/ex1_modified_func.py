# -*- coding: utf-8 -*-

import numpy as np
import calfem.core as cfc
import calfem.geometry as cfg
import calfem.mesh as cfm
import calfem.vis_mpl as cfv
import calfem.utils as cfu

# Gmsh boundary marker IDs (must be unique positive integers)
# LEFT_WALL tags the top-edge segment from the right outer corner to the slot right opening.
# RIGHT_WALL tags the top-edge segment from the slot left opening to the left outer corner.
LEFT_WALL = 80   # right portion of top edge → prescribed potential = 0
RIGHT_WALL = 90  # left portion of top edge → prescribed potential = 10


def create_geometry(plate_width, plate_height, slot_width, slot_depth):
    """
    Build the notched-plate geometry.

    Constructs a rectangular plate with a narrow vertical slot cut into
    the centre of the top edge. The two outer top-edge segments adjacent
    to the slot opening are tagged with boundary markers so that
    Dirichlet conditions can be applied to them.

    Parameters
    ----------
    plate_width : float
        Total width of the plate.
    plate_height : float
        Total height of the plate.
    slot_width : float
        Width of the slot opening at the top edge.
    slot_depth : float
        Depth of the slot measured downward from the top edge.

    Returns
    -------
    cfg.Geometry
        Geometry object containing points, splines, and a surface
        ready to be passed to the mesh generator.
    """
    slot_right_x  = plate_width / 2 + slot_width / 2
    slot_left_x   = plate_width / 2 - slot_width / 2
    slot_bottom_y = plate_height - slot_depth

    g = cfg.Geometry()

    # Outer boundary and slot corners (0-indexed)
    g.point([0,            0])              # 0: bottom-left
    g.point([plate_width,  0])              # 1: bottom-right
    g.point([plate_width,  plate_height])   # 2: top-right
    g.point([slot_right_x, plate_height])   # 3: slot top-right
    g.point([slot_right_x, slot_bottom_y])  # 4: slot bottom-right
    g.point([slot_left_x,  slot_bottom_y])  # 5: slot bottom-left
    g.point([slot_left_x,  plate_height])   # 6: slot top-left
    g.point([0,            plate_height])   # 7: top-left

    g.spline([0, 1])                         # bottom edge
    g.spline([1, 2])                         # right edge
    g.spline([2, 3], marker=LEFT_WALL)       # left face of slot (BC marker)
    g.spline([3, 4])                         # slot right outer wall
    g.spline([4, 5])                         # slot bottom
    g.spline([5, 6])                         # slot left outer wall
    g.spline([6, 7], marker=RIGHT_WALL)      # right face of slot (BC marker)
    g.spline([7, 0])                         # left edge

    g.surface([0, 1, 2, 3, 4, 5, 6, 7])

    return g


def create_mesh(geometry, el_type, dofs_per_node):
    """
    Discretise the geometry into finite elements using Gmsh.

    Parameters
    ----------
    geometry : cfg.Geometry
        CALFEM geometry object describing the domain.
    el_type : int
        Element type identifier (3 = Q4 four-node quadrilateral).
    dofs_per_node : int
        Number of degrees of freedom per node (1 for a scalar field).

    Returns
    -------
    coords : ndarray, shape (n_nodes, 2)
        Global (x, y) coordinates of every node.
    edof : ndarray, shape (n_elements, dofs_per_element)
        Element connectivity: global DOF indices for each element.
    dofs : ndarray, shape (n_nodes, dofs_per_node)
        Global DOF numbers assigned to every node.
    bdofs : dict
        Mapping from boundary marker ID to list of global DOFs on
        that boundary.
    element_markers : list
        Gmsh physical marker associated with each element.
    """
    mesh = cfm.GmshMesh(geometry)
    mesh.el_size_factor = 1.0
    mesh.el_type = el_type
    mesh.dofs_per_node = dofs_per_node
    coords, edof, dofs, bdofs, element_markers = mesh.create()
    return coords, edof, dofs, bdofs, element_markers


def assemble_stiffness(edof, ex, ey, ep, D, n_dofs):
    """
    Assemble the global stiffness (conductivity) matrix.

    Loops over all elements, computes each element stiffness matrix
    with ``cfc.flw2i4e``, and accumulates the contributions into the
    global matrix via ``cfc.assem``.

    Parameters
    ----------
    edof : ndarray, shape (n_elements, dofs_per_element)
        Element connectivity (global DOF indices per element).
    ex : ndarray, shape (n_elements, n_nodes_per_element)
        x-coordinates of each element's nodes.
    ey : ndarray, shape (n_elements, n_nodes_per_element)
        y-coordinates of each element's nodes.
    ep : list
        Element parameters [thickness, integration_order].
    D : ndarray, shape (2, 2)
        Conductivity (material property) tensor.
    n_dofs : int
        Total number of degrees of freedom in the model.

    Returns
    -------
    K : ndarray, shape (n_dofs, n_dofs)
        Assembled global stiffness matrix.
    """
    K = np.zeros([n_dofs, n_dofs])
    for eltopo, elx, ely in zip(edof, ex, ey):
        Ke = cfc.flw2i4e(elx, ely, ep, D)
        cfc.assem(eltopo, K, Ke)
    return K


def apply_boundary_conditions(bdofs, left_value, right_value):
    """
    Build Dirichlet boundary condition arrays for the two slot walls.

    Applies fixed potential values to the nodes on the outer top-edge
    segments adjacent to the slot opening, identified by the module-level
    marker constants ``LEFT_WALL`` and ``RIGHT_WALL``.

    Parameters
    ----------
    bdofs : dict
        Boundary DOF mapping returned by the mesh generator.
    left_value : float
        Prescribed potential on the left slot wall.
    right_value : float
        Prescribed potential on the right slot wall.

    Returns
    -------
    bc_dofs : ndarray of int
        Global DOF indices where the potential is prescribed.
    bc_values : ndarray of float
        Corresponding prescribed potential values.
    """
    bc_dofs   = np.array([], int)
    bc_values = np.array([], int)
    bc_dofs, bc_values = cfu.applybc(bdofs, bc_dofs, bc_values, LEFT_WALL,  left_value)
    bc_dofs, bc_values = cfu.applybc(bdofs, bc_dofs, bc_values, RIGHT_WALL, right_value)
    return bc_dofs, bc_values


def compute_flux_magnitudes(ex, ey, ep, D, element_potentials):
    """
    Compute the flux magnitude at the centre of every element.

    For each element the flux vector **q** = -D ∇φ is evaluated at the
    central integration point using ``cfc.flw2i4s``. The Euclidean
    magnitude |**q**| = √(qx² + qy²) is returned as a scalar per element.

    Parameters
    ----------
    ex : ndarray, shape (n_elements, n_nodes_per_element)
        x-coordinates of each element's nodes.
    ey : ndarray, shape (n_elements, n_nodes_per_element)
        y-coordinates of each element's nodes.
    ep : list
        Element parameters [thickness, integration_order].
    D : ndarray, shape (2, 2)
        Conductivity tensor.
    element_potentials : ndarray, shape (n_elements, n_nodes_per_element)
        Nodal potential values extracted for each element.

    Returns
    -------
    list of float
        Flux magnitude at the centre of each element, in the same order
        as the rows of ``element_potentials``.
    """
    flux_magnitude = []
    for i in range(element_potentials.shape[0]):
        es, _, _ = cfc.flw2i4s(ex[i, :], ey[i, :], ep, D, element_potentials[i, :])
        flux_magnitude.append(np.sqrt(es[0, 0]**2 + es[0, 1]**2))
    return flux_magnitude


def visualize(g, flux_magnitude, coords, edof, dofs_per_node, el_type, nodal_potentials):
    """
    Render the simulation results in three separate figure windows.

    Produces:
    1. The problem geometry (domain outline and boundaries).
    2. A colour map of flux magnitude per element.
    3. A colour map of the nodal potential field.

    Parameters
    ----------
    g : cfg.Geometry
        Geometry object used to draw the domain outline.
    flux_magnitude : list of float
        Per-element flux magnitude values.
    coords : ndarray, shape (n_nodes, 2)
        Global node coordinates.
    edof : ndarray, shape (n_elements, dofs_per_element)
        Element connectivity array.
    dofs_per_node : int
        Number of DOFs per node (1 for a scalar field).
    el_type : int
        Element type identifier passed to the CALFEM visualisation
        routines.
    nodal_potentials : ndarray, shape (n_dofs, 1)
        Solved potential value at every node.
    """
    cfv.figure()
    cfv.draw_geometry(g, title="Geometry")

    cfv.figure()
    cfv.draw_element_values(
        flux_magnitude, coords, edof, dofs_per_node, el_type, None,
        title="Flux magnitude"
    )

    cfv.figure()
    cfv.draw_nodal_values(
        nodal_potentials, coords, edof,
        dofs_per_node=dofs_per_node, el_type=el_type
    )

    cfv.showAndWait()


def main():
    """
    Run the full 2-D steady-state potential flow analysis.

    Defines the problem parameters, builds the geometry and mesh,
    assembles and solves the FEM system, computes element fluxes, and
    displays the results. Entry point when the script is executed
    directly.
    """
    # Problem parameters
    plate_width  = 100.0
    plate_height = 10.0
    slot_width   = 1.0
    slot_depth   = plate_height / 2

    D  = np.identity(2, "float")  # isotropic conductivity tensor
    ep = [1.0, 1]                 # element params: [thickness, integration order]

    el_type       = 3  # Q4: 4-node quadrilateral element
    dofs_per_node = 1  # scalar field (one potential per node)

    # Build geometry and mesh
    g = create_geometry(plate_width, plate_height, slot_width, slot_depth)
    coords, edof, dofs, bdofs, _ = create_mesh(g, el_type, dofs_per_node)

    # Assemble global stiffness matrix
    n_dofs = np.size(dofs)
    ex, ey = cfc.coordxtr(edof, coords, dofs)
    K = assemble_stiffness(edof, ex, ey, ep, D, n_dofs)

    # Apply boundary conditions and solve
    load_vector       = np.zeros([n_dofs, 1])
    bc_dofs, bc_values = apply_boundary_conditions(bdofs, left_value=0.0, right_value=10.0)
    nodal_potentials, _ = cfc.solveq(K, load_vector, bc_dofs, bc_values)

    # Post-process: compute per-element flux magnitudes
    element_potentials = cfc.extract_eldisp(edof, nodal_potentials)
    flux_magnitude = compute_flux_magnitudes(ex, ey, ep, D, element_potentials)

    # Visualize results
    visualize(g, flux_magnitude, coords, edof, dofs_per_node, el_type, nodal_potentials)


if __name__ == "__main__":
    main()
