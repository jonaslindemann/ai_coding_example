import numpy as np
import pytest

from debug_temperature import (
    solve_temperature, WIDTH, HEIGHT, TEMPERATURE_LEFT, TEMPERATURE_RIGHT,
)

TOL = 1e-8
GEOM_TOL = 1e-6   # gmsh places edge nodes to ~1e-9, not exactly


@pytest.fixture(scope="module")
def solution():
    coords, temperature, reaction = solve_temperature()
    return coords, temperature[:, 0], reaction[:, 0]


def _on(coords, *, x=None, y=None):
    mask = np.ones(len(coords), dtype=bool)
    if x is not None:
        mask &= np.isclose(coords[:, 0], x, atol=GEOM_TOL)
    if y is not None:
        mask &= np.isclose(coords[:, 1], y, atol=GEOM_TOL)
    assert mask.any()
    return mask


def _exact(x):
    return TEMPERATURE_LEFT + (TEMPERATURE_RIGHT - TEMPERATURE_LEFT) * x / WIDTH


# --- Dirichlet boundaries -------------------------------------------------

def test_left_edge_has_prescribed_temperature(solution):
    coords, T, _ = solution
    assert np.allclose(T[_on(coords, x=0.0)], TEMPERATURE_LEFT, atol=TOL)


def test_right_edge_has_prescribed_temperature(solution):
    coords, T, _ = solution
    assert np.allclose(T[_on(coords, x=WIDTH)], TEMPERATURE_RIGHT, atol=TOL)


# --- Insulated boundaries / 1-D behaviour --------------------------------

@pytest.mark.parametrize("edge_y", [0.0, HEIGHT])
def test_insulated_edges_follow_linear_profile(edge_y, solution):
    # With q_y = 0 on top/bottom, the edge temperatures are not fixed but
    # must vary linearly from left to right like the rest of the plate.
    coords, T, _ = solution
    m = _on(coords, y=edge_y)
    assert np.allclose(T[m], _exact(coords[m, 0]), atol=1e-6)


def test_field_is_independent_of_y(solution):
    coords, T, _ = solution
    top, bottom = _on(coords, y=HEIGHT), _on(coords, y=0.0)
    xs = coords[bottom, 0]
    T_top_at_xs = np.interp(xs, *zip(*sorted(zip(coords[top, 0], T[top]))))
    assert np.allclose(T[bottom], T_top_at_xs, atol=1e-6)


# --- Whole-field properties ----------------------------------------------

def test_matches_analytical_linear_solution(solution):
    # Bilinear quads reproduce a linear field exactly (patch test).
    coords, T, _ = solution
    assert np.max(np.abs(T - _exact(coords[:, 0]))) < 1e-6


def test_maximum_principle(solution):
    _, T, _ = solution
    assert T.min() >= TEMPERATURE_LEFT - TOL
    assert T.max() <= TEMPERATURE_RIGHT + TOL


def test_temperature_increases_monotonically_in_x(solution):
    coords, T, _ = solution
    order = np.argsort(coords[:, 0])
    assert np.all(np.diff(T[order]) >= -1e-6)


def test_antisymmetry_about_midline(solution):
    # T(x) + T(W - x) = T_left + T_right; the mean equals the mid-value.
    coords, T, _ = solution
    mid = 0.5 * (TEMPERATURE_LEFT + TEMPERATURE_RIGHT)
    centre = np.isclose(coords[:, 0], 0.5 * WIDTH, atol=GEOM_TOL)
    if centre.any():
        assert np.allclose(T[centre], mid, atol=1e-6)


# --- Conservation (reaction = boundary heat flow) -------------------------

def test_no_heat_source_at_free_nodes(solution):
    coords, _, r = solution
    free = ~(_on(coords, x=0.0) | _on(coords, x=WIDTH))
    assert np.allclose(r[free], 0.0, atol=1e-8)


def test_heat_in_equals_heat_out(solution):
    coords, _, r = solution
    q_left = r[_on(coords, x=0.0)].sum()
    q_right = r[_on(coords, x=WIDTH)].sum()
    assert q_left + q_right == pytest.approx(0.0, abs=1e-8)


def test_total_heat_flow_matches_fourier_law(solution):
    # Q = k * t * H * dT / W with k = 1, t = 1.
    coords, _, r = solution
    expected = (TEMPERATURE_RIGHT - TEMPERATURE_LEFT) * HEIGHT / WIDTH
    assert r[_on(coords, x=WIDTH)].sum() == pytest.approx(expected, rel=1e-8)
