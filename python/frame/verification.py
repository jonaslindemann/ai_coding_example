# -*- coding: utf-8 -*-
"""
Verification benchmarks for frame_model.py.

ENGINEER-OWNED. Each benchmark builds a small FrameModel for which a
closed-form solution exists and compares a computed quantity with the
textbook value. The same cases are run by pytest (test_frame_model.py),
shown in the web application and printed in the report, so the evidence
that the core is correct travels with every result.

Run ``python verification.py`` for a table of all benchmarks.
"""

import numpy as np

from frame_model import FrameModel
from sections import Section, E_STEEL

E = E_STEEL
L = 6.0
H = 4.0
P = 10e3       # point load (N)
Q = 20e3       # line load (N/m)
SEC = Section("test", A=50e-4, I=8000e-8, W=500e-6)
# Practically rigid in bending and axially, used for "rigid beam" cases
RIGID = Section("rigid", A=1.0, I=1e3, W=1.0)
# Axially rigid column, so sway is governed by bending only
COLUMN = Section("column", A=1.0, I=SEC.I, W=SEC.W)


def _mid(model):
    return model.n_points // 2


def _beam(cls, x0, x1, sections=SEC, y0=0.0, y1=0.0):
    model = cls(E=E)
    a = model.add_node(x0, y0)
    b = model.add_node(x1, y1)
    model.add_member(a, b, sections)
    return model, a, b


def cantilever_point_load(cls):
    model, a, b = _beam(cls, 0.0, L)
    model.add_support(a)
    model.add_point_load(b, fy=-P)
    res = model.solve()
    return [
        ("tip deflection", P * L**3 / (3 * E * SEC.I), -res.node_displacement(b)[1], "m"),
        ("support moment", P * L, abs(res.reactions[a][2]), "N m"),
    ]


def cantilever_udl(cls):
    model, a, b = _beam(cls, 0.0, L)
    model.add_support(a)
    model.add_line_load(0, qy=-Q)
    res = model.solve()
    return [
        ("tip deflection", Q * L**4 / (8 * E * SEC.I), -res.node_displacement(b)[1], "m"),
        ("support moment", Q * L**2 / 2, abs(res.reactions[a][2]), "N m"),
    ]


def simply_supported_udl(cls, reverse=False):
    x0, x1 = (L, 0.0) if reverse else (0.0, L)
    model, a, b = _beam(cls, x0, x1)
    model.add_support(a, x=True, y=True, rotation=False)
    model.add_support(b, x=False, y=True, rotation=False)
    model.add_line_load(0, qy=-Q)
    res = model.solve()
    m = res.members[0]
    k = _mid(model)
    return [
        ("midspan deflection", 5 * Q * L**4 / (384 * E * SEC.I), -m.uy[k], "m"),
        ("midspan moment", Q * L**2 / 8, abs(m.M[k]), "N m"),
        ("support reaction", Q * L / 2, res.reactions[a][1], "N"),
    ]


def fixed_fixed_udl(cls):
    model, a, b = _beam(cls, 0.0, L)
    model.add_support(a)
    model.add_support(b)
    model.add_line_load(0, qy=-Q)
    res = model.solve()
    m = res.members[0]
    k = _mid(model)
    return [
        ("midspan deflection", Q * L**4 / (384 * E * SEC.I), -m.uy[k], "m"),
        ("end moment", Q * L**2 / 12, abs(m.M[0]), "N m"),
        ("midspan moment", Q * L**2 / 24, abs(m.M[k]), "N m"),
    ]


def inclined_cantilever(cls, angle_deg=30.0):
    alpha = np.radians(angle_deg)
    model, a, b = _beam(cls, 0.0, L * np.cos(alpha), SEC, 0.0, L * np.sin(alpha))
    model.add_support(a)
    model.add_point_load(b, fy=-P)
    res = model.solve()
    # Bending from the transverse component plus axial shortening from
    # the axial component of P
    bending = P * L**3 * np.cos(alpha)**2 / (3 * E * SEC.I)
    axial = P * L * np.sin(alpha)**2 / (E * SEC.A)
    return [
        ("vertical tip deflection", bending + axial,
         -res.node_displacement(b)[1], "m"),
    ]


def column_axial_line_load(cls):
    """Vertical column under its own weight: tests global->local loads."""
    model, a, b = _beam(cls, 0.0, 0.0, SEC, 0.0, H)
    model.add_support(a)
    model.add_line_load(0, qy=-Q)
    res = model.solve()
    return [
        ("top shortening", Q * H**2 / (2 * E * SEC.A), -res.node_displacement(b)[1], "m"),
        ("base reaction", Q * H, res.reactions[a][1], "N"),
        ("horizontal top displacement", 0.0, abs(res.node_displacement(b)[0]), "m"),
    ]


def portal_sway(cls, base):
    model = cls(E=E)
    n0 = model.add_node(0.0, 0.0)
    n1 = model.add_node(L, 0.0)
    n2 = model.add_node(0.0, H)
    n3 = model.add_node(L, H)
    model.add_member(n0, n2, COLUMN)
    model.add_member(n1, n3, COLUMN)
    model.add_member(n2, n3, RIGID)
    fixed = base == "fixed"
    model.add_support(n0, rotation=fixed)
    model.add_support(n1, rotation=fixed)
    model.add_point_load(n2, fx=P)
    res = model.solve()
    sway = res.node_displacement(n2)[0]
    if fixed:
        return [
            ("sway", P * H**3 / (24 * E * SEC.I), sway, "m"),
            ("base moment", P * H / 4, abs(res.reactions[n0][2]), "N m"),
        ]
    return [
        ("sway", P * H**3 / (6 * E * SEC.I), sway, "m"),
        ("column top moment", P * H / 2, abs(res.members[0].M[-1]), "N m"),
    ]


BENCHMARKS = [
    ("Cantilever, tip load", cantilever_point_load, 1e-9),
    ("Cantilever, uniform load", cantilever_udl, 1e-9),
    ("Simply supported beam, uniform load", simply_supported_udl, 1e-9),
    ("Simply supported beam defined right-to-left",
     lambda cls: simply_supported_udl(cls, reverse=True), 1e-9),
    ("Fixed-fixed beam, uniform load", fixed_fixed_udl, 1e-9),
    ("Inclined cantilever (30 deg), vertical tip load", inclined_cantilever, 1e-6),
    ("Vertical column, axial line load", column_axial_line_load, 1e-9),
    ("Portal frame, fixed bases, rigid beam", lambda cls: portal_sway(cls, "fixed"), 1e-4),
    ("Portal frame, pinned bases, rigid beam", lambda cls: portal_sway(cls, "pinned"), 1e-4),
]


def run_benchmarks(model_class=FrameModel):
    """
    Run all benchmarks on ``model_class`` (FrameModel or a subclass).

    Returns a list of dicts with keys case, quantity, expected, computed,
    unit, rel_error and passed.
    """
    rows = []
    for case, func, tol in BENCHMARKS:
        for quantity, expected, computed, unit in func(model_class):
            if expected == 0.0:
                err = abs(computed)
            else:
                err = abs(computed - expected) / abs(expected)
            rows.append({
                "case": case,
                "quantity": quantity,
                "expected": float(expected),
                "computed": float(computed),
                "unit": unit,
                "rel_error": float(err),
                "passed": bool(err <= tol),
            })
    return rows


if __name__ == "__main__":
    rows = run_benchmarks()
    print(f"{'case':48s} {'quantity':28s} {'expected':>12s} {'computed':>12s} {'rel.err':>9s}")
    for r in rows:
        flag = "ok" if r["passed"] else "FAIL"
        print(f"{r['case']:48s} {r['quantity']:28s} {r['expected']:12.5g} "
              f"{r['computed']:12.5g} {r['rel_error']:9.1e} {flag}")
    n_ok = sum(r["passed"] for r in rows)
    print(f"\n{n_ok}/{len(rows)} checks passed")
