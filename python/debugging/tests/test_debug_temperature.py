import numpy as np

from debug_temperature import solve_temperature, WIDTH, TEMPERATURE_LEFT, TEMPERATURE_RIGHT


def _edge_values(coords, temperature, *, x=None, y=None):
    mask = np.ones(len(coords), dtype=bool)
    if x is not None:
        mask &= np.isclose(coords[:, 0], x, atol=1e-10)
    if y is not None:
        mask &= np.isclose(coords[:, 1], y, atol=1e-10)
    return temperature[mask, 0]


def test_left_boundary_is_zero_degrees():
    coords, temperature, _ = solve_temperature()
    values = _edge_values(coords, temperature, x=0.0)
    assert len(values) > 0
    assert np.allclose(values, TEMPERATURE_LEFT, atol=1e-8)


def test_right_boundary_is_100_degrees():
    coords, temperature, _ = solve_temperature()
    values = _edge_values(coords, temperature, x=WIDTH)
    assert len(values) > 0
    assert np.allclose(values, TEMPERATURE_RIGHT, atol=1e-8)


def test_temperature_is_between_boundary_values():
    coords, temperature, _ = solve_temperature()
    values = temperature[:, 0]
    assert values.min() >= TEMPERATURE_LEFT - 1e-8
    assert values.max() <= TEMPERATURE_RIGHT + 1e-8
