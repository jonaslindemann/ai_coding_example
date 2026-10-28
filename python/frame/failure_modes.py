# -*- coding: utf-8 -*-
"""
Plausible but wrong: three realistic mistakes and which checks catch them.

Each variant runs without errors, produces reasonable-looking plots and
numbers, and is wrong. Run ``python failure_modes.py`` to compare them
with the verified core and see which line of defence catches each one:

    1. Global loads passed to beam2e as local loads
       -> caught by the equilibrium check and the benchmarks
    2. Section table converted with the wrong unit factor (cm^4 as cm^2)
       -> NOT caught by benchmarks or equilibrium; caught by a data test
    3. User interface maps "pinned" to the default "fixed"
       -> passes every automated check; only an input echo in the report
          and engineering judgement catch it
"""

import numpy as np

from frame_model import FrameModel, PlaneFrame
from sections import Section, CM2, CM4
from verification import run_benchmarks

PARAMS = dict(n_bays=2, n_storeys=3, base="pinned", wind_load=12e3)


class GlobalAsLocalLoads:
    """Mistake 1: pass global (qx, qy) straight to beam2e as eq."""

    @staticmethod
    def local_line_load(c, s, qx, qy):
        return np.array([qx, qy])


class NaiveFrameModel(GlobalAsLocalLoads, FrameModel):
    pass


class NaivePlaneFrame(GlobalAsLocalLoads, PlaneFrame):
    pass


def wrong_units_frame(**params):
    """Mistake 2: second moment of area converted with CM2 instead of CM4."""
    frame = PlaneFrame(**params)
    for m in frame.members:
        sec = m.section
        m.section = Section(sec.name, sec.A, sec.I / CM4 * CM2, sec.W)
    return frame


def ui_lost_base_condition(**params):
    """Mistake 3: an option key typo in the UI silently falls back to 'fixed'."""
    ui_value = params.pop("base")
    options = {"Fixed": "fixed", "Pinned ": "pinned"}  # note the trailing space
    params["base"] = options.get(ui_value.capitalize(), "fixed")
    return PlaneFrame(**params)


def _depth_estimate(section):
    """I/W = h/2 for a doubly symmetric section, so h = 2 I / W (m)."""
    return 2 * section.I / section.W


def row(label, frame, reference, model_class=FrameModel):
    frame.solve()
    s, r = frame.summary(), reference.summary()
    eq_ok = max(frame.results.equilibrium_error().values()) < 1e-8
    # Benchmarks run on the same model code as the frame
    bench_ok = all(b["passed"] for b in run_benchmarks(model_class))
    # Sanity check: a plausible section depth (0.1 - 1.0 m) from I/W
    depth_ok = all(0.1 < _depth_estimate(m.section) < 1.0 for m in frame.members)

    def err(key):
        return 100 * (s[key] - r[key]) / r[key]

    print(f"\n{label}")
    print(f"  roof sway        {1e3 * s['top_sway']:8.2f} mm   (correct {1e3 * r['top_sway']:.2f} mm, {err('top_sway'):+.0f} %)")
    print(f"  beam deflection  {1e3 * s['max_beam_deflection']:8.2f} mm   (correct {1e3 * r['max_beam_deflection']:.2f} mm, {err('max_beam_deflection'):+.0f} %)")
    print(f"  max utilisation  {100 * s['max_utilisation']:8.1f} %    (correct {100 * r['max_utilisation']:.1f} %)")
    print(f"  all limits met   {str(s['drift_ok'] and s['deflection_ok'] and s['utilisation_ok']):>8s}")
    print(f"  equilibrium check   {'pass' if eq_ok else 'FAIL'}")
    print(f"  analytical benchmarks {'pass' if bench_ok else 'FAIL'}")
    print(f"  section depth from I/W plausible {'pass' if depth_ok else 'FAIL'}")
    print(f"  input echo: base = {frame.base!r} (requested {PARAMS['base']!r})")


if __name__ == "__main__":
    reference = PlaneFrame(**PARAMS)
    reference.solve()
    print("Verified core, requested input:", PARAMS)

    row("1. Global loads used as local loads in beam2e",
        NaivePlaneFrame(**PARAMS), reference, NaiveFrameModel)
    row("2. I converted from cm^4 with the cm^2 factor",
        wrong_units_frame(**PARAMS), reference)
    row("3. UI option typo: 'Pinned' silently becomes 'fixed'",
        ui_lost_base_condition(**dict(PARAMS)), reference)
