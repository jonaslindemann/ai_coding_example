r"""
2D truss bridge model: geometry and topology.

This module builds everything about a truss bridge that does not depend on the
material or the loads: where the nodes are, which nodes each member connects,
which global degrees of freedom (DOFs) each member touches (the edof matrix),
and which DOFs are fixed by the supports. TrussBridge.solve() then runs a
linear static analysis with the direct stiffness method, using only
calfem.core functions. Plotting and UI are deliberately not part of this
module.

Conventions (agreed for this project, see bridge_spec.md)
---------------------------------------------------------
* Units: SI (m). The left support is at the origin (0, 0), x points to the
  right and y points upward.
* Node numbering (1-based): the bottom chord left to right (nodes 1..n+1),
  then the top chord left to right.
* DOF numbering (1-based, as CALFEM expects): node i owns the DOFs
  [2i-1, 2i] = [ux, uy].
* Element order: bottom chord, top chord, verticals, diagonals. Each group runs
  left to right.
* Supports: a pin at node 1 (ux and uy fixed) and a roller at node n+1 (uy
  fixed, free to roll horizontally).

Truss types (n panels of width L/n, height h)
---------------------------------------------
* "pratt"  - Trapezoidal: inclined end posts run from each support up to the
             first and last top nodes. Verticals sit at the interior bottom
             nodes, and the diagonals slope down toward midspan.
* "howe"   - Same layout as Pratt, but the diagonals slope down toward the
             supports.
* "warren" - The top nodes sit above the bottom-panel midpoints. There are no
             verticals, and the diagonals alternate up and down.

Example layouts for n = 4 (b = bottom node index, t = top node index)::

    Pratt                         Howe                          Warren
       t1 ---- t2 ---- t3            t1 ---- t2 ---- t3          t0 -- t1 -- t2 -- t3
      / |    \  |  /    | \         / |    /  |  \    | \       / \   / \   / \   / \
     /  |     \ | /     |  \       /  |   /   |   \   |  \     /   \ /   \ /   \ /   \
    b0--b1-----b2------b3--b4     b0--b1-----b2-----b3---b4   b0----b1----b2----b3----b4
"""

import numpy as np
import calfem.core as cfc

#: Allowed values for the ``truss_type`` argument.
TRUSS_TYPES = ("pratt", "howe", "warren")

#: Labels used in :attr:`TrussBridge.member_groups`.
MEMBER_GROUPS = ("bottom", "top", "vertical", "diagonal")


class TrussBridge:
    """Geometry and topology of a simply supported 2D truss bridge.

    Builds the node coordinates, the element connectivity, the CALFEM edof
    matrix and the constrained DOFs for a Pratt, Howe or Warren truss. All
    arrays are built in the constructor, so the object is ready to use as soon
    as it exists. Nothing is computed lazily and nothing is changed later.

    Parameters
    ----------
    truss_type : str
        One of "pratt", "howe", "warren" (case-insensitive).
    L : float
        Span between the supports [m]. Must be > 0.
    h : float
        Height between the top and bottom chord centerlines [m]. Must be > 0.
    n : int
        Number of panels. Must be even and >= 2, so that the truss is
        symmetric about midspan.

    Attributes
    ----------
    truss_type : str
        The truss type, in lower case.
    L, h : float
        Span and height [m].
    n : int
        Number of panels.
    coords : ndarray, shape (j, 2)
        Node coordinates [x, y] in m. Row k holds node k+1 (the rows are
        0-based, the node numbers are 1-based).
    elements : ndarray of int, shape (m, 2)
        Element connectivity: the 1-based start and end node of each member.
    member_groups : list of str
        Group label of each element: "bottom", "top", "vertical" or
        "diagonal". The end posts count as "diagonal".
    dofs : ndarray of int, shape (j, 2)
        1-based global DOFs [ux, uy] of each node. Row k holds node k+1.
    edof : ndarray of int, shape (m, 4)
        Element DOF topology. Row e is [ux_a, uy_a, ux_b, uy_b] for element e
        with end nodes a and b. This is the format that calfem.core.assem and
        calfem.core.extract_eldisp take: DOFs only, no element-number column.
    ex, ey : ndarray, shape (m, 2)
        x and y coordinates of the two ends of each element, in the form
        calfem.core.bar2e and bar2s take.
    bc_dofs : ndarray of int, shape (3,)
        1-based constrained DOFs, in this order: ux and uy of the pin, then uy
        of the roller. Pass these as ``bc`` to calfem.core.solveq.
    support_nodes : tuple of int
        1-based (pin node, roller node).
    loaded_nodes : ndarray of int
        1-based interior bottom-chord nodes, the supports excluded. These are
        the nodes that carry the load P in the spec.
    E, A, P : float or None
        Young's modulus [Pa], cross-sectional area [m^2] and nodal load [N]
        used in the last call to :meth:`solve`. None before solving.
    K : ndarray, shape (2j, 2j) or None
        Global stiffness matrix [N/m], set by :meth:`solve`.
    f : ndarray, shape (2j, 1) or None
        Global load vector [N], set by :meth:`solve`.
    a : ndarray, shape (2j, 1) or None
        Global nodal displacements [m], set by :meth:`solve`. Entry 2i-2 is
        ux of node i and entry 2i-1 is uy of node i (0-based indexing).
    r : ndarray, shape (2j, 1) or None
        Global reaction vector [N], set by :meth:`solve`. Non-zero only at
        bc_dofs, up to round-off.
    ed : ndarray, shape (m, 4) or None
        Element displacements [m], set by :meth:`solve`.
    N : ndarray, shape (m,) or None
        Normal force in each member [N], tension positive, set by
        :meth:`solve`.

    Raises
    ------
    ValueError
        If truss_type is unknown, n is not an even integer >= 2, or L or h is
        not positive.
    TypeError
        If n is not an integer.

    Notes
    -----
    All three layouts are statically determinate: m + r = 2j, where m is the
    number of members, r = 3 is the number of support reactions and j is the
    number of nodes.

    ======  =========  =========
    Type    Nodes j    Members m
    ======  =========  =========
    Pratt   2n         4n - 3
    Howe    2n         4n - 3
    Warren  2n + 1     4n - 1
    ======  =========  =========
    """

    def __init__(self, truss_type, L, h, n):
        # --- Input validation: reject bad input, never fill in a default ----
        if not isinstance(truss_type, str) or truss_type.lower() not in TRUSS_TYPES:
            raise ValueError(f"truss_type must be one of {TRUSS_TYPES}, got {truss_type!r}")
        # bool is a subclass of int in Python, so exclude it explicitly
        if isinstance(n, bool) or not isinstance(n, (int, np.integer)):
            raise TypeError(f"n must be an integer, got {type(n).__name__}")
        # n even: the diagonal pattern mirrors about the midspan node
        if n < 2 or n % 2 != 0:
            raise ValueError(f"n must be an even integer >= 2, got {n}")
        # "not x > 0" also catches NaN, which "x <= 0" would let through
        if not L > 0:
            raise ValueError(f"L must be positive, got {L}")
        if not h > 0:
            raise ValueError(f"h must be positive, got {h}")

        self.truss_type = truss_type.lower()
        self.L = float(L)
        self.h = float(h)
        self.n = int(n)

        # Build in dependency order: coordinates -> connectivity -> DOFs/edof
        self._build_geometry()
        self._build_topology()
        self._build_dofs()

        # Analysis inputs and results, filled in by solve()
        self.E = self.A = self.P = None
        self.K = self.f = self.a = self.r = self.ed = self.N = None

    # ------------------------------------------------------------------
    # Node numbering helpers
    # ------------------------------------------------------------------

    def _bottom(self, i):
        """Return the 1-based node number of bottom-chord node i.

        Parameters
        ----------
        i : int
            Bottom-node index, 0..n. The node is at x = i * L / n, y = 0.

        Returns
        -------
        int
            The node number, i + 1. The bottom chord is numbered first, so
            the left support is node 1 and the right support is node n + 1.
        """
        return i + 1

    def _top(self, i):
        """Return the 1-based node number of top-chord node i.

        The top-node indexing depends on the truss type.

        * Pratt/Howe: i = 1..n-1 is the top node directly above bottom node
          i. There is no top node above a support, because the end posts are
          inclined. Top nodes are numbered from n + 2, so top node i is node
          n + 1 + i.
        * Warren: i = 0..n-1 is the top node above the midpoint of panel i,
          at x = (i + 0.5) * L / n. Top node i is node n + 2 + i.

        Parameters
        ----------
        i : int
            Top-node index, as described above.

        Returns
        -------
        int
            The 1-based node number.
        """
        n = self.n
        if self.truss_type == "warren":
            # Warren indices start at 0, so add one more to start at n + 2
            return n + 2 + i
        # Pratt/Howe indices start at 1, so n + 1 + 1 = n + 2 for the first one
        return n + 1 + i

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_geometry(self):
        """Compute the node coordinates.

        The bottom chord gets n + 1 equally spaced nodes from (0, 0) to
        (L, 0). The top chord at y = h gets:

        * Pratt/Howe: n - 1 nodes above the interior bottom nodes,
          x = i * L / n for i = 1..n-1.
        * Warren: n nodes above the panel midpoints,
          x = (i + 0.5) * L / n for i = 0..n-1.

        Sets
        ----
        coords : ndarray, shape (j, 2)
            The bottom-chord rows first, then the top-chord rows. This order
            is what makes ``_bottom`` and ``_top`` correct.
        """
        n, L, h = self.n, self.L, self.h
        dx = L / n  # panel width

        # Bottom chord: n + 1 nodes, including both supports
        bottom = [[i * dx, 0.0] for i in range(n + 1)]

        if self.truss_type == "warren":
            # One top node at the midpoint of each panel
            top = [[(i + 0.5) * dx, h] for i in range(n)]
        else:
            # Top nodes only above the interior bottom nodes (inclined end posts)
            top = [[i * dx, h] for i in range(1, n)]

        self.coords = np.array(bottom + top, dtype=float)

    def _build_topology(self):
        """Build the element connectivity and the member-group labels.

        Members are added group by group, each group left to right:

        1. Bottom chord: n members between neighbouring bottom nodes.
        2. Top chord: members between neighbouring top nodes. Pratt/Howe have
           n - 2 of them, Warren has n - 1.
        3. Verticals (Pratt/Howe only): n - 1 members from each interior
           bottom node to the top node above it.
        4. Diagonals, one panel at a time.

           * Pratt/Howe: one diagonal per panel, n in total. The first and
             last are the inclined end posts. The interior diagonals go in the
             direction set by the truss type:

             - Pratt slopes down toward midspan. In the left half the
               diagonal runs from the top node on the support side to the
               bottom node nearer midspan. The right half is the mirror image.
             - Howe is the mirror of Pratt and slopes down toward the
               supports.

           * Warren: two diagonals per panel, 2n in total. One rises from the
             panel's left bottom node to its top midpoint node, the other
             falls from there to the right bottom node.

        Sets
        ----
        elements : ndarray of int, shape (m, 2)
            The 1-based end nodes of each member.
        member_groups : list of str
            The group label of each member, in the same order.
        """
        n = self.n
        B, T = self._bottom, self._top  # short aliases for readability
        elems = []
        groups = []

        def add(a, b, group):
            """Append member a -> b (1-based nodes) with its group label."""
            elems.append([a, b])
            groups.append(group)

        # 1. Bottom chord: B(i) -- B(i+1) for every panel
        for i in range(n):
            add(B(i), B(i + 1), "bottom")

        if self.truss_type == "warren":
            # 2. Top chord: links the n midpoint nodes -> n - 1 members
            for i in range(n - 1):
                add(T(i), T(i + 1), "top")
            # 4. Diagonals: a "/\" in every panel (up to the midpoint, then down)
            for i in range(n):
                add(B(i), T(i), "diagonal")      # rising leg
                add(T(i), B(i + 1), "diagonal")  # falling leg
        else:
            # 2. Top chord: links top nodes 1..n-1 -> n - 2 members
            #    (no members when n = 2, since there is only one top node)
            for i in range(1, n - 1):
                add(T(i), T(i + 1), "top")
            # 3. Verticals: each interior bottom node to the top node above it
            for i in range(1, n):
                add(B(i), T(i), "vertical")
            # 4. Diagonals: one per panel; panel i spans x_i .. x_{i+1}
            half = n // 2  # panels 0..half-1 are left of midspan
            for i in range(n):
                if i == 0:
                    # Left end post: support B(0) up to the first top node
                    add(B(0), T(1), "diagonal")
                elif i == n - 1:
                    # Right end post: the last top node down to support B(n)
                    add(T(n - 1), B(n), "diagonal")
                elif self.truss_type == "pratt":
                    # Pratt: the diagonal's low end is nearer midspan
                    if i < half:
                        add(T(i), B(i + 1), "diagonal")  # left half: "\"
                    else:
                        add(B(i), T(i + 1), "diagonal")  # right half: "/"
                else:  # howe
                    # Howe: the diagonal's low end is nearer the support
                    if i < half:
                        add(B(i), T(i + 1), "diagonal")  # left half: "/"
                    else:
                        add(T(i), B(i + 1), "diagonal")  # right half: "\"

        self.elements = np.array(elems, dtype=int)
        self.member_groups = groups

    def _build_dofs(self):
        """Build the DOF numbering, the edof matrix, the element coordinates
        and the boundary conditions.

        DOF numbering
            Each node has two translational DOFs. Node i (1-based) owns the
            global DOFs 2i - 1 (ux) and 2i (uy). The global system therefore
            has 2j DOFs.

        edof matrix
            For element e with end nodes a and b, row e of edof is
            ``[2a-1, 2a, 2b-1, 2b]``: the global DOFs of the element's four
            local DOFs [u1, v1, u2, v2]. calfem.core.assem uses it to add each
            4x4 element stiffness matrix to the global matrix, and
            calfem.core.extract_eldisp uses it to pick each element's
            displacements out of the global solution vector.

        Element coordinates
            ex[e] = [x_a, x_b] and ey[e] = [y_a, y_b], the end coordinates in
            the form bar2e and bar2s take.

        Boundary-condition DOFs
            The pin at the left support (node 1) fixes ux and uy, giving DOFs
            1 and 2. The roller at the right support (node n + 1) rolls
            horizontally, so only uy is fixed: DOF 2(n+1). The result is three
            constrained DOFs, which matches the three support reactions.

        Sets
        ----
        dofs, edof, ex, ey, bc_dofs, support_nodes, loaded_nodes
            See the class docstring.
        """
        j = self.n_nodes
        node_numbers = np.arange(1, j + 1)  # 1..j

        # Node i -> [2i - 1, 2i] = [ux, uy]
        self.dofs = np.column_stack([2 * node_numbers - 1, 2 * node_numbers])

        # 0-based row indices of each element's start (a) and end (b) node
        a = self.elements[:, 0] - 1
        b = self.elements[:, 1] - 1

        # edof row = [DOFs of node a, DOFs of node b]
        self.edof = np.hstack([self.dofs[a], self.dofs[b]])

        # End coordinates of each element, one row per element
        self.ex = np.column_stack([self.coords[a, 0], self.coords[b, 0]])
        self.ey = np.column_stack([self.coords[a, 1], self.coords[b, 1]])

        # Supports sit at the two ends of the bottom chord
        pin = self._bottom(0)        # node 1, at (0, 0)
        roller = self._bottom(self.n)  # node n + 1, at (L, 0)
        self.support_nodes = (pin, roller)

        # Pin: ux and uy fixed. Roller: only uy fixed (it rolls in x).
        self.bc_dofs = np.array(
            [self.dofs[pin - 1, 0], self.dofs[pin - 1, 1], self.dofs[roller - 1, 1]],
            dtype=int,
        )

        # Load P goes on every bottom-chord node between the supports
        self.loaded_nodes = np.array([self._bottom(i) for i in range(1, self.n)], dtype=int)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def solve(self, E, A, P):
        """Run a linear static analysis with the direct stiffness method.

        Uses only calfem.core functions for the mechanics: bar2e, assem,
        solveq, extract_eldisp and bar2s.

        Parameters
        ----------
        E : float
            Young's modulus [Pa], the same for all members. Must be > 0.
        A : float
            Cross-sectional area [m^2], the same for all members. Must be > 0.
        P : float
            Load [N] at each interior bottom-chord node, positive downward.
            Any finite value is accepted, so a negative P acts upward.

        Returns
        -------
        a : ndarray, shape (2j, 1)
            Nodal displacements [m].
        r : ndarray, shape (2j, 1)
            Reaction forces [N] in the global x/y directions.
        N : ndarray, shape (m,)
            Normal force in each member [N], tension positive.

        All three results, plus K, f and ed, are also stored as attributes.

        Raises
        ------
        ValueError
            If E or A is not positive, or P is not finite.
        """
        # Input checks: reject bad input, never fill in a default
        if not E > 0:
            raise ValueError(f"E must be positive, got {E}")
        if not A > 0:
            raise ValueError(f"A must be positive, got {A}")
        if not np.isfinite(P):
            raise ValueError(f"P must be finite, got {P}")
        self.E, self.A, self.P = float(E), float(A), float(P)

        # Spec: "Same value for all members" -> one ep = [E, A] for every bar
        ep = [self.E, self.A]
        n_dofs = self.n_dofs

        # --- DSM step 1: element stiffness matrices -----------------------
        # --- DSM step 2: assembly into the global stiffness matrix --------
        # Spec: "Linear elastic material, small displacements, pin-jointed
        # members, axial force only" -> 2-node bar element (bar2e), whose
        # 4x4 matrix in global coordinates is added at the element's edof
        # DOFs by assem.
        K = np.zeros((n_dofs, n_dofs))
        for e in range(self.n_elements):
            Ke = cfc.bar2e(self.ex[e], self.ey[e], ep)
            cfc.assem(self.edof[e], K, Ke)

        # --- DSM step 3: global load vector -------------------------------
        # Spec: "Loads: P at each interior bottom-chord node (except the
        # supports). Positive downward." y points upward (left support at
        # the origin, top chord at y = h), so P adds -P to uy of each
        # loaded node.
        f = np.zeros((n_dofs, 1))
        for node in self.loaded_nodes:
            f[self.dofs[node - 1, 1] - 1, 0] = -self.P

        # --- DSM step 4: boundary conditions and solution -----------------
        # Spec: "a pin at the left end and a roller (rolls in the horizontal
        # direction) at the right end" -> bc_dofs = [ux, uy of the pin, uy of
        # the roller]. All prescribed displacements are zero (solveq's
        # default when bcVal is omitted). solveq returns the displacements a
        # and r = K a - f, which holds the reactions at the constrained DOFs
        # (spec outputs: "nodal displacements" and "reactions").
        a, r = cfc.solveq(K, f, self.bc_dofs)

        # --- DSM step 5: element displacements ----------------------------
        # Pick each element's 4 global DOF displacements out of a via edof.
        ed = cfc.extract_eldisp(self.edof, a)

        # --- DSM step 6: element normal forces ----------------------------
        # Spec output "normal forces", sign convention "tension is positive".
        # bar2s returns N at 2 points along the bar (both ends). With no
        # distributed load (eq not given) N is constant along the bar, so the
        # first value is stored.
        N = np.zeros(self.n_elements)
        for e in range(self.n_elements):
            es = cfc.bar2s(self.ex[e], self.ey[e], ep, ed[e])
            N[e] = es[0, 0]

        self.K, self.f, self.a, self.r, self.ed, self.N = K, f, a, r, ed, N
        return a, r, N

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    @property
    def n_nodes(self):
        """int: The number of nodes, j."""
        return self.coords.shape[0]

    @property
    def n_elements(self):
        """int: The number of members, m."""
        return self.elements.shape[0]

    @property
    def n_dofs(self):
        """int: The number of global DOFs, 2j (two translations per node)."""
        return 2 * self.n_nodes

    @property
    def n_reactions(self):
        """int: The number of support reaction components, r.

        There is one reaction per constrained DOF: 2 at the pin and 1 at the
        roller, so r = 3.
        """
        return self.bc_dofs.size
