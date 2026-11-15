"""Tests for design_checks.py against hand-derived values (spec section 7).

Reference design: Pratt, L = 20 m, h = 3 m, n = 4, q = 4 kN/m^2, b = 2.5 m,
so w = 5 kN/m, P = 25 kN and P_end = 12.5 kN. The reaction from the
interior loads is R = 37.5 kN, the panel length is 5 m and the diagonal
length is sqrt(34) m.
Chords (top chord, bottom chord, end posts): SHS 100x5, A = 18.73 cm^2,
I = 279.4 cm^4. Web (verticals, diagonals): SHS 80x4, A = 11.99 cm^2,
I = 114.5 cm^4. Section values are from spec table 4.1. E = 210 GPa,
f_y = 355 MPa, rho = 7850 kg/m^3.

All expected values are exact formulas from the hand derivation. None of
them is taken from the model.
"""

import math
from types import SimpleNamespace

import pytest

import design_checks as dc

REL = 1e-9

L, H, N = 20.0, 3.0, 4
E = 210e9
FY = 355e6
RHO = 7850.0
D = math.sqrt(34.0)             # diagonal and end post length [m]

A_C, I_C = 18.73e-4, 279.4e-8   # SHS 100x5
A_W, I_W = 11.99e-4, 114.5e-8   # SHS 80x4

# Hand-derived member forces under LC-full [N] (step 6 scaled by 2.5).
N_TOP = -250e3 / 3.0                    # -M(L/2)/h = -250 kNm / 3 m
N_END_POST = -37.5e3 * D / 3.0          # -R * d / h

# Pratt diagonal T1-B2 under single-panel loads. Each loaded panel puts
# 12.5 kN on both its end nodes. A unit load at B_1 gives a panel-1 shear of
# -1/4, at B_2 +1/2, at B_3 +1/4, and at B_0 or B_4 zero. Panel shears:
# LC-0 = -3.125 kN, LC-1 = +3.125 kN, LC-2 = +9.375 kN, LC-3 = +3.125 kN.
# The diagonal force is V * d / h.
N_DIAG_MIN = -3.125e3 * D / 3.0
N_DIAG_MAX = (3.125e3 + 9.375e3 + 3.125e3) * D / 3.0


def euler(I, ell):
    return math.pi ** 2 * E * I / ell ** 2


@pytest.fixture(scope="module")
def design():
    S = dc.SECTIONS_BY_NAME
    return dc.check_design("pratt", H, N, S["SHS 100x5"], S["SHS 80x4"])


def members(design, group):
    return [e for e, g in enumerate(design.member_groups) if g == group]


# Loads (spec D5, D7) --------------------------------------------------------

def test_line_load():
    assert dc.line_load() == pytest.approx(4e3 * 2.5 / 2.0, rel=REL)


def test_nodal_loads(design):
    assert design.w == pytest.approx(5e3, rel=REL)
    assert design.P == pytest.approx(5e3 * L / N, rel=REL)
    assert design.P_end == pytest.approx(5e3 * L / (2 * N), rel=REL)


# C1 yield and C2 buckling: top chord ----------------------------------------

def test_top_chord_envelope_equals_lc_full(design):
    for e in members(design, "top chord"):
        assert design.N_min[e] == pytest.approx(N_TOP, rel=REL)
        assert design.N_max[e] == 0.0


def test_top_chord_yield(design):
    for e in members(design, "top chord"):
        assert design.U_yield[e] == pytest.approx(-N_TOP / (A_C * FY), rel=REL)


def test_top_chord_buckling(design):
    for e in members(design, "top chord"):
        assert design.compression[e]
        assert design.U_buckling[e] == pytest.approx(-N_TOP / euler(I_C, 5.0), rel=REL)


# C2 buckling: end post (governing member) -----------------------------------

def test_end_post_buckling_governs(design):
    U_end = -N_END_POST / euler(I_C, D)
    for e in members(design, "end post"):
        assert design.U_buckling[e] == pytest.approx(U_end, rel=REL)
    assert design.governing_check == dc.CHECK_BUCKLING
    assert design.governing_member - 1 in members(design, "end post")
    assert design.U_max == pytest.approx(U_end, rel=REL)


# C1 and C2 from the envelope: Pratt diagonal --------------------------------

def test_pratt_diagonal_envelope(design):
    """The diagonal is in tension under LC-full but in compression under
    LC-0, so C2 must apply to it with N_min from the envelope."""
    for e in members(design, "diagonal"):
        assert design.N_min[e] == pytest.approx(N_DIAG_MIN, rel=REL)
        assert design.N_max[e] == pytest.approx(N_DIAG_MAX, rel=REL)
        assert design.compression[e]
        assert design.U_yield[e] == pytest.approx(N_DIAG_MAX / (A_W * FY), rel=REL)
        assert design.U_buckling[e] == pytest.approx(-N_DIAG_MIN / euler(I_W, D), rel=REL)


def test_tension_only_members_have_no_buckling(design):
    for group in ("bottom chord", "vertical"):
        for e in members(design, group):
            assert not design.compression[e]
            assert design.U_buckling[e] == 0.0


# C3 deflection --------------------------------------------------------------

def test_midspan_deflection(design):
    """Unit-load method: delta = sum N * n * ell / (E * A) under LC-full,
    with n the member forces from a unit load at B_2."""
    chords = (
        4 * 62.5e3 * (5.0 / 6.0) * 5.0                      # bottom chord: N = R*5/h, n = 5/6
        + 2 * (250e3 / 3.0) * (5.0 / 3.0) * 5.0             # top chord: N = -250/3 kN, n = -5/3
        + 2 * (37.5e3 * D / 3.0) * (0.5 * D / 3.0) * D      # end posts
    ) / (E * A_C)
    web = (
        2 * (12.5e3 * D / 3.0) * (0.5 * D / 3.0) * D        # diagonals; verticals have n = 0
    ) / (E * A_W)
    delta = chords + web

    assert design.u_midspan == pytest.approx(-delta, rel=REL)
    assert design.U_deflection == pytest.approx(delta / (L / 400.0), rel=REL)


# Mass -----------------------------------------------------------------------

def test_mass(design):
    chord_length = 4 * 5.0 + 2 * 5.0 + 2 * D      # bottom chord, top chord, end posts
    web_length = 3 * 3.0 + 2 * D                   # verticals, diagonals
    expected = RHO * (A_C * chord_length + A_W * web_length)
    assert design.mass == pytest.approx(expected, rel=REL)


def test_passes(design):
    assert design.passes_yield and design.passes_buckling and design.passes_deflection
    assert design.passes


# Ranking (spec 6.4, R7) -----------------------------------------------------

def fake(mass, U_max, truss_type):
    return SimpleNamespace(mass=mass, U_max=U_max, truss_type=truss_type)


def test_ranking_by_mass():
    a, b = fake(100.0, 0.9, "warren"), fake(101.0, 0.1, "pratt")
    assert dc.rank_designs([b, a]) == [a, b]


def test_ranking_equal_mass_lower_utilisation_first():
    a, b = fake(100.0, 0.5, "howe"), fake(100.0 * (1 + 0.5e-9), 0.8, "pratt")
    assert dc.rank_designs([b, a]) == [a, b]


def test_ranking_equal_mass_and_utilisation_by_type():
    p, h, w = fake(100.0, 0.5, "pratt"), fake(100.0, 0.5, "howe"), fake(100.0, 0.5, "warren")
    assert dc.rank_designs([w, h, p]) == [p, h, w]


def test_ranking_mass_difference_above_tolerance_is_not_a_tie():
    a, b = fake(100.0, 0.9, "warren"), fake(100.0 * (1 + 2e-9), 0.1, "pratt")
    assert dc.rank_designs([b, a]) == [a, b]


def test_pratt_and_howe_with_equal_mass_ranked_by_utilisation():
    """Pratt and Howe with the same n, h and sections have identical member
    lengths, and so equal mass. The ranking must then use U_max."""
    S = dc.SECTIONS_BY_NAME
    p = dc.check_design("pratt", H, N, S["SHS 100x5"], S["SHS 80x4"])
    h = dc.check_design("howe", H, N, S["SHS 100x5"], S["SHS 80x4"])
    assert p.mass == pytest.approx(h.mass, rel=1e-12)
    expected = [p, h] if p.U_max <= h.U_max else [h, p]
    assert dc.rank_designs([h, p]) == expected


# Search result when no design passes (spec 6.4, R9) -------------------------

def test_search_no_design_passes():
    """Pratt, n = 4, h = 3 m with SHS 60x4 everywhere: the end post buckles.
    U = R * d / h / (pi^2 E I / d^2), with I = 45.39 cm^4."""
    result = dc.design_search(truss_types=("pratt",), n_values=(4,), h_values=(3.0,),
                              sections=(dc.SECTIONS_BY_NAME["SHS 60x4"],))
    assert result.num_designs == 1
    assert result.passing == []
    assert result.lightest is None
    c = result.closest
    assert c is not None
    assert c.governing_check == dc.CHECK_BUCKLING
    assert c.governing_member - 1 in members(c, "end post")
    assert c.U_max == pytest.approx(-N_END_POST / euler(45.39e-8, D), rel=REL)


def test_search_ranks_passing_designs():
    result = dc.design_search(truss_types=("pratt", "howe"), n_values=(4,), h_values=(3.0,),
                              sections=dc.SECTIONS[3:6])
    assert result.num_designs == 2 * 3 * 3
    assert result.closest is None
    assert all(d.passes for d in result.passing)
    assert result.passing == dc.rank_designs(result.passing)
    masses = [d.mass for d in result.passing]
    assert masses == sorted(masses) or all(
        m2 >= m1 * (1 - 1e-9) for m1, m2 in zip(masses, masses[1:]))
