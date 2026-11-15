"""Tests for the geometry and topology in truss_model.TrussBridge."""

import numpy as np
import pytest

from truss_model import TrussBridge, TRUSS_TYPES

L, H = 12.0, 2.0
NS = (2, 4, 6)


def expected_counts(truss_type, n):
    """(nodes j, members m, constrained DOFs r) from the agreed layouts."""
    if truss_type == "warren":
        # n+1 bottom nodes + n top nodes; n bottom + (n-1) top + 2n diagonals
        return 2 * n + 1, 4 * n - 1, 3
    # Pratt/Howe trapezoidal: n+1 bottom + (n-1) top nodes;
    # n bottom + (n-2) top + (n-1) verticals + n diagonals (incl. end posts)
    return 2 * n, 4 * n - 3, 3


@pytest.mark.parametrize("truss_type", TRUSS_TYPES)
@pytest.mark.parametrize("n", NS)
def test_counts(truss_type, n):
    t = TrussBridge(truss_type, L, H, n)
    j, m, r = expected_counts(truss_type, n)

    assert t.n_nodes == j
    assert t.n_elements == m
    assert t.n_reactions == r

    assert t.coords.shape == (j, 2)
    assert t.elements.shape == (m, 2)
    assert t.edof.shape == (m, 4)
    assert t.ex.shape == (m, 2) and t.ey.shape == (m, 2)
    assert len(t.member_groups) == m


@pytest.mark.parametrize("truss_type", TRUSS_TYPES)
@pytest.mark.parametrize("n", NS)
def test_statical_determinacy(truss_type, n):
    t = TrussBridge(truss_type, L, H, n)
    assert t.n_elements + t.n_reactions == 2 * t.n_nodes


@pytest.mark.parametrize("truss_type", TRUSS_TYPES)
@pytest.mark.parametrize("n", NS)
def test_bc_dofs(truss_type, n):
    t = TrussBridge(truss_type, L, H, n)
    roller = n + 1
    np.testing.assert_array_equal(t.bc_dofs, [1, 2, 2 * roller])
    np.testing.assert_allclose(t.coords[0], [0.0, 0.0])
    np.testing.assert_allclose(t.coords[roller - 1], [L, 0.0])


@pytest.mark.parametrize("truss_type", TRUSS_TYPES)
@pytest.mark.parametrize("n", NS)
def test_topology_consistency(truss_type, n):
    t = TrussBridge(truss_type, L, H, n)

    # Every node is connected, no duplicate or zero-length members
    assert set(t.elements.ravel()) == set(range(1, t.n_nodes + 1))
    assert len({tuple(sorted(e)) for e in t.elements}) == t.n_elements
    lengths = np.hypot(np.diff(t.ex, axis=1), np.diff(t.ey, axis=1))
    assert np.all(lengths > 0)

    # edof rows match node DOFs [2i-1, 2i] of the element's end nodes
    a, b = t.elements[:, 0], t.elements[:, 1]
    expected_edof = np.column_stack([2 * a - 1, 2 * a, 2 * b - 1, 2 * b])
    np.testing.assert_array_equal(t.edof, expected_edof)
    assert t.edof.min() == 1 and t.edof.max() == t.n_dofs

    # Loaded nodes: interior bottom-chord nodes only
    np.testing.assert_array_equal(t.loaded_nodes, np.arange(2, n + 1))


def _interior_diagonals_slope_down_toward_midspan(t):
    """True/False per interior diagonal (end posts excluded)."""
    mid = t.L / 2
    result = []
    for (a, b), g in zip(t.elements, t.member_groups):
        if g != "diagonal":
            continue
        pa, pb = t.coords[a - 1], t.coords[b - 1]
        if np.isclose(min(pa[0], pb[0]), 0.0) or np.isclose(max(pa[0], pb[0]), t.L):
            continue  # end post
        low, high = (pa, pb) if pa[1] < pb[1] else (pb, pa)
        result.append(abs(low[0] - mid) < abs(high[0] - mid))
    return result


@pytest.mark.parametrize("n", (4, 6))
def test_pratt_diagonals_slope_down_toward_midspan(n):
    t = TrussBridge("pratt", L, H, n)
    flags = _interior_diagonals_slope_down_toward_midspan(t)
    assert flags and all(flags)


@pytest.mark.parametrize("n", (4, 6))
def test_howe_diagonals_slope_down_toward_supports(n):
    t = TrussBridge("howe", L, H, n)
    flags = _interior_diagonals_slope_down_toward_midspan(t)
    assert flags and not any(flags)


@pytest.mark.parametrize("bad_n", (0, 1, 3, 5, -2))
def test_invalid_n(bad_n):
    with pytest.raises(ValueError):
        TrussBridge("pratt", L, H, bad_n)


def test_invalid_type():
    with pytest.raises(ValueError):
        TrussBridge("k-truss", L, H, 4)


# ----------------------------------------------------------------------
# solve(): verification against equilibrium and hand calculations
# ----------------------------------------------------------------------
# Test inputs only. These are not model defaults.
E_T, A_T, P_T = 200e9, 1e-3, 10e3  # Pa, m^2, N


def _moment(t, x):
    """Bending moment at x of a simply supported beam with P at each interior
    bottom node (sagging positive). Used for method-of-sections checks."""
    R = (t.n - 1) * t.P / 2
    xs = t.coords[t.loaded_nodes - 1, 0]
    return R * x - sum(t.P * (x - xk) for xk in xs if xk < x)


def _member(t, n1, n2):
    """0-based index of the member connecting nodes n1 and n2."""
    for e, (a, b) in enumerate(t.elements):
        if {a, b} == {n1, n2}:
            return e
    raise KeyError((n1, n2))


@pytest.mark.parametrize("truss_type", TRUSS_TYPES)
@pytest.mark.parametrize("n", NS)
def test_solve_shapes_and_storage(truss_type, n):
    t = TrussBridge(truss_type, L, H, n)
    a, r, N = t.solve(E_T, A_T, P_T)
    assert a.shape == (t.n_dofs, 1) and r.shape == (t.n_dofs, 1)
    assert N.shape == (t.n_elements,)
    assert t.a is a and t.r is r and t.N is N


@pytest.mark.parametrize("truss_type", TRUSS_TYPES)
@pytest.mark.parametrize("n", NS)
def test_global_equilibrium(truss_type, n):
    t = TrussBridge(truss_type, L, H, n)
    a, r, N = t.solve(E_T, A_T, P_T)
    tol = 1e-8 * P_T * n

    # Supports have zero displacement
    np.testing.assert_allclose(a[t.bc_dofs - 1], 0.0, atol=0)
    # Reactions are zero at the free DOFs
    free = np.setdiff1d(np.arange(1, t.n_dofs + 1), t.bc_dofs)
    np.testing.assert_allclose(r[free - 1], 0.0, atol=tol)
    # Sum Fx = 0, sum Fy = 0: horizontal pin reaction 0, R_pin + R_roller = (n-1) P
    rx_pin, ry_pin, ry_roller = r[t.bc_dofs - 1, 0]
    assert abs(rx_pin) < tol
    assert ry_pin + ry_roller == pytest.approx((n - 1) * P_T, rel=1e-10)
    # Symmetric loading -> equal vertical reactions
    assert ry_pin == pytest.approx((n - 1) * P_T / 2, rel=1e-10)
    assert ry_roller == pytest.approx((n - 1) * P_T / 2, rel=1e-10)


@pytest.mark.parametrize("truss_type", TRUSS_TYPES)
@pytest.mark.parametrize("n", NS)
def test_nodal_equilibrium(truss_type, n):
    """At every node, member forces + external load + reaction sum to zero."""
    t = TrussBridge(truss_type, L, H, n)
    a, r, N = t.solve(E_T, A_T, P_T)
    resid = np.zeros((t.n_nodes, 2))
    for e, (na, nb) in enumerate(t.elements):
        d = t.coords[nb - 1] - t.coords[na - 1]
        u = d / np.linalg.norm(d)
        # Tension pulls each end node toward the other end
        resid[na - 1] += N[e] * u
        resid[nb - 1] -= N[e] * u
    resid += t.f.reshape(-1, 2) + r.reshape(-1, 2)
    np.testing.assert_allclose(resid, 0.0, atol=1e-8 * P_T * n)


@pytest.mark.parametrize("n", (4, 6))
def test_pratt_method_of_sections(n):
    """Pratt: the top chord member next to midspan carries -M(L/2)/h, and the
    centre vertical is a zero-force member."""
    t = TrussBridge("pratt", L, H, n)
    t.solve(E_T, A_T, P_T)
    k = n // 2
    e_top = _member(t, t._top(k - 1), t._top(k))
    assert t.N[e_top] == pytest.approx(-_moment(t, L / 2) / H, rel=1e-9)
    e_vert = _member(t, t._bottom(k), t._top(k))
    assert abs(t.N[e_vert]) < 1e-8 * P_T


@pytest.mark.parametrize("n", (2, 4, 6))
def test_howe_method_of_sections(n):
    """Howe: the bottom chord member next to midspan carries +M(L/2)/h."""
    t = TrussBridge("howe", L, H, n)
    t.solve(E_T, A_T, P_T)
    k = n // 2
    e_bot = _member(t, t._bottom(k - 1), t._bottom(k))
    assert t.N[e_bot] == pytest.approx(_moment(t, L / 2) / H, rel=1e-9)


@pytest.mark.parametrize("n", (2, 4, 6))
def test_warren_method_of_sections(n):
    """Warren: bottom chord member in panel i carries +M(x_mid,i)/h, where
    x_mid,i is the x of the top node above that panel."""
    t = TrussBridge("warren", L, H, n)
    t.solve(E_T, A_T, P_T)
    for i in range(n):
        e = _member(t, t._bottom(i), t._bottom(i + 1))
        x_top = t.coords[t._top(i) - 1, 0]
        assert t.N[e] == pytest.approx(_moment(t, x_top) / H, rel=1e-9)


@pytest.mark.parametrize("truss_type", TRUSS_TYPES)
def test_symmetry_and_sign(truss_type):
    """Symmetric structure and loading -> symmetric deflection, sagging
    downward. Bottom chord in tension, top chord in compression."""
    n = 6
    t = TrussBridge(truss_type, L, H, n)
    a, r, N = t.solve(E_T, A_T, P_T)
    uy_bottom = np.array([a[2 * t._bottom(i) - 1, 0] for i in range(n + 1)])
    np.testing.assert_allclose(uy_bottom, uy_bottom[::-1], rtol=1e-9, atol=1e-15)
    assert np.all(uy_bottom[1:-1] < 0)
    groups = np.array(t.member_groups)
    assert np.all(N[groups == "bottom"] > 0)
    assert np.all(N[groups == "top"] < 0)


def test_linearity_in_P_and_EA():
    """N scales with P and is independent of E*A (statically determinate),
    while a scales with P / (E*A)."""
    t = TrussBridge("pratt", L, H, 4)
    a1, _, N1 = (x.copy() for x in t.solve(E_T, A_T, P_T))
    a2, _, N2 = t.solve(2 * E_T, A_T, 3 * P_T)
    np.testing.assert_allclose(N2, 3 * N1, rtol=1e-10, atol=1e-8 * P_T)
    np.testing.assert_allclose(a2, 1.5 * a1, rtol=1e-10, atol=1e-18)


@pytest.mark.parametrize("E, A, P", [(0, A_T, P_T), (E_T, -1, P_T), (E_T, A_T, np.nan)])
def test_solve_invalid_input(E, A, P):
    with pytest.raises(ValueError):
        TrussBridge("pratt", L, H, 4).solve(E, A, P)
