"""Benchmark: Pratt truss under LC-full against the engineer's hand values.

L = 20 m, h = 3 m, n = 4, w = 2 kN/m, E = 210 GPa, A_c = A_w = 0.01 m^2.
The expected values were given by the engineer and must not be changed.
Members are located by geometry (group and an end node at midspan), not by
element index.
"""

import math

import numpy as np
import pytest

from truss_model import TrussBridge

L = 20.0
H = 3.0
N_PANELS = 4
W = 2.0e3        # N/m
E = 210.0e9      # Pa
A = 0.01         # m^2

REL_FORCE = 1e-9
REL_DEFLECTION = 1e-3

EXPECTED_REACTION = 20.0e3                        # N, each support
EXPECTED_TOP_CHORD = -100.0e3 / 3.0              # N, -M(L/2)/h = -100 kNm / 3 m
EXPECTED_BOTTOM_CHORD = 25000.0                   # N
EXPECTED_DIAGONAL = 5.0 * math.sqrt(34.0) / 3.0 * 1.0e3   # N
EXPECTED_MIDSPAN_DEFLECTION = -0.6728e-3          # m, downward


@pytest.fixture(scope="module")
def bridge():
    b = TrussBridge("pratt", L, H, N_PANELS)
    b.solve(E, A, A, W)
    return b


def members_at_midspan(bridge, group):
    """Return the indices of members in a group with one end at x = L/2."""
    x_mid = bridge.L / 2.0
    at_mid = np.isclose(bridge.ex, x_mid, rtol=0.0, atol=1e-12 * bridge.L).any(axis=1)
    found = [e for e in range(bridge.num_elements)
             if bridge.member_groups[e] == group and at_mid[e]]
    assert len(found) == 2, f"expected two {group} members next to midspan, found {found}"
    return found


def test_support_reactions(bridge):
    for node in bridge.support_nodes:
        r_y = bridge.r_full[2 * node - 1]
        assert r_y == pytest.approx(EXPECTED_REACTION, rel=REL_FORCE)


def test_top_chord_next_to_midspan(bridge):
    for e in members_at_midspan(bridge, "top chord"):
        assert bridge.N_full[e] == pytest.approx(EXPECTED_TOP_CHORD, rel=REL_FORCE)


def test_bottom_chord_next_to_midspan(bridge):
    for e in members_at_midspan(bridge, "bottom chord"):
        assert bridge.N_full[e] == pytest.approx(EXPECTED_BOTTOM_CHORD, rel=REL_FORCE)


def test_diagonal_next_to_midspan(bridge):
    for e in members_at_midspan(bridge, "diagonal"):
        assert bridge.N_full[e] == pytest.approx(EXPECTED_DIAGONAL, rel=REL_FORCE)


def test_midspan_deflection(bridge):
    u_y = bridge.u_midspan
    assert u_y < 0.0, "midspan deflection must be downward"
    assert u_y == pytest.approx(EXPECTED_MIDSPAN_DEFLECTION, rel=REL_DEFLECTION)
