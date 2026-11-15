"""Property-based tests for TrussBridge.solve().

Every test is parametrized over all truss types and n = 2, 4, 6, 8. The tests
check physical properties that must hold for any linear elastic, statically
determinate truss, so no reference values are needed:

* global equilibrium
* linearity in P
* symmetry under symmetric loading
* determinacy: forces independent of E and A
* superposition of load cases
"""

import numpy as np
import pytest

from truss_model import TrussBridge, TRUSS_TYPES

# Test inputs only (SI). These are not model defaults.
L, H = 20.0, 3.0      # m
E, A = 210e9, 0.01    # Pa, m^2
P = 10e3              # N

NS = (2, 4, 6, 8)
EPS = np.finfo(float).eps

params = pytest.mark.parametrize("n", NS)
types = pytest.mark.parametrize("truss_type", TRUSS_TYPES)


def solved(truss_type, n, E=E, A=A, P=P):
    """Build and solve a truss. Returns the model with copies of (a, r, N)."""
    t = TrussBridge(truss_type, L, H, n)
    a, r, N = t.solve(E, A, P)
    return t, a.copy(), r.copy(), N.copy()


def force_tol(n, P=P):
    """Absolute force tolerance at machine-precision level. Scales with the
    total load and the number of DOFs that round-off accumulates over."""
    return 100 * EPS * abs(P) * max(n - 1, 1) * 4 * n


def disp_tol(a):
    """Absolute displacement tolerance at machine-precision level."""
    return 100 * EPS * np.max(np.abs(a)) * a.size


# ----------------------------------------------------------------------
# Global equilibrium
# ----------------------------------------------------------------------

@types
@params
def test_global_equilibrium(truss_type, n):
    """Sum Fx = 0, sum Fy = 0, sum M about the origin = 0 for reactions + loads."""
    t, a, r, N = solved(truss_type, n)
    f = t.f

    # Only the constrained DOFs carry reactions
    react = np.zeros_like(r)
    react[t.bc_dofs - 1] = r[t.bc_dofs - 1]

    fx = react[0::2, 0] + f[0::2, 0]
    fy = react[1::2, 0] + f[1::2, 0]
    x, y = t.coords[:, 0], t.coords[:, 1]

    tol = force_tol(n)
    assert abs(fx.sum()) <= tol
    assert abs(fy.sum()) <= tol
    assert abs(np.sum(x * fy - y * fx)) <= tol * L

    # The reactions balance the total applied load (n - 1) P
    assert react[1::2, 0].sum() == pytest.approx((n - 1) * P, rel=100 * EPS, abs=tol)

    # Reactions at the free DOFs are zero (K a = f there)
    free = np.setdiff1d(np.arange(t.n_dofs), t.bc_dofs - 1)
    assert np.max(np.abs(r[free, 0])) <= tol


# ----------------------------------------------------------------------
# Linearity
# ----------------------------------------------------------------------

@types
@params
def test_linearity_doubling_P(truss_type, n):
    """Doubling P doubles every displacement, reaction and normal force."""
    t1, a1, r1, N1 = solved(truss_type, n, P=P)
    t2, a2, r2, N2 = solved(truss_type, n, P=2 * P)

    np.testing.assert_allclose(a2, 2 * a1, rtol=1e-12, atol=disp_tol(a2))
    np.testing.assert_allclose(r2, 2 * r1, rtol=1e-12, atol=force_tol(n, 2 * P))
    np.testing.assert_allclose(N2, 2 * N1, rtol=1e-12, atol=force_tol(n, 2 * P))


# ----------------------------------------------------------------------
# Symmetry
# ----------------------------------------------------------------------

def mirror_node_map(t):
    """For each 1-based node, the 1-based node mirrored about x = L/2."""
    mapping = {}
    for k, (x, y) in enumerate(t.coords):
        target = np.array([t.L - x, y])
        dist = np.linalg.norm(t.coords - target, axis=1)
        j = int(np.argmin(dist))
        assert dist[j] < 1e-12 * t.L, f"node {k + 1} has no mirror image"
        mapping[k + 1] = j + 1
    return mapping


def mirror_element_map(t):
    """For each 0-based element, the 0-based element in the mirrored position."""
    nodes = mirror_node_map(t)
    lookup = {frozenset(map(int, e)): i for i, e in enumerate(t.elements)}
    mapping = {}
    for i, (a, b) in enumerate(t.elements):
        key = frozenset((nodes[int(a)], nodes[int(b)]))
        assert key in lookup, f"element {i + 1} has no mirror image"
        mapping[i] = lookup[key]
    return mapping


@types
@params
def test_symmetry_mirrored_members(truss_type, n):
    """Under symmetric loading, mirrored members carry equal forces. Also checks
    that the geometry itself is symmetric (every node and member has a mirror)."""
    t, a, r, N = solved(truss_type, n)
    emap = mirror_element_map(t)
    assert t.member_groups == [t.member_groups[emap[i]] for i in range(t.n_elements)]
    N_mirror = N[[emap[i] for i in range(t.n_elements)]]
    np.testing.assert_allclose(N, N_mirror, rtol=1e-12, atol=force_tol(n))


@types
@params
def test_symmetry_vertical_deflection_and_reactions(truss_type, n):
    """Vertical displacements are mirror-symmetric and the vertical reactions are
    equal. ux is not compared: the pin/roller support pair is not symmetric in x."""
    t, a, r, N = solved(truss_type, n)
    nmap = mirror_node_map(t)
    uy = a[1::2, 0]
    uy_mirror = np.array([uy[nmap[k] - 1] for k in range(1, t.n_nodes + 1)])
    np.testing.assert_allclose(uy, uy_mirror, rtol=1e-12, atol=disp_tol(a))

    pin, roller = t.support_nodes
    assert r[2 * pin - 1, 0] == pytest.approx(r[2 * roller - 1, 0], rel=1e-12)


# ----------------------------------------------------------------------
# Determinacy
# ----------------------------------------------------------------------

@types
@params
@pytest.mark.parametrize("factor_on", ("E", "A"))
def test_determinacy_stiffness_scaling(truss_type, n, factor_on):
    """A statically determinate truss: scaling E or A by 10 leaves N and r
    unchanged and divides all displacements by 10."""
    t1, a1, r1, N1 = solved(truss_type, n)
    if factor_on == "E":
        t2, a2, r2, N2 = solved(truss_type, n, E=10 * E)
    else:
        t2, a2, r2, N2 = solved(truss_type, n, A=10 * A)

    np.testing.assert_allclose(N2, N1, rtol=1e-12, atol=force_tol(n))
    np.testing.assert_allclose(r2, r1, rtol=1e-12, atol=force_tol(n))
    np.testing.assert_allclose(a2, a1 / 10, rtol=1e-12, atol=disp_tol(a1))


# ----------------------------------------------------------------------
# Superposition
# ----------------------------------------------------------------------

# Load-case pairs (P1, P2): same sign, different magnitude, opposite sign
LOAD_CASES = [(P, 2.5 * P), (P, -0.4 * P), (3.7 * P, -3.7 * P)]


@types
@params
@pytest.mark.parametrize("P1, P2", LOAD_CASES)
def test_superposition(truss_type, n, P1, P2):
    """solve(P1 + P2) equals solve(P1) + solve(P2) for a, r and N.

    The model has only the spec's load pattern (P at every interior
    bottom-chord node), so the load cases differ in magnitude and sign,
    not in pattern."""
    _, a1, r1, N1 = solved(truss_type, n, P=P1)
    _, a2, r2, N2 = solved(truss_type, n, P=P2)
    _, a12, r12, N12 = solved(truss_type, n, P=P1 + P2)

    scale = max(abs(P1), abs(P2))
    a_ref = np.maximum(np.abs(a1), np.abs(a2))
    np.testing.assert_allclose(a12, a1 + a2, rtol=1e-12, atol=disp_tol(a_ref) + 1e-30)
    np.testing.assert_allclose(r12, r1 + r2, rtol=1e-12, atol=force_tol(n, scale))
    np.testing.assert_allclose(N12, N1 + N2, rtol=1e-12, atol=force_tol(n, scale))
