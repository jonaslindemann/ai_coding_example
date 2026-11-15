"""Physics-based property tests for TrussBridge.solve (spec section 8).

Parametrized over all truss types and n = 2, 4, 6, 8, 10. A_c and A_w are
deliberately different, so that the section classes actually matter.

Tolerances:

* Forces are compared with an absolute tolerance of FORCE_ATOL = 1e-9 * W,
  the zero-force tolerance N_tol of spec 3.6, plus rtol = 1e-9.
* Equilibrium sums use EQ_ATOL = 1e-12 * W, which is "machine precision" in
  this test file: about 10^4 times the double-precision epsilon, to allow for
  round-off in the solve.
* Displacements use rtol = 1e-9 plus an absolute tolerance of 1e-9 times the
  largest displacement.
"""

import numpy as np
import pytest

from truss_model import TrussBridge

TYPES = ["pratt", "howe", "warren"]
N_VALUES = [2, 4, 6, 8, 10]

L = 20.0
H = 3.0
E = 210.0e9
A_C = 0.010
A_W = 0.004
W_LOAD = 5.0e3          # N/m
W_TOTAL = W_LOAD * L    # N

RTOL = 1e-9
FORCE_ATOL = 1e-9 * W_TOTAL
EQ_ATOL = 1e-12 * W_TOTAL

params = pytest.mark.parametrize("n", N_VALUES)
types = pytest.mark.parametrize("truss_type", TYPES)


def solved(truss_type, n, E=E, A_c=A_C, A_w=A_W, w=W_LOAD):
    b = TrussBridge(truss_type, L, H, n)
    b.solve(E, A_c, A_w, w)
    return b


def assert_forces_close(actual, expected):
    np.testing.assert_allclose(actual, expected, rtol=RTOL, atol=FORCE_ATOL)


def assert_displacements_close(actual, expected):
    atol = 1e-9 * np.max(np.abs(expected))
    np.testing.assert_allclose(actual, expected, rtol=RTOL, atol=atol)


def all_load_cases(b):
    """Yield (name, f, a, r) for LC-full and every single-panel case."""
    yield "LC-full", b.f_full[:, 0], b.a_full, b.r_full
    for i in range(b.n):
        yield f"LC-{i}", b.f_panels[i], b.a_panels[i], b.r_panels[i]


# 1. Global equilibrium ------------------------------------------------------

@types
@params
def test_global_equilibrium(truss_type, n):
    """Support reactions balance the applied loads: forces in x and y, and moment.

    r = K a - f sums to zero over all x DOFs (or all y DOFs) for any a,
    because a rigid translation produces no forces. Summing r over all DOFs
    would therefore pass even if the solution were wrong. So the test first
    checks that r vanishes at the free DOFs, and then checks equilibrium using
    only the reactions at the support DOFs, including moment equilibrium.
    """
    b = solved(truss_type, n)
    x, y = b.coords[:, 0], b.coords[:, 1]
    support = np.zeros(b.num_dofs, dtype=bool)
    support[b.bc_dofs - 1] = True

    for name, f, a, r in all_load_cases(b):
        # Free DOFs carry no reaction: K a = f is satisfied there.
        np.testing.assert_allclose(r[~support], 0.0, atol=EQ_ATOL, err_msg=name)

        R = np.where(support, r, 0.0)
        Fx = R[0::2] + f[0::2]
        Fy = R[1::2] + f[1::2]
        assert abs(Fx.sum()) <= EQ_ATOL, name
        assert abs(Fy.sum()) <= EQ_ATOL, name
        # Moment about the origin (B_0), counter-clockwise positive.
        assert abs(np.sum(x * Fy - y * Fx)) <= EQ_ATOL * L, name

    # The loads include P_end: under LC-full the reactions carry the whole W.
    R_y = sum(b.r_full[2 * k - 1] for k in b.support_nodes)
    assert R_y == pytest.approx(W_TOTAL, rel=RTOL)


# 2. Linearity ---------------------------------------------------------------

@types
@params
def test_linearity(truss_type, n):
    """Doubling w doubles all displacements, reactions and forces."""
    b1 = solved(truss_type, n, w=W_LOAD)
    b2 = solved(truss_type, n, w=2.0 * W_LOAD)

    assert_displacements_close(b2.a_full, 2.0 * b1.a_full)
    assert_displacements_close(b2.a_panels, 2.0 * b1.a_panels)
    assert_forces_close(b2.r_full, 2.0 * b1.r_full)
    assert_forces_close(b2.N_full, 2.0 * b1.N_full)
    assert_forces_close(b2.N_panels, 2.0 * b1.N_panels)
    assert_forces_close(b2.N_max, 2.0 * b1.N_max)
    assert_forces_close(b2.N_min, 2.0 * b1.N_min)


# 3. Symmetry ----------------------------------------------------------------

def mirror_map(b):
    """Map each element to its mirror image about x = L/2, found by geometry.

    The map is built from node coordinates only, independently of the
    model's element numbering. It fails if any element has no mirror image,
    or if a mirror image belongs to a different member group.
    """
    tol = 1e-9 * b.L

    def key(points):
        return tuple(sorted((round(px / tol), round(py / tol)) for px, py in points))

    index = {}
    for e in range(b.num_elements):
        index[key(zip(b.ex[e], b.ey[e]))] = e

    mapping = np.empty(b.num_elements, dtype=int)
    for e in range(b.num_elements):
        mirrored = key(zip(b.L - b.ex[e], b.ey[e]))
        assert mirrored in index, f"element {e + 1} has no mirror image"
        m = index[mirrored]
        assert b.member_groups[m] == b.member_groups[e]
        mapping[e] = m

    assert sorted(mapping) == list(range(b.num_elements)), "mirror map is not one-to-one"
    return mapping


@types
@params
def test_symmetry(truss_type, n):
    """Under LC-full, mirrored members carry equal forces. The envelope is
    symmetric too, because the set of panel patterns is symmetric."""
    b = solved(truss_type, n)
    mirror = mirror_map(b)

    assert_forces_close(b.N_full[mirror], b.N_full)
    assert_forces_close(b.N_max[mirror], b.N_max)
    assert_forces_close(b.N_min[mirror], b.N_min)

    # The two support reactions are equal.
    R_left = b.r_full[2 * b.support_nodes[0] - 1]
    R_right = b.r_full[2 * b.support_nodes[1] - 1]
    assert R_left == pytest.approx(R_right, rel=RTOL)


# 4. Determinacy -------------------------------------------------------------

def assert_same_forces(b, ref):
    assert_forces_close(b.N_full, ref.N_full)
    assert_forces_close(b.N_panels, ref.N_panels)
    assert_forces_close(b.N_max, ref.N_max)
    assert_forces_close(b.N_min, ref.N_min)


@types
@params
def test_determinacy_scale_E(truss_type, n):
    """E x 10: normal forces unchanged, displacements divided by 10."""
    ref = solved(truss_type, n)
    b = solved(truss_type, n, E=10.0 * E)
    assert_same_forces(b, ref)
    assert_displacements_close(b.a_full, ref.a_full / 10.0)
    assert_displacements_close(b.a_panels, ref.a_panels / 10.0)


@types
@params
def test_determinacy_scale_both_areas(truss_type, n):
    """A_c and A_w x 10 together: forces unchanged, displacements / 10."""
    ref = solved(truss_type, n)
    b = solved(truss_type, n, A_c=10.0 * A_C, A_w=10.0 * A_W)
    assert_same_forces(b, ref)
    assert_displacements_close(b.a_full, ref.a_full / 10.0)
    assert_displacements_close(b.a_panels, ref.a_panels / 10.0)


@types
@params
@pytest.mark.parametrize("which", ["A_c", "A_w"])
def test_determinacy_scale_one_area(truss_type, n, which):
    """Only A_c or only A_w x 10: normal forces unchanged, displacements change."""
    ref = solved(truss_type, n)
    if which == "A_c":
        b = solved(truss_type, n, A_c=10.0 * A_C)
    else:
        b = solved(truss_type, n, A_w=10.0 * A_W)
    assert_same_forces(b, ref)
    # Guard against a model that ignores the class areas: the stiffness, and
    # hence the midspan deflection, must change.
    assert abs(b.u_midspan) < abs(ref.u_midspan) * (1.0 - 1e-6)


# 5. Superposition -----------------------------------------------------------

@types
@params
def test_superposition(truss_type, n):
    """The sum of LC-0 ... LC-(n-1) equals LC-full, and LC-full lies within
    the envelope."""
    b = solved(truss_type, n)

    np.testing.assert_allclose(b.f_panels.sum(axis=0), b.f_full[:, 0], rtol=RTOL, atol=EQ_ATOL)
    assert_displacements_close(b.a_panels.sum(axis=0), b.a_full)
    assert_forces_close(b.r_panels.sum(axis=0), b.r_full)
    assert_forces_close(b.N_panels.sum(axis=0), b.N_full)

    # LC-full is one of the 2^n panel patterns, so it lies in the envelope.
    assert np.all(b.N_full <= b.N_max + FORCE_ATOL)
    assert np.all(b.N_full >= b.N_min - FORCE_ATOL)
    assert np.all(b.N_max >= 0.0)
    assert np.all(b.N_min <= 0.0)

    # Spec 8.6: if all single-panel forces of a member have the same sign,
    # the envelope equals the LC-full force.
    N_i = np.where(np.abs(b.N_panels) < b.N_tol, 0.0, b.N_panels)
    all_tension = np.all(N_i >= 0.0, axis=0)
    all_compression = np.all(N_i <= 0.0, axis=0)
    assert_forces_close(b.N_max[all_tension], b.N_full[all_tension])
    assert_forces_close(b.N_min[all_compression], b.N_full[all_compression])
