# -*- coding: utf-8 -*-

import numpy as np
import calfem.core as cfc
import calfem.geometry as cfg
import calfem.mesh as cfm
import calfem.vis_mpl as cfv
import calfem.utils as cfu


class NotchedPlateGeometry:
    """
    Geometry of a rectangular plate with a narrow slot cut into the top centre.

    Owns the plate dimensions, slot dimensions, and the Gmsh boundary marker
    IDs used to identify the two top-edge segments adjacent to the slot.
    The CALFEM Geometry object is built lazily on first access.

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
    left_marker : int
        Gmsh marker for the right portion of the top edge (adjacent to the
        slot right opening). Must be a unique positive integer.
    right_marker : int
        Gmsh marker for the left portion of the top edge (adjacent to the
        slot left opening). Must be a unique positive integer.
    """

    def __init__(
        self,
        plate_width,
        plate_height,
        slot_width,
        slot_depth,
        left_marker=80,
        right_marker=90,
    ):
        self.plate_width  = plate_width
        self.plate_height = plate_height
        self.slot_width   = slot_width
        self.slot_depth   = slot_depth
        self.left_marker  = left_marker
        self.right_marker = right_marker
        self._geometry    = None

    @property
    def geometry(self):
        """
        The CALFEM Geometry object, built on first access.

        Returns
        -------
        cfg.Geometry
        """
        if self._geometry is None:
            self._geometry = self._build()
        return self._geometry

    def _build(self):
        """Construct and return the CALFEM Geometry object."""
        slot_right_x  = self.plate_width / 2 + self.slot_width / 2
        slot_left_x   = self.plate_width / 2 - self.slot_width / 2
        slot_bottom_y = self.plate_height - self.slot_depth

        g = cfg.Geometry()

        # Outer boundary and slot corners (0-indexed)
        g.point([0,                0])                  # 0: bottom-left
        g.point([self.plate_width, 0])                  # 1: bottom-right
        g.point([self.plate_width, self.plate_height])  # 2: top-right
        g.point([slot_right_x,     self.plate_height])  # 3: slot top-right
        g.point([slot_right_x,     slot_bottom_y])      # 4: slot bottom-right
        g.point([slot_left_x,      slot_bottom_y])      # 5: slot bottom-left
        g.point([slot_left_x,      self.plate_height])  # 6: slot top-left
        g.point([0,                self.plate_height])  # 7: top-left

        g.spline([0, 1])                                # bottom edge
        g.spline([1, 2])                                # right edge
        g.spline([2, 3], marker=self.left_marker)       # right portion of top edge (BC)
        g.spline([3, 4])                                # slot right outer wall
        g.spline([4, 5])                                # slot bottom
        g.spline([5, 6])                                # slot left outer wall
        g.spline([6, 7], marker=self.right_marker)      # left portion of top edge (BC)
        g.spline([7, 0])                                # left edge

        g.surface([0, 1, 2, 3, 4, 5, 6, 7])

        return g


class PotentialFlowSolver:
    """
    FEM solver for 2-D steady-state potential flow.

    Manages the full analysis pipeline: meshing, stiffness assembly,
    boundary condition application, solving, and flux post-processing.
    Results are stored as instance attributes after calling ``solve()``.

    Parameters
    ----------
    geometry : NotchedPlateGeometry
        Problem geometry supplying the CALFEM Geometry object and
        boundary marker IDs.
    conductivity : ndarray, shape (2, 2)
        Conductivity tensor D (use ``np.identity(2)`` for isotropic).
    el_type : int
        Element type identifier (3 = Q4 four-node quadrilateral).
    dofs_per_node : int
        Number of degrees of freedom per node (1 for a scalar field).
    thickness : float
        Out-of-plane thickness for the 2-D plane formulation.
    """

    def __init__(
        self,
        geometry,
        conductivity,
        el_type=3,
        dofs_per_node=1,
        thickness=1.0,
    ):
        self.geometry      = geometry
        self.conductivity  = conductivity
        self.el_type       = el_type
        self.dofs_per_node = dofs_per_node
        self.ep            = [thickness, 1]  # [thickness, integration_order]

        # Mesh data — populated by solve()
        self.coords = None
        self.edof   = None
        self.dofs   = None
        self.bdofs  = None
        self.ex     = None
        self.ey     = None

        # Solution data — populated by solve()
        self.nodal_potentials = None
        self.flux_magnitudes  = None

    def solve(self, left_value=0.0, right_value=10.0):
        """
        Execute the full FEM analysis pipeline.

        Meshes the geometry, assembles the global stiffness matrix, applies
        Dirichlet boundary conditions, solves the linear system, and computes
        per-element flux magnitudes. All results are stored as attributes.

        Parameters
        ----------
        left_value : float
            Prescribed potential on the ``left_marker`` boundary.
        right_value : float
            Prescribed potential on the ``right_marker`` boundary.
        """
        self._create_mesh()
        K = self._assemble_stiffness()
        bc_dofs, bc_values = self._build_boundary_conditions(left_value, right_value)

        n_dofs      = np.size(self.dofs)
        load_vector = np.zeros([n_dofs, 1])

        self.nodal_potentials, _ = cfc.solveq(K, load_vector, bc_dofs, bc_values)

        element_potentials   = cfc.extract_eldisp(self.edof, self.nodal_potentials)
        self.flux_magnitudes = self._compute_flux_magnitudes(element_potentials)

    # ------------------------------------------------------------------
    # Private pipeline steps
    # ------------------------------------------------------------------

    def _create_mesh(self):
        """Mesh the geometry and populate mesh data attributes."""
        mesh = cfm.GmshMesh(self.geometry.geometry)
        mesh.el_size_factor = 1.0
        mesh.el_type        = self.el_type
        mesh.dofs_per_node  = self.dofs_per_node
        self.coords, self.edof, self.dofs, self.bdofs, _ = mesh.create()
        self.ex, self.ey = cfc.coordxtr(self.edof, self.coords, self.dofs)

    def _assemble_stiffness(self):
        """
        Build and return the global stiffness matrix K.

        Returns
        -------
        K : ndarray, shape (n_dofs, n_dofs)
        """
        n_dofs = np.size(self.dofs)
        K = np.zeros([n_dofs, n_dofs])
        for eltopo, elx, ely in zip(self.edof, self.ex, self.ey):
            Ke = cfc.flw2i4e(elx, ely, self.ep, self.conductivity)
            cfc.assem(eltopo, K, Ke)
        return K

    def _build_boundary_conditions(self, left_value, right_value):
        """
        Build Dirichlet BC arrays for the two marked top-edge segments.

        Parameters
        ----------
        left_value : float
            Prescribed potential on the left_marker boundary.
        right_value : float
            Prescribed potential on the right_marker boundary.

        Returns
        -------
        bc_dofs : ndarray of int
        bc_values : ndarray of float
        """
        bc_dofs   = np.array([], int)
        bc_values = np.array([], int)
        bc_dofs, bc_values = cfu.applybc(
            self.bdofs, bc_dofs, bc_values,
            self.geometry.left_marker, left_value
        )
        bc_dofs, bc_values = cfu.applybc(
            self.bdofs, bc_dofs, bc_values,
            self.geometry.right_marker, right_value
        )
        return bc_dofs, bc_values

    def _compute_flux_magnitudes(self, element_potentials):
        """
        Compute the flux magnitude |q| = √(qx² + qy²) at the centre of each element.

        Parameters
        ----------
        element_potentials : ndarray, shape (n_elements, n_nodes_per_element)
            Nodal potentials gathered per element.

        Returns
        -------
        list of float
            Flux magnitude for each element.
        """
        flux_magnitudes = []
        for i in range(element_potentials.shape[0]):
            es, _, _ = cfc.flw2i4s(
                self.ex[i, :], self.ey[i, :],
                self.ep, self.conductivity,
                element_potentials[i, :]
            )
            flux_magnitudes.append(np.sqrt(es[0, 0]**2 + es[0, 1]**2))
        return flux_magnitudes


class FlowVisualizer:
    """
    Renders the results of a solved potential flow simulation.

    Parameters
    ----------
    geometry : NotchedPlateGeometry
        The problem geometry (used to draw the domain outline).
    solver : PotentialFlowSolver
        A solver instance on which ``solve()`` has already been called.
    """

    def __init__(self, geometry, solver):
        self.geometry = geometry
        self.solver   = solver

    def show(self):
        """
        Open three figure windows and block until they are closed.

        Figures:
        1. Domain geometry outline.
        2. Per-element flux magnitude colour map.
        3. Nodal potential field colour map.
        """
        cfv.figure()
        cfv.draw_geometry(self.geometry.geometry, title="Geometry")

        cfv.figure()
        cfv.draw_element_values(
            self.solver.flux_magnitudes,
            self.solver.coords,
            self.solver.edof,
            self.solver.dofs_per_node,
            self.solver.el_type,
            None,
            title="Flux magnitude",
        )

        cfv.figure()
        cfv.draw_nodal_values(
            self.solver.nodal_potentials,
            self.solver.coords,
            self.solver.edof,
            dofs_per_node=self.solver.dofs_per_node,
            el_type=self.solver.el_type,
        )

        cfv.showAndWait()


def main():
    """Run the notched-plate 2-D steady-state potential flow analysis."""

    geometry = NotchedPlateGeometry(
        plate_width=100.0,
        plate_height=10.0,
        slot_width=1.0,
        slot_depth=5.0,
    )

    solver = PotentialFlowSolver(
        geometry=geometry,
        conductivity=np.identity(2, "float"),
    )
    solver.solve(left_value=0.0, right_value=10.0)

    FlowVisualizer(geometry, solver).show()


if __name__ == "__main__":
    main()



