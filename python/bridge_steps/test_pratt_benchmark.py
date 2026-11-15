"""Benchmark: Pratt truss, L = 20 m, h = 3 m, n = 4, P = 10 kN, E = 210 GPa, A = 0.01 m².

Expected values are hand calculations (method of sections, unit-load method).
They were corrected from the original benchmark with the problem owner's approval:
  * the central bottom chord carries M(L/2 - L/n)/h, not M(L/2)/h; M(L/2)/h is
    carried (in compression) by the top chord next to midspan,
  * the diagonal force is the exact V*d/h instead of the rounded 9.718 kN,
  * the midspan deflection is 0.6728 mm (unit-load method), not 9.74 mm.
Tolerances: forces rel = 1e-9; deflection abs = 1e-6 m.
"""

import numpy as np
import pytest

from truss_model import TrussBridge

# Benchmark input (SI units)
L = 20.0        # m
h = 3.0         # m
n = 4
P = 10e3        # N
E = 210e9       # Pa
A = 0.01        # m^2

# Expected values (hand calculations)
dx = L / n                              # panel width [m]
d = np.hypot(dx, h)                     # diagonal length [m]
R_EXPECTED = P * (n - 1) / 2            # support reaction [N]
M_EXPECTED = P * n * L / 8              # midspan moment [N·m]

# Method of sections through the panel left of midspan (x = 5..10 m). The top
# chord and the diagonal meet at the top node at x = L/2 - dx, so the bottom
# chord carries M there / h. The diagonal and the bottom chord meet at the
# midspan bottom node, so the top chord carries -M(L/2)/h.
M_AT_TOP_NODE = R_EXPECTED * (L / 2 - dx) - P * (L / 2 - 2 * dx)  # = 75 kN·m
N_BOTTOM_CENTRAL_EXPECTED = M_AT_TOP_NODE / h       # 25 kN, tension
N_TOP_CENTRAL_EXPECTED = -M_EXPECTED / h            # -33.33 kN, compression

# Diagonal: its vertical component carries the panel shear V = R - P
V_PANEL = R_EXPECTED - P                            # 5 kN
N_DIAG_LEFT_OF_MID_EXPECTED = V_PANEL * d / h       # 5*sqrt(34)/3 kN ≈ 9.718 kN

# Unit-load method, delta = sum(N * n_unit * l) / (E A), unit load at midspan.
# Member forces N (load P) and n_unit (unit load), n = 4:
#   bottom chord (4):  25 kN,              5/6,           l = dx
#   top chord    (2): -M/h,               -(L/2)/(2h),    l = dx
#   end posts    (2): -R d/h,             -0.5 d/h,       l = d
#   diagonals    (2):  V d/h,              0.5 d/h,       l = d
#   verticals:         n_unit = 0, no contribution
_sum = (
    4 * N_BOTTOM_CENTRAL_EXPECTED * (0.5 * (L / 2 - dx) / h) * dx
    + 2 * N_TOP_CENTRAL_EXPECTED * (-(0.5 * L / 2) / h) * dx
    + 2 * (-R_EXPECTED * d / h) * (-0.5 * d / h) * d
    + 2 * (V_PANEL * d / h) * (0.5 * d / h) * d
)
DEFLECTION_MID_EXPECTED = _sum / (E * A)            # ≈ 0.6728 mm, downward

REL_FORCE = 1e-9
ABS_DEFLECTION = 1e-6  # m


@pytest.fixture(scope="module")
def truss():
    t = TrussBridge("pratt", L, h, n)
    t.solve(E, A, P)
    return t


def _member(t, n1, n2):
    """0-based index of the member connecting 1-based nodes n1 and n2."""
    for e, (a, b) in enumerate(t.elements):
        if {a, b} == {n1, n2}:
            return e
    raise KeyError((n1, n2))


def test_support_reactions(truss):
    pin, roller = truss.support_nodes
    ry_pin = truss.r[2 * pin - 1, 0]
    ry_roller = truss.r[2 * roller - 1, 0]
    assert ry_pin == pytest.approx(R_EXPECTED, rel=REL_FORCE)
    assert ry_roller == pytest.approx(R_EXPECTED, rel=REL_FORCE)


def test_midspan_moment(truss):
    """Moment at x = L/2 from the computed left reaction and the loads left of midspan."""
    pin = truss.support_nodes[0]
    ry_pin = truss.r[2 * pin - 1, 0]
    x_mid = L / 2
    M = ry_pin * x_mid
    for node in truss.loaded_nodes:
        x = truss.coords[node - 1, 0]
        if x < x_mid:
            M -= P * (x_mid - x)
    assert M == pytest.approx(M_EXPECTED, rel=REL_FORCE)


def test_central_bottom_chord_force(truss):
    """Both bottom-chord members adjacent to midspan (n even: no single central member)."""
    k = n // 2  # midspan bottom node index
    for i in (k - 1, k):
        e = _member(truss, truss._bottom(i), truss._bottom(i + 1))
        assert truss.member_groups[e] == "bottom"
        assert truss.N[e] == pytest.approx(N_BOTTOM_CENTRAL_EXPECTED, rel=REL_FORCE)


def test_central_top_chord_force(truss):
    """The top chord next to midspan carries -M(L/2)/h (compression)."""
    k = n // 2
    for i in (k - 1, k):
        e = _member(truss, truss._top(i), truss._top(i + 1))
        assert truss.member_groups[e] == "top"
        assert truss.N[e] == pytest.approx(N_TOP_CENTRAL_EXPECTED, rel=REL_FORCE)


def test_diagonal_left_of_midspan(truss):
    """Pratt left half: the diagonal in panel n/2-1 runs from top node n/2-1 down to midspan."""
    k = n // 2
    e = _member(truss, truss._top(k - 1), truss._bottom(k))
    assert truss.member_groups[e] == "diagonal"
    assert truss.N[e] == pytest.approx(N_DIAG_LEFT_OF_MID_EXPECTED, rel=REL_FORCE)


def test_midspan_deflection(truss):
    """Downward deflection magnitude of the midspan bottom node."""
    mid = truss._bottom(n // 2)
    uy = truss.a[2 * mid - 1, 0]
    assert -uy == pytest.approx(DEFLECTION_MID_EXPECTED, abs=ABS_DEFLECTION)
