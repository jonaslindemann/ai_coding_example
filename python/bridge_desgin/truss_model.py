"""Geometry and topology of a 2D footbridge truss for CALFEM for Python.

This module builds the structural model of one of the two identical trusses
described in ``bridge_spec_final.md``: node coordinates, element
connectivity, member groups, section classes, the CALFEM ``edof`` matrix and
the constrained degrees of freedom. It does no stiffness assembly and no
solving.

Conventions (spec sections 3.3 and 5):

* SI units: lengths in metres.
* Global x along the span from the left support, y vertically upwards.
* Nodes, elements and DOFs are numbered from 1, as CALFEM's ``edof`` and
  ``solveq`` expect. Node k has DOFs 2k - 1 (x) and 2k (y).
"""

import calfem.core as cfc
import numpy as np

#: Relative zero-force tolerance: N_tol = ZERO_FORCE_TOL * W, with W = w * L
#: (spec 3.6, R8).
ZERO_FORCE_TOL = 1e-9

#: Truss types accepted by :class:`TrussBridge` (spec 3.2).
TRUSS_TYPES = ("pratt", "howe", "warren")

# Member group labels (spec 3.3). Elements are stored in this group order.
GROUP_BOTTOM_CHORD = "bottom chord"
GROUP_TOP_CHORD = "top chord"
GROUP_VERTICAL = "vertical"
GROUP_END_POST = "end post"
GROUP_DIAGONAL = "diagonal"

# Section classes (spec 3.3): chord members take area A_c, web members A_w.
CLASS_CHORD = "chord"
CLASS_WEB = "web"

#: Section class of each member group (spec 3.3, R2). End posts exist only in
#: Pratt and Howe trusses. Warren's end diagonals are ordinary diagonals and
#: therefore belong to the web class.
SECTION_CLASS_OF_GROUP = {
    GROUP_BOTTOM_CHORD: CLASS_CHORD,
    GROUP_TOP_CHORD: CLASS_CHORD,
    GROUP_END_POST: CLASS_CHORD,
    GROUP_VERTICAL: CLASS_WEB,
    GROUP_DIAGONAL: CLASS_WEB,
}


class TrussBridge:
    """Geometry and topology of one simply supported Pratt, Howe or Warren truss.

    The truss spans ``L`` with ``n`` panels of length ``L / n`` and height
    ``h`` between the chord centrelines. The deck, and therefore every load,
    is at the bottom chord.

    Node layout (spec 3.2), with B_i the bottom node at x = i * L / n,
    i = 0 ... n:

    * Pratt and Howe: top nodes T_i at (i * L / n, h), i = 1 ... n - 1. There
      is no top node over a support, and inclined end posts B_0-T_1 and
      B_n-T_(n-1) close the truss.
    * Warren: top nodes T_i at ((i + 1/2) * L / n, h), i = 0 ... n - 1, over
      the panel midpoints. There are no verticals.

    Numbering (spec 3.3): the bottom nodes come first, left to right, so B_i
    is node i + 1. The top nodes follow, left to right. Elements are stored
    in group order: bottom chord, top chord, verticals, end posts, diagonals.

    Supports (spec 3.4): a pin at B_0 (u_x = u_y = 0) and a roller at B_n
    (u_y = 0), so r = 3 support reactions. Both truss families are statically
    determinate: m + r = 2j.

    Parameters
    ----------
    truss_type : str
        ``"pratt"``, ``"howe"`` or ``"warren"``, in any letter case.
    L : float
        Span between the support centrelines [m]. Must be positive.
    h : float
        Truss height between the chord centrelines [m]. Must be positive.
    n : int
        Number of panels. Must be an even integer >= 2, so that the truss is
        symmetric and has a bottom node at midspan.

    Raises
    ------
    ValueError
        If ``truss_type`` is unknown, ``n`` is not an even integer >= 2, or
        ``L`` or ``h`` is not positive.

    Attributes
    ----------
    truss_type : str
        Truss type in lower case.
    L, h : float
        Span and height [m].
    n : int
        Number of panels.
    panel_length : float
        Panel length L / n [m].
    coords : ndarray, shape (j, 2)
        Node coordinates [m]. Row k - 1 holds (x, y) of node k.
    num_nodes : int
        Number of nodes j: 2n for Pratt/Howe, 2n + 1 for Warren.
    elements : ndarray of int, shape (m, 2)
        1-based node numbers (start node, end node) of each element.
    member_groups : list of str
        Group label of each element: one of ``"bottom chord"``,
        ``"top chord"``, ``"vertical"``, ``"end post"``, ``"diagonal"``.
    section_classes : list of str
        Section class of each element: ``"chord"`` or ``"web"``.
    num_elements : int
        Number of elements m: 4n - 3 for Pratt/Howe, 4n - 1 for Warren.
    ex, ey : ndarray, shape (m, 2)
        x and y coordinates of the start and end node of each element, in
        the form CALFEM's ``bar2e`` and ``bar2s`` take.
    lengths : ndarray, shape (m,)
        Member lengths [m].
    num_dofs : int
        Total number of degrees of freedom, 2j.
    edof : ndarray of int, shape (m, 4)
        CALFEM topology matrix. Row e holds the 1-based DOFs
        [x_start, y_start, x_end, y_end] of element e.
    support_nodes : list of int
        Node numbers of the pinned support (B_0) and the roller (B_n).
    bc_dofs : ndarray of int, shape (3,)
        1-based constrained DOFs [x and y of B_0, y of B_n], as the
        ``bcPrescr`` argument of CALFEM's ``solveq``.
    num_reactions : int
        Number of support reactions r (always 3).
    loaded_nodes : list of int
        Node numbers of the bottom-chord nodes B_0 ... B_n, which carry the
        deck load (spec 3.5).
    midspan_node : int
        Node number of B_(n/2), the node used for the deflection check.
    """

    def __init__(self, truss_type, L, h, n):
        """Validate the input and build nodes, elements and DOF data.

        See the class docstring for the parameters and the attributes set.
        """
        truss_type = str(truss_type).lower()
        if truss_type not in TRUSS_TYPES:
            raise ValueError(f"truss_type must be one of {TRUSS_TYPES}, got {truss_type!r}")
        # bool is a subclass of int, so True/False must be rejected
        # explicitly. int(n) != n rejects non-integer values such as 4.5.
        if isinstance(n, bool) or int(n) != n or n < 2 or n % 2 != 0:
            raise ValueError(f"n must be an even integer >= 2, got {n!r}")
        if not L > 0:
            raise ValueError(f"L must be positive, got {L!r}")
        if not h > 0:
            raise ValueError(f"h must be positive, got {h!r}")

        self.truss_type = truss_type
        self.L = float(L)
        self.h = float(h)
        self.n = int(n)
        self.panel_length = self.L / self.n

        # The order matters: elements need the node coordinates, and the
        # DOF data needs the elements.
        self._build_nodes()
        self._build_elements()
        self._build_dofs()

    def _bottom(self, i):
        """Return the 1-based node number of bottom node B_i, i = 0 ... n."""
        return i + 1

    def _top(self, i):
        """Return the 1-based node number of top node T_i.

        The top nodes are numbered after the n + 1 bottom nodes. Warren
        top nodes start at T_0 (node n + 2). Pratt and Howe top nodes start
        at T_1 (also node n + 2), because there is no T_0 over the support.
        """
        if self.truss_type == "warren":
            return self.n + 2 + i
        return self.n + 1 + i

    def _build_nodes(self):
        """Compute the node coordinates (spec 3.2).

        Sets ``coords`` (bottom nodes first, then top nodes, each left to
        right) and ``num_nodes``.
        """
        n, d, h = self.n, self.panel_length, self.h

        bottom = [(i * d, 0.0) for i in range(n + 1)]
        if self.truss_type == "warren":
            # Top nodes over the panel midpoints, T_0 ... T_(n-1).
            top = [((i + 0.5) * d, h) for i in range(n)]
        else:
            # Top nodes over the interior bottom nodes, T_1 ... T_(n-1).
            top = [(i * d, h) for i in range(1, n)]

        self.coords = np.array(bottom + top, dtype=float)
        self.num_nodes = self.coords.shape[0]

    def _build_elements(self):
        """Build the element connectivity, member groups and member geometry.

        The members of each truss type are those in spec 3.2, stored in group
        order. Within each group they run from left to right.

        Pratt and Howe diagonals sit in the interior panels i = 1 ... n - 2,
        where panel i lies between B_i and B_(i+1):

        * Pratt: the lower end points towards midspan. Left half: T_i-B_(i+1).
          Right half: B_i-T_(i+1).
        * Howe: the lower end points towards the supports. Left half:
          B_i-T_(i+1). Right half: T_i-B_(i+1).

        The left half is panels i <= n/2 - 1, and the right half is
        panels i >= n/2 (spec 3.2, R4).

        Sets ``elements``, ``member_groups``, ``section_classes``,
        ``num_elements``, ``ex``, ``ey`` and ``lengths``.
        """
        n = self.n
        B, T = self._bottom, self._top
        elements = []
        groups = []

        def add(group, members):
            """Append the (start, end) node pairs in members under one group label."""
            for node_a, node_b in members:
                elements.append((node_a, node_b))
                groups.append(group)

        add(GROUP_BOTTOM_CHORD, [(B(i), B(i + 1)) for i in range(n)])

        if self.truss_type == "warren":
            add(GROUP_TOP_CHORD, [(T(i), T(i + 1)) for i in range(n - 1)])
            # Each panel i has two diagonals meeting at T_i: up from B_i and
            # down to B_(i+1). The end diagonals B_0-T_0 and T_(n-1)-B_n are
            # ordinary diagonals (R2).
            diagonals = []
            for i in range(n):
                diagonals.append((B(i), T(i)))
                diagonals.append((T(i), B(i + 1)))
            add(GROUP_DIAGONAL, diagonals)
        else:
            add(GROUP_TOP_CHORD, [(T(i), T(i + 1)) for i in range(1, n - 1)])
            add(GROUP_VERTICAL, [(B(i), T(i)) for i in range(1, n)])
            add(GROUP_END_POST, [(B(0), T(1)), (B(n), T(n - 1))])

            # The Pratt left half and the Howe right half share the
            # orientation T_i-B_(i+1). The other two cases use B_i-T_(i+1).
            # Comparing the two booleans picks the right one for all four
            # combinations.
            diagonals = []
            for i in range(1, n - 1):
                left_half = i <= n // 2 - 1
                lower_end_to_midspan = self.truss_type == "pratt"
                if left_half == lower_end_to_midspan:
                    diagonals.append((T(i), B(i + 1)))
                else:
                    diagonals.append((B(i), T(i + 1)))
            add(GROUP_DIAGONAL, diagonals)

        self.elements = np.array(elements, dtype=int)
        self.member_groups = groups
        self.section_classes = [SECTION_CLASS_OF_GROUP[g] for g in groups]
        self.num_elements = self.elements.shape[0]

        # Node numbers are 1-based, so subtract 1 to index coords.
        p1 = self.coords[self.elements[:, 0] - 1]
        p2 = self.coords[self.elements[:, 1] - 1]
        self.ex = np.column_stack((p1[:, 0], p2[:, 0]))
        self.ey = np.column_stack((p1[:, 1], p2[:, 1]))
        self.lengths = np.hypot(p2[:, 0] - p1[:, 0], p2[:, 1] - p1[:, 1])

    def _build_dofs(self):
        """Build the edof matrix and the boundary conditions (spec 3.3, 3.4).

        Each element row of ``edof`` lists the 1-based DOFs of its start node
        and then its end node: [2a - 1, 2a, 2b - 1, 2b] for nodes a and b.
        CALFEM's ``assem`` uses these rows to place each element stiffness
        matrix in the global matrix, and ``extract_eldisp`` uses them to pick
        the element displacements out of the global displacement vector.

        The constrained DOFs are x and y of the pinned support B_0 and y of
        the roller B_n. They are stored as a numpy integer array, because
        ``solveq`` needs an array of 1-based DOFs.

        Sets ``num_dofs``, ``edof``, ``support_nodes``, ``bc_dofs``,
        ``num_reactions``, ``loaded_nodes`` and ``midspan_node``.
        """
        self.num_dofs = 2 * self.num_nodes
        a, b = self.elements[:, 0], self.elements[:, 1]
        self.edof = np.column_stack((2 * a - 1, 2 * a, 2 * b - 1, 2 * b)).astype(int)

        left, right = self._bottom(0), self._bottom(self.n)
        self.support_nodes = [left, right]
        self.bc_dofs = np.array([2 * left - 1, 2 * left, 2 * right], dtype=int)
        self.num_reactions = self.bc_dofs.size

        # The deck load acts on every bottom-chord node. The support nodes
        # receive P_end (spec 3.5).
        self.loaded_nodes = [self._bottom(i) for i in range(self.n + 1)]
        # n is even, so B_(n/2) lies exactly at midspan.
        self.midspan_node = self._bottom(self.n // 2)

    def _panel_load_vector(self, panels, w):
        """Return the global load vector for a set of loaded panels (spec 3.5).

        Each loaded panel i (between B_i and B_(i+1), 0-based) puts a downward
        load w * L / (2n) on each of its two end nodes. Loads act in -y, on
        DOF 2k of node k (1-based), which is index 2k - 1 in the 0-based array.

        Parameters
        ----------
        panels : iterable of int
            0-based indices of the loaded panels.
        w : float
            Line load on the truss [N/m].

        Returns
        -------
        ndarray, shape (num_dofs, 1)
            Load vector f [N], as CALFEM's ``solveq`` expects.
        """
        f = np.zeros((self.num_dofs, 1))
        half_panel_load = w * self.panel_length / 2.0
        for i in panels:
            for k in (self._bottom(i), self._bottom(i + 1)):
                f[2 * k - 1, 0] -= half_panel_load
        return f

    def solve(self, E, A_c, A_w, w):
        """Analyse the truss for LC-full and the single-panel load cases.

        The model takes the line load w and builds its own load cases
        (spec 3.5, R3):

        * LC-full: all panels loaded. This gives P = w * L / n at the interior
          bottom nodes and P_end = P / 2 at the two support nodes.
        * LC-i, i = 0 ... n - 1: only panel i loaded.

        From the single-panel forces N_e,i it computes the envelope (spec 3.5)

            N_max,e = sum_i max(N_e,i, 0),   N_min,e = sum_i min(N_e,i, 0),

        with forces |N| < N_tol = 1e-9 * w * L treated as zero (spec 3.6).

        Parameters
        ----------
        E : float
            Young's modulus [Pa]. Must be positive.
        A_c : float
            Cross-section area of the chord class [m^2]: bottom chord, top
            chord and end posts. Must be positive.
        A_w : float
            Cross-section area of the web class [m^2]: verticals and
            diagonals. Must be positive.
        w : float
            Line load on the truss [N/m], acting downwards (spec D5).

        Returns
        -------
        a : ndarray, shape (num_dofs,)
            Nodal displacements under LC-full [m].
        r : ndarray, shape (num_dofs,)
            r = K a - f under LC-full [N]. At the support DOFs this is the
            support reaction, including P_end. At free DOFs it is about 0.
        N : ndarray, shape (num_elements,)
            Normal forces under LC-full [N]. Tension is positive.
        N_max : ndarray, shape (num_elements,)
            Largest tension over all panel load patterns [N], >= 0.
        N_min : ndarray, shape (num_elements,)
            Largest compression over all panel load patterns [N], <= 0.

        The method also stores these results on the instance, together with
        the per-case results:

        * ``E``, ``A_c``, ``A_w``, ``w``, ``areas`` (area per element), ``K``
        * ``f_full``, ``a_full``, ``r_full``, ``N_full``,
          ``u_midspan`` (u_y of the midspan node under LC-full [m])
        * ``f_panels``, ``a_panels``, ``r_panels``: shape (n, num_dofs)
        * ``N_panels``: shape (n, num_elements), row i is LC-i
        * ``N_tol``, ``N_max``, ``N_min``
        """
        if not E > 0:
            raise ValueError(f"E must be positive, got {E!r}")
        if not A_c > 0:
            raise ValueError(f"A_c must be positive, got {A_c!r}")
        if not A_w > 0:
            raise ValueError(f"A_w must be positive, got {A_w!r}")

        self.E, self.A_c, self.A_w, self.w = float(E), float(A_c), float(A_w), float(w)

        # Element properties: each member gets the area of its section class
        # (spec 3.3, R1).
        self.areas = np.array(
            [self.A_c if c == CLASS_CHORD else self.A_w for c in self.section_classes]
        )

        # DSM step 1, element stiffness matrices, and step 2, assembly into
        # the global stiffness matrix K (spec 6.1, steps 1 and 2): bar2e gives
        # Ke in global coordinates, and assem adds it at the element's edof
        # DOFs.
        K = np.zeros((self.num_dofs, self.num_dofs))
        for e in range(self.num_elements):
            Ke = cfc.bar2e(self.ex[e], self.ey[e], [self.E, self.areas[e]])
            K = cfc.assem(self.edof[e], K, Ke)
        self.K = K

        # DSM step 3, global load vectors (spec 3.5): LC-full has every panel
        # loaded, and LC-i only panel i.
        self.f_full = self._panel_load_vector(range(self.n), self.w)
        f_cases = [self._panel_load_vector([i], self.w) for i in range(self.n)]

        # DSM steps 4 to 6, per load case: boundary conditions and solution,
        # element displacements, and element normal forces.
        self.a_full, self.r_full, self.N_full = self._solve_load_case(self.f_full)
        results = [self._solve_load_case(f) for f in f_cases]
        self.f_panels = np.array([f[:, 0] for f in f_cases])
        self.a_panels = np.array([res[0] for res in results])
        self.r_panels = np.array([res[1] for res in results])
        self.N_panels = np.array([res[2] for res in results])

        # Midspan vertical displacement under LC-full (spec 6.2). DOF 2k of
        # node k is index 2k - 1.
        self.u_midspan = self.a_full[2 * self.midspan_node - 1]

        # Post-processing, envelope over all panel load patterns (spec 3.5)
        # with the zero-force tolerance (spec 3.6). Single-panel forces below
        # N_tol are set to zero before splitting by sign. The summed envelope
        # values are cleaned the same way.
        self.N_tol = ZERO_FORCE_TOL * abs(self.w) * self.L
        N_cases = np.where(np.abs(self.N_panels) < self.N_tol, 0.0, self.N_panels)
        N_max = np.clip(N_cases, 0.0, None).sum(axis=0)
        N_min = np.clip(N_cases, None, 0.0).sum(axis=0)
        self.N_max = np.where(np.abs(N_max) < self.N_tol, 0.0, N_max)
        self.N_min = np.where(np.abs(N_min) < self.N_tol, 0.0, N_min)

        return self.a_full, self.r_full, self.N_full, self.N_max, self.N_min

    def _solve_load_case(self, f):
        """Solve one load case with the assembled K (spec 6.1, steps 3 to 5).

        Parameters
        ----------
        f : ndarray, shape (num_dofs, 1)
            Global load vector [N].

        Returns
        -------
        a : ndarray, shape (num_dofs,)
            Nodal displacements [m].
        r : ndarray, shape (num_dofs,)
            r = K a - f [N]: the support reactions at the constrained DOFs.
        N : ndarray, shape (num_elements,)
            Normal force of each element [N], tension positive.
        """
        # DSM step 4, boundary conditions and solution (spec 3.4, 6.1 step 3):
        # solveq removes the constrained DOFs (bc_dofs, 1-based, prescribed
        # zero), solves K a = f for the free DOFs, and returns r = K a - f.
        a, r = cfc.solveq(self.K, f, self.bc_dofs)

        # DSM step 5, element displacements (spec 6.1 step 4): each row of
        # ed holds the four edof displacements of one element.
        ed = cfc.extract_eldisp(self.edof, a)

        # DSM step 6, element normal forces (spec 6.1 step 5): bar2s returns
        # N at both member ends, shape (2, 1). They are equal for a bar with
        # no distributed load, and N_e is es[0, 0] (R6).
        N = np.empty(self.num_elements)
        for e in range(self.num_elements):
            es = cfc.bar2s(self.ex[e], self.ey[e], [self.E, self.areas[e]], ed[e])
            N[e] = es[0, 0]

        return a[:, 0], r[:, 0], N
