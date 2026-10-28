# -*- coding: utf-8 -*-
"""
Design search over section combinations for a PlaneFrame.

AI-ASSISTED APPLICATION LAYER. The search only builds and solves frames
with the verified core and reads its summary() - pass/fail and limits
come from PlaneFrame, not from here. The one engineering decision in this
module is a parameter: which sections are allowed as columns. The model
has no buckling check, so slender I-sections (IPE) are excluded as
columns by default.

Run ``python frame_design.py`` for a table of the lightest designs of the
reference frame with pinned bases.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from frame_model import PlaneFrame      # noqa: E402
from sections import SECTIONS           # noqa: E402


def column_candidates(h_sections_only=True):
    """Column sections; IPE excluded by default (no buckling check)."""
    return [n for n in SECTIONS if not (h_sections_only and n.startswith("IPE"))]


def beam_candidates():
    """Beam sections: IPE profiles, the usual choice for floor beams."""
    return [n for n in SECTIONS if n.startswith("IPE")]


def check_ratios(frame, summary):
    """Each check as a ratio of its limit (1.0 = exactly at the limit)."""
    return {
        "drift": summary["drift_ratio"] / frame.DRIFT_LIMIT,
        "deflection": summary["deflection_ratio"] / frame.DEFLECTION_LIMIT,
        "utilisation": summary["max_utilisation"],
    }


def design_search(params, columns, beams):
    """
    Solve every column/beam combination for the given frame parameters.

    ``params`` are PlaneFrame keyword arguments; column_section and
    beam_section are overridden. Returns one dict per combination, passing
    designs first, each group sorted by steel mass.
    """
    rows = []
    for column in columns:
        for beam in beams:
            frame = PlaneFrame(**dict(params, column_section=column, beam_section=beam))
            frame.solve()
            s = frame.summary()
            ratios = check_ratios(frame, s)
            governs = max(ratios, key=ratios.get)
            rows.append({
                "column": column,
                "beam": beam,
                "mass": s["steel_mass"],
                "drift": s["drift_ratio"],
                "deflection": s["deflection_ratio"],
                "utilisation": s["max_utilisation"],
                "ratio": ratios[governs],
                "governs": governs,
                "ok": s["drift_ok"] and s["deflection_ok"] and s["utilisation_ok"],
            })
    rows.sort(key=lambda r: (not r["ok"], r["mass"]))
    return rows


if __name__ == "__main__":
    rows = design_search(dict(base="pinned"), column_candidates(), beam_candidates())
    print("Lightest designs, reference frame with pinned bases, H-section columns:")
    for r in [r for r in rows if r["ok"]][:8]:
        print(f"  {r['column']:8s} {r['beam']:8s} {r['mass']:6.0f} kg   "
              f"drift h/{1 / r['drift']:.0f}   deflection L/{1 / r['deflection']:.0f}   "
              f"utilisation {100 * r['utilisation']:.0f} %   governs: {r['governs']}")
    print(f"{sum(r['ok'] for r in rows)} of {len(rows)} combinations pass all checks")
