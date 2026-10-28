# -*- coding: utf-8 -*-
"""
Tests for the engineer-owned core (frame_model.py, sections.py).

Run with ``pytest`` from this directory.

Three kinds of evidence:
  1. Analytical benchmarks (verification.py) - does it compute the right
     numbers for cases where we know the answer?
  2. Physical properties - equilibrium, symmetry, superposition - that
     must hold for ANY frame, including ones without a known solution.
  3. Guards against specific failure modes: units, local/global loads,
     and the beam2s evaluation-point issue.
"""

import numpy as np
import pytest
import calfem.core as cfc

from frame_model import FrameModel, PlaneFrame, beam2_section_forces
from sections import SECTIONS, STEEL_DENSITY, GRAVITY
from verification import BENCHMARKS, run_benchmarks

FRAMES = [
    dict(),
    dict(base="pinned"),
    dict(n_bays=1, n_storeys=1),
    dict(n_bays=4, n_storeys=6, bay_width=5.0, storey_height=3.2),
    dict(n_bays=3, n_storeys=2, wind_load=0.0, self_weight=False),
]


# ----------------------------------------------------------------------
# 1. Analytical benchmarks
# ----------------------------------------------------------------------

@pytest.mark.parametrize("row", run_benchmarks(), ids=lambda r: f"{r['case']}: {r['quantity']}")
def test_benchmark(row):
    assert row["passed"], (
        f"expected {row['expected']:.6g}, computed {row['computed']:.6g}, "
        f"rel. error {row['rel_error']:.2e}")


def test_all_benchmarks_produce_results():
    assert len(run_benchmarks()) >= len(BENCHMARKS)


# ----------------------------------------------------------------------
# 2. Physical properties
# ----------------------------------------------------------------------

@pytest.mark.parametrize("params", FRAMES)
def test_global_equilibrium(params):
    res = PlaneFrame(**params).solve()
    for component, err in res.equilibrium_error().items():
        assert err < 1e-10, f"{component} out of balance: {err:.2e}"


def test_symmetric_gravity_gives_no_sway():
    frame = PlaneFrame(n_bays=2, n_storeys=3, wind_load=0.0)
    frame.solve()
    assert frame.summary()["top_sway"] < 1e-12
    # Mirror symmetry: ux antisymmetric, uy symmetric about the centre line
    for level in range(frame.n_storeys + 1):
        for col in range(frame.n_bays + 1):
            u = frame.results.node_displacement(frame.node(col, level))
            m = frame.results.node_displacement(frame.node(frame.n_bays - col, level))
            assert u[0] == pytest.approx(-m[0], abs=1e-12)
            assert u[1] == pytest.approx(m[1], abs=1e-12)
    left = frame.results.reactions[frame.node(0, 0)]
    right = frame.results.reactions[frame.node(frame.n_bays, 0)]
    assert left[1] == pytest.approx(right[1], rel=1e-10)
    assert left[2] == pytest.approx(-right[2], rel=1e-10)


def test_superposition():
    common = dict(n_bays=3, n_storeys=4, self_weight=False)
    both = PlaneFrame(**common).solve()
    gravity = PlaneFrame(**common, wind_load=0.0).solve()
    wind = PlaneFrame(**common, floor_load=0.0, roof_load=0.0).solve()
    np.testing.assert_allclose(both.a, gravity.a + wind.a, atol=1e-14)


def test_pinned_bases_have_no_moment_and_sway_more():
    fixed = PlaneFrame(base="fixed")
    pinned = PlaneFrame(base="pinned")
    fixed.solve()
    pinned.solve()
    for node, (_, _, mz) in pinned.results.reactions.items():
        assert abs(mz) < 1e-6
    assert pinned.summary()["top_sway"] > fixed.summary()["top_sway"]


def test_self_weight_reaction_equals_steel_weight():
    frame = PlaneFrame(floor_load=0.0, roof_load=0.0, wind_load=0.0, self_weight=True)
    res = frame.solve()
    total_ry = sum(r[1] for r in res.reactions.values())
    assert total_ry == pytest.approx(frame.steel_mass() * GRAVITY, rel=1e-12)


def test_stiffer_columns_reduce_drift():
    weak = PlaneFrame(column_section="HEA 200")
    strong = PlaneFrame(column_section="HEB 300")
    weak.solve()
    strong.solve()
    assert strong.summary()["max_drift"] < weak.summary()["max_drift"]


# ----------------------------------------------------------------------
# 3. Failure-mode guards
# ----------------------------------------------------------------------

def test_section_units():
    ipe300 = SECTIONS["IPE 300"]
    assert ipe300.A == pytest.approx(53.8e-4)
    assert ipe300.I == pytest.approx(8356e-8)
    assert ipe300.W == pytest.approx(557e-6)
    # IPE 300 weighs about 42.2 kg/m
    assert ipe300.mass_per_m == pytest.approx(42.2, rel=0.01)


def test_global_load_on_column_is_axial():
    """A vertical line load on a vertical column must not bend it."""
    model = FrameModel()
    a = model.add_node(0.0, 0.0)
    b = model.add_node(0.0, 3.0)
    model.add_member(a, b, "HEA 200")
    model.add_support(a)
    model.add_line_load(0, qy=-STEEL_DENSITY * GRAVITY * SECTIONS["HEA 200"].A)
    res = model.solve()
    assert np.max(np.abs(res.members[0].M)) < 1e-9
    assert abs(res.node_displacement(b)[0]) < 1e-15


@pytest.mark.parametrize("ex, ey, eq", [
    ([0.0, 6.0], [0.0, 0.0], [0.0, -20e3]),
    ([6.0, 0.0], [0.0, 0.0], [0.0, -20e3]),
    ([0.0, 3.0], [0.0, 4.0], [1e3, -5e3]),
])
def test_section_forces_match_calfem_beam2s(ex, ey, eq):
    """Our evaluation routine reproduces CALFEM beam2s where it works."""
    ex, ey = np.array(ex), np.array(ey)
    ep = [210e9, 50e-4, 8000e-8]
    ed = np.array([1e-3, -2e-3, 1e-4, -3e-4, 5e-4, -2e-4])
    nep = 11
    es_ref, edi_ref, eci_ref = cfc.beam2s(ex, ey, ep, ed, eq, nep=nep)
    es, edi, s = beam2_section_forces(ex, ey, ep, ed, eq, nep)
    np.testing.assert_allclose(s, eci_ref[:, 0], atol=1e-12)
    np.testing.assert_allclose(es, es_ref, rtol=1e-10, atol=1e-6)
    np.testing.assert_allclose(edi, edi_ref, rtol=1e-10, atol=1e-15)


def test_evaluation_points_for_awkward_length():
    """A 3.6 m column with 21 points broke beam2s; our routine must not."""
    frame = PlaneFrame(storey_height=3.6, n_points=21)
    res = frame.solve()
    for m in res.members:
        assert len(m.s) == 21
        assert m.s[-1] == pytest.approx(m.length)


# ----------------------------------------------------------------------
# Input validation
# ----------------------------------------------------------------------

@pytest.mark.parametrize("params", [
    dict(n_bays=0),
    dict(n_storeys=0),
    dict(bay_width=-1.0),
    dict(base="clamped"),
    dict(column_section="IPE 999"),
    dict(steel_grade="S960"),
])
def test_invalid_input_raises(params):
    with pytest.raises(ValueError):
        PlaneFrame(**params)


def test_unsupported_model_raises():
    model = FrameModel()
    a = model.add_node(0.0, 0.0)
    b = model.add_node(6.0, 0.0)
    model.add_member(a, b, "IPE 300")
    with pytest.raises(ValueError):
        model.solve()


def test_section_table_is_plausible():
    """
    Data check that catches unit mistakes the benchmarks cannot see:
    for a doubly symmetric section I/W = h/2, so 2 I / W must be a
    realistic profile depth, and A must give a realistic mass per metre.
    """
    for name, sec in SECTIONS.items():
        depth = 2 * sec.I / sec.W
        assert 0.1 < depth < 1.0, f"{name}: depth {depth:.3f} m"
        nominal = int(name.split()[1]) / 1000
        assert depth == pytest.approx(nominal, rel=0.15), name
        assert 10 < sec.mass_per_m < 200, name
