"""Design checks and design search for the footbridge truss.

Implements spec ``bridge_spec_final.md`` sections 6.3, 6.4 and 7 on top of
the frozen model in ``truss_model.py``. This module does no mechanics of its
own. Every force and displacement comes from ``TrussBridge.solve``.

Public model API used: ``TrussBridge(truss_type, L, h, n)``,
``solve(E, A_c, A_w, w) -> (a, r, N, N_max, N_min)``, ``section_classes``,
``lengths``, ``midspan_node`` and ``N_tol``.

All quantities are in SI units: N, m, Pa, kg.
"""

import math
from dataclasses import dataclass, field
from functools import cmp_to_key

import numpy as np

from truss_model import CLASS_CHORD, TrussBridge

# ---------------------------------------------------------------------------
# Data from the spec
# ---------------------------------------------------------------------------

SPAN = 20.0                  # L [m] (D1)
DECK_WIDTH = 2.5             # b [m] (D2)
CROWD_LOAD = 4.0e3           # q [N/m^2], characteristic (D3)
DEFLECTION_RATIO = 400.0     # limit L/400 (D8)

E_STEEL = 210.0e9            # E [Pa] (Q11)
DENSITY = 7850.0             # rho [kg/m^3] (Q13)

# Partial factors (spec 7, Q16): characteristic load, no factors.
GAMMA_Q = 1.0
GAMMA_M0 = 1.0
GAMMA_M1 = 1.0

# Design space (spec 6.4).
TRUSS_TYPE_ORDER = ("pratt", "howe", "warren")   # also the final tie-break order (R7)
N_VALUES = (4, 6, 8, 10)                         # Q9
H_VALUES = (3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0)   # Q10 [m]

# Ranking (spec 6.4, R7): masses equal within this relative tolerance.
MASS_REL_TOL = 1e-9

CHECK_YIELD = "C1 yield"
CHECK_BUCKLING = "C2 buckling"
CHECK_DEFLECTION = "C3 deflection"


@dataclass(frozen=True)
class Section:
    """A cross-section from the spec's section list (4.1), in SI units.

    Attributes
    ----------
    name : str
        Designation, for example ``"SHS 100x5"``.
    kind : str
        ``"SHS"`` (hot-finished hollow, EN 10210) or ``"IPE"`` (rolled, EN 10025-2).
    A : float
        Area [m^2].
    I_y, I_z : float
        Second moments of area about the strong and weak axes [m^4].
    t : float
        Thickness that governs f_y [m]: the wall for SHS, the flange for IPE.
    """

    name: str
    kind: str
    A: float
    I_y: float
    I_z: float
    t: float

    @property
    def I_min(self):
        """Governing second moment of area for buckling, min(I_y, I_z) (spec 7 C2)."""
        return min(self.I_y, self.I_z)

    @property
    def f_y(self):
        """Yield strength of S355 for this thickness [Pa] (spec D9)."""
        return yield_strength(self.t, self.kind)


def _section(name, kind, A_cm2, I_y_cm4, I_z_cm4, t_mm):
    # Convert the table units (spec 4.1) to SI: 1 cm^2 = 1e-4 m^2,
    # 1 cm^4 = 1e-8 m^4, 1 mm = 1e-3 m.
    return Section(name, kind, A_cm2 * 1e-4, I_y_cm4 * 1e-8, I_z_cm4 * 1e-8, t_mm * 1e-3)


#: Section list, spec 4.1 (approved, Q14), in the order of the table.
SECTIONS = (
    _section("SHS 60x4", "SHS", 8.79, 45.39, 45.39, 4.0),
    _section("SHS 80x4", "SHS", 11.99, 114.5, 114.5, 4.0),
    _section("SHS 80x5", "SHS", 14.73, 136.6, 136.6, 5.0),
    _section("SHS 100x4", "SHS", 15.19, 231.8, 231.8, 4.0),
    _section("SHS 100x5", "SHS", 18.73, 279.4, 279.4, 5.0),
    _section("SHS 100x6.3", "SHS", 23.19, 335.6, 335.6, 6.3),
    _section("SHS 120x5", "SHS", 22.73, 497.7, 497.7, 5.0),
    _section("SHS 120x6.3", "SHS", 28.23, 602.9, 602.9, 6.3),
    _section("SHS 140x6.3", "SHS", 33.27, 983.9, 983.9, 6.3),
    _section("SHS 150x6.3", "SHS", 35.79, 1223.0, 1223.0, 6.3),
    _section("SHS 150x8", "SHS", 44.75, 1491.0, 1491.0, 8.0),
    _section("SHS 160x8", "SHS", 47.95, 1831.0, 1831.0, 8.0),
    _section("SHS 200x8", "SHS", 60.75, 3709.0, 3709.0, 8.0),
    _section("SHS 200x10", "SHS", 74.93, 4471.0, 4471.0, 10.0),
    _section("IPE 100", "IPE", 10.32, 171.0, 16.0, 5.7),
    _section("IPE 120", "IPE", 13.21, 318.0, 28.0, 6.3),
    _section("IPE 140", "IPE", 16.43, 541.0, 45.0, 6.9),
    _section("IPE 160", "IPE", 20.09, 869.0, 68.0, 7.4),
    _section("IPE 180", "IPE", 23.95, 1317.0, 101.0, 8.0),
    _section("IPE 200", "IPE", 28.48, 1943.0, 142.0, 8.5),
    _section("IPE 220", "IPE", 33.37, 2772.0, 205.0, 9.2),
    _section("IPE 240", "IPE", 39.12, 3892.0, 284.0, 9.8),
    _section("IPE 270", "IPE", 45.95, 5790.0, 420.0, 10.2),
    _section("IPE 300", "IPE", 53.81, 8356.0, 604.0, 10.7),
)

SECTIONS_BY_NAME = {s.name: s for s in SECTIONS}


# ---------------------------------------------------------------------------
# Basic quantities
# ---------------------------------------------------------------------------

def yield_strength(t, kind):
    """Return f_y [Pa] of S355 for thickness t [m] (spec D9, EN 1993-1-1 Table 3.1).

    f_y = 355 MPa for t <= 40 mm, and 335 MPa for 40 < t <= 80 mm (rolled,
    EN 10025-2) or 40 < t <= 65 mm (hollow, EN 10210-1). Thicker sections are
    outside the table and raise ValueError.
    """
    if t <= 0.040:
        return 355.0e6
    upper = 0.065 if kind == "SHS" else 0.080
    if t <= upper:
        return 335.0e6
    raise ValueError(f"thickness {t * 1e3:g} mm is outside spec D9 for {kind}")


def line_load(q=CROWD_LOAD, b=DECK_WIDTH):
    """Return the line load on one truss, w = q * b / 2 [N/m] (spec D5)."""
    return q * b / 2.0


def nodal_loads(w, L, n):
    """Return (P, P_end) [N] for line load w, span L and n panels (spec D7)."""
    P = w * L / n
    return P, P / 2.0


# ---------------------------------------------------------------------------
# Design checks for one design (spec 6.3, 7)
# ---------------------------------------------------------------------------

@dataclass
class DesignResult:
    """Results of the design checks for one design (spec 6.3).

    Utilisation arrays have one entry per member, in the model's element
    order. U_buckling is 0 for members that are not compression members.
    Member numbers in ``governing_member`` are 1-based, and the value is None
    when the deflection check governs.
    """

    truss_type: str
    h: float
    n: int
    chord: Section
    web: Section
    w: float
    P: float
    P_end: float
    N_max: np.ndarray
    N_min: np.ndarray
    compression: np.ndarray
    U_yield: np.ndarray
    U_buckling: np.ndarray
    u_midspan: float
    U_deflection: float
    mass: float
    U_yield_max: float
    U_buckling_max: float
    U_max: float
    governing_check: str
    governing_member: object
    passes_yield: bool
    passes_buckling: bool
    passes_deflection: bool
    passes: bool
    member_groups: list = field(repr=False, default_factory=list)


def check_design(truss_type, h, n, chord, web, L=SPAN, q=CROWD_LOAD, b=DECK_WIDTH, E=E_STEEL):
    """Run checks C1 to C3 and compute the mass for one design (spec 7).

    Parameters
    ----------
    truss_type : str
        ``"pratt"``, ``"howe"`` or ``"warren"``.
    h : float
        Truss height [m].
    n : int
        Number of panels.
    chord, web : Section
        Sections S_c (chords and end posts) and S_w (verticals and diagonals).
    L, q, b, E : float
        Span [m], crowd load [N/m^2], deck width [m] and Young's modulus [Pa].
        The defaults are the spec values.

    Returns
    -------
    DesignResult
    """
    w = line_load(q, b)
    P, P_end = nodal_loads(w, L, n)

    bridge = TrussBridge(truss_type, L, h, n)
    a, _r, _N, N_max, N_min = bridge.solve(E, chord.A, web.A, w)

    is_chord = np.array([c == CLASS_CHORD for c in bridge.section_classes])
    A = np.where(is_chord, chord.A, web.A)
    I = np.where(is_chord, chord.I_min, web.I_min)
    f_y = np.where(is_chord, chord.f_y, web.f_y)
    ell = bridge.lengths

    # C1 yield, for tension and compression (spec 7).
    N_Ed = GAMMA_Q * np.maximum(np.abs(N_max), np.abs(N_min))
    U_yield = N_Ed / (A * f_y / GAMMA_M0)

    # C2 Euler buckling, compression members only (spec 7, 3.6):
    # L_cr = member length about both axes, I = min(I_y, I_z).
    compression = N_min < -bridge.N_tol
    N_cr = math.pi ** 2 * E * I / ell ** 2
    U_buckling = np.where(compression, GAMMA_Q * np.abs(N_min) / (N_cr / GAMMA_M1), 0.0)

    # C3 midspan deflection under LC-full (spec 7). DOF 2k of node k is
    # index 2k - 1.
    u_midspan = float(a[2 * bridge.midspan_node - 1])
    U_deflection = abs(u_midspan) / (L / DEFLECTION_RATIO)

    # Mass of one truss, members only (spec 7, Q20).
    mass = float(DENSITY * np.sum(A * ell))

    U_yield_max = float(U_yield.max())
    U_buckling_max = float(U_buckling.max())
    candidates = [
        (U_yield_max, CHECK_YIELD, int(np.argmax(U_yield)) + 1),
        (U_buckling_max, CHECK_BUCKLING, int(np.argmax(U_buckling)) + 1),
        (U_deflection, CHECK_DEFLECTION, None),
    ]
    # max() keeps the first of equal values, so ties go to C1, then C2, then C3.
    U_max, governing_check, governing_member = max(candidates, key=lambda c: c[0])

    return DesignResult(
        truss_type=bridge.truss_type, h=float(h), n=int(n), chord=chord, web=web,
        w=w, P=P, P_end=P_end, N_max=N_max, N_min=N_min, compression=compression,
        U_yield=U_yield, U_buckling=U_buckling, u_midspan=u_midspan,
        U_deflection=U_deflection, mass=mass, U_yield_max=U_yield_max,
        U_buckling_max=U_buckling_max, U_max=float(U_max),
        governing_check=governing_check, governing_member=governing_member,
        passes_yield=U_yield_max <= 1.0, passes_buckling=U_buckling_max <= 1.0,
        passes_deflection=U_deflection <= 1.0, passes=float(U_max) <= 1.0,
        member_groups=list(bridge.member_groups),
    )


# ---------------------------------------------------------------------------
# Design search and ranking (spec 6.4)
# ---------------------------------------------------------------------------

def compare_designs(d1, d2):
    """Order two designs by the ranking in spec 6.4 (R7).

    1. Mass, where masses within a relative 1e-9 count as equal.
    2. Lower maximum utilisation U_max.
    3. Truss type in the order Pratt, Howe, Warren.

    Returns a negative, zero or positive number, as for ``cmp_to_key``.
    """
    if abs(d1.mass - d2.mass) > MASS_REL_TOL * max(d1.mass, d2.mass):
        return -1 if d1.mass < d2.mass else 1
    if d1.U_max != d2.U_max:
        return -1 if d1.U_max < d2.U_max else 1
    o1 = TRUSS_TYPE_ORDER.index(d1.truss_type)
    o2 = TRUSS_TYPE_ORDER.index(d2.truss_type)
    return o1 - o2


def rank_designs(designs):
    """Return the designs sorted by the spec 6.4 ranking (lightest first)."""
    return sorted(designs, key=cmp_to_key(compare_designs))


@dataclass
class SearchResult:
    """Result of the design search (spec 6.4).

    Attributes
    ----------
    passing : list of DesignResult
        All designs that pass every check, ranked lightest first.
    closest : DesignResult or None
        Set only when no design passes: the design with the lowest U_max,
        with its governing member and check (R9).
    num_designs : int
        Number of designs checked.
    """

    passing: list
    closest: object
    num_designs: int

    @property
    def lightest(self):
        """The lightest passing design, or None if no design passes."""
        return self.passing[0] if self.passing else None


def design_search(truss_types=TRUSS_TYPE_ORDER, n_values=N_VALUES, h_values=H_VALUES,
                  sections=SECTIONS, L=SPAN, q=CROWD_LOAD, b=DECK_WIDTH, E=E_STEEL,
                  progress=None):
    """Check every design in the search space and rank the passing ones (spec 6.4).

    The search space is every combination of truss type, n, h, chord
    section and web section. By default this is the spec's space:
    3 * 4 * 7 * 24^2 = 48 384 designs. Each design calls ``solve``.

    Parameters
    ----------
    truss_types, n_values, h_values, sections : sequences
        The search space. The defaults are the spec values.
    L, q, b, E : float
        As in :func:`check_design`.
    progress : callable, optional
        Called as ``progress(done, total)`` after each design, for example
        to update a progress bar.

    Returns
    -------
    SearchResult
    """
    total = len(truss_types) * len(n_values) * len(h_values) * len(sections) ** 2
    passing = []
    closest = None
    done = 0
    for truss_type in truss_types:
        for n in n_values:
            for h in h_values:
                for chord in sections:
                    for web in sections:
                        d = check_design(truss_type, h, n, chord, web, L=L, q=q, b=b, E=E)
                        if d.passes:
                            passing.append(d)
                        elif closest is None or d.U_max < closest.U_max:
                            closest = d
                        done += 1
                        if progress is not None:
                            progress(done, total)

    return SearchResult(
        passing=rank_designs(passing),
        closest=None if passing else closest,
        num_designs=done,
    )
