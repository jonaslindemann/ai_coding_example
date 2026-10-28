# -*- coding: utf-8 -*-
"""
Plane steel frames analysed with CALFEM beam2e elements.

ENGINEER-OWNED COMPUTATIONAL CORE. This module is the part of the example
that the engineer writes, reads line by line and verifies (see
verification.py and test_frame_model.py). Everything else - the web
application and the report - is built on top of it and must not change it.

Two classes are provided:

    FrameModel  - a generic 2D frame: nodes, members, supports and loads.
    PlaneFrame  - a parametric multi-bay, multi-storey building frame
                  generated on top of FrameModel.

Modelling assumptions
---------------------
* Linear elastic, first-order (small displacement) analysis. No P-delta
  effects, no buckling, no lateral-torsional buckling.
* Euler-Bernoulli beams with axial deformation (CALFEM beam2e). Shear
  deformation is neglected.
* Rigid beam-column connections. Column bases are either fixed or pinned.
* Each structural member is one beam2e element. With element loads this
  is exact for Euler-Bernoulli beams, so no mesh refinement is needed.
* Utilisation is the elastic extreme-fibre stress |N|/A + |M|/W divided
  by the yield strength. It is NOT a design code check: stability,
  partial factors and load combinations are the engineer's responsibility.

Units and sign conventions
--------------------------
* SI units throughout: m, N, N/m, Pa.
* Global x to the right, global y upwards. Rotations counter-clockwise.
* Line loads are given in GLOBAL directions per unit member length and
  converted here to the LOCAL directions that beam2e expects.
* Normal force N is positive in tension. The bending moment M follows
  CALFEM: M = EI v'' in local coordinates. Moment diagrams are drawn on
  the tension side, i.e. in the -M local y direction.
"""

from dataclasses import dataclass, field

import numpy as np
import calfem.core as cfc

from sections import SECTIONS, E_STEEL, STEEL_DENSITY, GRAVITY, STEEL_GRADES


def beam2_section_forces(ex, ey, ep, ed, eq, n_points):
    """
    Section forces and local displacements along a beam2e element.

    Same exact Euler-Bernoulli solution as calfem.core.beam2s, but with
    evaluation points from np.linspace. beam2s (CALFEM 3.6.16) builds its
    points with np.arange on floats, which for some lengths returns one
    point too many and fails. test_frame_model.py checks that both give
    identical results where beam2s works.

    Returns es (n, 3) = [N, V, M], edi (n, 2) = [u, v] and s (n,).
    """
    E, A, I = ep
    qX, qY = eq
    dx, dy = ex[1] - ex[0], ey[1] - ey[0]
    L = np.hypot(dx, dy)
    c, s = dx / L, dy / L

    G = np.array([
        [ c, s, 0, 0, 0, 0],
        [-s, c, 0, 0, 0, 0],
        [ 0, 0, 1, 0, 0, 0],
        [ 0, 0, 0, c, s, 0],
        [ 0, 0, 0,-s, c, 0],
        [ 0, 0, 0, 0, 0, 1],
    ])
    u1, v1, t1, u2, v2, t2 = G @ np.asarray(ed, dtype=float).ravel()

    X = np.linspace(0.0, L, n_points)

    # Axial: linear field plus particular solution for qX
    u = u1 + (u2 - u1) * X / L - (X**2 - L * X) * qX / (2 * E * A)
    du = (u2 - u1) / L - (2 * X - L) * qX / (2 * E * A)

    # Bending: cubic Hermite field plus particular solution for qY
    c2 = -3 * v1 / L**2 - 2 * t1 / L + 3 * v2 / L**2 - t2 / L
    c3 = 2 * v1 / L**3 + t1 / L**2 - 2 * v2 / L**3 + t2 / L**2
    v = (v1 + t1 * X + c2 * X**2 + c3 * X**3
         + (X**4 - 2 * L * X**3 + L**2 * X**2) * qY / (24 * E * I))
    d2v = 2 * c2 + 6 * c3 * X + (6 * X**2 - 6 * L * X + L**2) * qY / (12 * E * I)
    d3v = 6 * c3 + (2 * X - L) * qY / (2 * E * I)

    es = np.column_stack([E * A * du, -E * I * d3v, E * I * d2v])
    edi = np.column_stack([u, v])
    return es, edi, X


@dataclass
class Member:
    """A straight frame member between two nodes."""

    i: int
    j: int
    section: object
    kind: str = "member"
    qx: float = 0.0          # global line load, x direction (N/m)
    qy: float = 0.0          # global line load, y direction (N/m)


@dataclass
class MemberResult:
    """Section forces and displacements along one member."""

    member: Member
    s: np.ndarray            # local coordinate along the member (m)
    N: np.ndarray            # normal force (N), tension positive
    V: np.ndarray            # shear force (N)
    M: np.ndarray            # bending moment (N m)
    x: np.ndarray            # global x of the evaluation points
    y: np.ndarray            # global y of the evaluation points
    ux: np.ndarray           # global x displacement at the points
    uy: np.ndarray           # global y displacement at the points
    deflection: np.ndarray   # transverse displacement relative to the chord
    stress: np.ndarray       # |N|/A + |M|/W (Pa)

    @property
    def length(self):
        return self.s[-1]

    @property
    def max_abs_moment(self):
        return np.max(np.abs(self.M))

    @property
    def max_stress(self):
        return np.max(self.stress)

    @property
    def max_deflection(self):
        return np.max(np.abs(self.deflection))


@dataclass
class FrameResults:
    """Results of a linear static analysis of a FrameModel."""

    a: np.ndarray                                # global displacements
    r: np.ndarray                                # reaction forces
    members: list = field(default_factory=list)  # list of MemberResult
    reactions: dict = field(default_factory=dict)  # node -> (Rx, Ry, Mz)
    support_coords: dict = field(default_factory=dict)  # node -> (x, y)
    applied: tuple = (0.0, 0.0, 0.0)             # resultant of applied loads
    fy: float = np.inf

    def node_displacement(self, node):
        """(ux, uy, rotation) of a node."""
        return self.a[3 * node: 3 * node + 3, 0]

    @property
    def utilisation(self):
        """Maximum utilisation of each member (stress / fy)."""
        return np.array([m.max_stress for m in self.members]) / self.fy

    def equilibrium_error(self):
        """
        Global equilibrium check, independent of the stiffness matrix.

        Sums the reactions and the applied loads (computed directly from
        the load definitions) and returns the relative residual of the
        force and moment balance. Should be at round-off level.
        """
        Fx, Fy, Mo = self.applied
        Rx = sum(R[0] for R in self.reactions.values())
        Ry = sum(R[1] for R in self.reactions.values())
        # Moment about the origin: reaction moment plus moment of the
        # reaction forces
        Ro = 0.0
        for node, (rx, ry, mz) in self.reactions.items():
            x, y = self.support_coords[node]
            Ro += mz + x * ry - y * rx
        scale = max(abs(Fx), abs(Fy), 1.0)
        return {
            "Fx": abs(Fx + Rx) / scale,
            "Fy": abs(Fy + Ry) / scale,
            "M": abs(Mo + Ro) / max(abs(Mo), scale),
        }


class FrameModel:
    """
    Generic plane frame made of beam2e elements.

    Parameters
    ----------
    E : float
        Young's modulus (Pa).
    fy : float
        Yield strength (Pa) used for the utilisation.
    n_points : int
        Number of evaluation points along each member for section forces
        and displacements.
    """

    def __init__(self, E=E_STEEL, fy=STEEL_GRADES["S355"], n_points=21):
        self.E = E
        self.fy = fy
        self.n_points = n_points

        self.coords = []          # list of (x, y)
        self.members = []         # list of Member
        self.supports = {}        # node -> (fix_x, fix_y, fix_rotation)
        self.point_loads = {}     # node -> np.array([Fx, Fy, M])
        self.results = None

    # ------------------------------------------------------------------
    # Model definition
    # ------------------------------------------------------------------

    def add_node(self, x, y):
        self.coords.append((float(x), float(y)))
        return len(self.coords) - 1

    def add_member(self, i, j, section, kind="member"):
        if isinstance(section, str):
            section = SECTIONS[section]
        if i == j:
            raise ValueError("A member must connect two different nodes.")
        self.members.append(Member(i, j, section, kind))
        return len(self.members) - 1

    def add_support(self, node, x=True, y=True, rotation=True):
        self.supports[node] = (x, y, rotation)

    def add_point_load(self, node, fx=0.0, fy=0.0, m=0.0):
        load = self.point_loads.setdefault(node, np.zeros(3))
        load += (fx, fy, m)

    def add_line_load(self, member, qx=0.0, qy=0.0):
        """Uniform line load in GLOBAL directions (N per m of member)."""
        self.members[member].qx += qx
        self.members[member].qy += qy

    def add_self_weight(self):
        """Steel self-weight as a downward line load on every member."""
        for k, m in enumerate(self.members):
            self.add_line_load(k, qy=-STEEL_DENSITY * GRAVITY * m.section.A)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def n_nodes(self):
        return len(self.coords)

    @staticmethod
    def dofs(node):
        """CALFEM (1-based) degrees of freedom of a node."""
        return [3 * node + 1, 3 * node + 2, 3 * node + 3]

    def member_geometry(self, m):
        """ex, ey, length and direction cosines of a member."""
        (x1, y1), (x2, y2) = self.coords[m.i], self.coords[m.j]
        L = np.hypot(x2 - x1, y2 - y1)
        return np.array([x1, x2]), np.array([y1, y2]), L, (x2 - x1) / L, (y2 - y1) / L

    @staticmethod
    def local_line_load(c, s, qx, qy):
        """
        Transform a global line load (qx, qy) to the local member axes.

        beam2e expects eq = [qX, qY] along and perpendicular to the member.
        Passing global components directly is only correct for members
        pointing in the +x direction - a classic, silent mistake.
        """
        return np.array([c * qx + s * qy, -s * qx + c * qy])

    def applied_load_resultant(self):
        """
        Resultant (Fx, Fy, M about the origin) of all applied loads,
        computed directly from the load definitions.
        """
        Fx = Fy = Mo = 0.0
        for node, (fx, fy, m) in self.point_loads.items():
            x, y = self.coords[node]
            Fx += fx
            Fy += fy
            Mo += m + x * fy - y * fx
        for m in self.members:
            ex, ey, L, _, _ = self.member_geometry(m)
            fx, fy = m.qx * L, m.qy * L
            xm, ym = ex.mean(), ey.mean()
            Fx += fx
            Fy += fy
            Mo += xm * fy - ym * fx
        return Fx, Fy, Mo

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def solve(self):
        if not self.supports:
            raise ValueError("The frame has no supports.")

        n_dofs = 3 * self.n_nodes
        K = np.zeros((n_dofs, n_dofs))
        f = np.zeros((n_dofs, 1))

        element_data = []
        for m in self.members:
            ex, ey, L, c, s = self.member_geometry(m)
            ep = [self.E, m.section.A, m.section.I]
            eq = self.local_line_load(c, s, m.qx, m.qy)
            edof = np.array(self.dofs(m.i) + self.dofs(m.j))
            Ke, fe = cfc.beam2e(ex, ey, ep, eq)
            cfc.assem(edof, K, Ke, f, fe)
            element_data.append((ex, ey, ep, eq, edof, L, c, s))

        for node, load in self.point_loads.items():
            f[np.array(self.dofs(node)) - 1, 0] += load

        bc = [
            dof
            for node, fixed in self.supports.items()
            for dof, is_fixed in zip(self.dofs(node), fixed)
            if is_fixed
        ]
        bc = np.array(sorted(bc))

        try:
            a, r = cfc.solveq(K, f, bc)
        except np.linalg.LinAlgError:
            raise ValueError("The frame is a mechanism (singular stiffness matrix).")
        if not np.all(np.isfinite(a)):
            raise ValueError("The frame is a mechanism (singular stiffness matrix).")

        results = FrameResults(a=a, r=r, applied=self.applied_load_resultant(), fy=self.fy)

        for node in self.supports:
            idx = np.array(self.dofs(node)) - 1
            results.reactions[node] = tuple(r[idx, 0])
            results.support_coords[node] = self.coords[node]

        for m, (ex, ey, ep, eq, edof, L, c, s) in zip(self.members, element_data):
            ed = cfc.extract_ed(edof, a)
            es, edi, eci = beam2_section_forces(ex, ey, ep, ed, eq, self.n_points)

            u_loc, v_loc = edi[:, 0], edi[:, 1]
            chord = v_loc[0] + (v_loc[-1] - v_loc[0]) * eci / L
            A, I = ep[1], ep[2]
            stress = np.abs(es[:, 0]) / A + np.abs(es[:, 2]) / m.section.W

            results.members.append(MemberResult(
                member=m,
                s=eci,
                N=es[:, 0],
                V=es[:, 1],
                M=es[:, 2],
                x=ex[0] + c * eci,
                y=ey[0] + s * eci,
                ux=c * u_loc - s * v_loc,
                uy=s * u_loc + c * v_loc,
                deflection=v_loc - chord,
                stress=stress,
            ))

        self.results = results
        return results


class PlaneFrame(FrameModel):
    """
    Parametric multi-bay, multi-storey steel building frame.

    Parameters
    ----------
    n_bays, bay_width : int, float
        Number of bays and their width (m).
    n_storeys, storey_height : int, float
        Number of storeys and their height (m).
    column_section, beam_section : str
        Section names from sections.SECTIONS.
    base : str
        "fixed" or "pinned" column bases.
    floor_load, roof_load : float
        Uniform downward line load on floor and roof beams (N/m).
    wind_load : float
        Horizontal point load at each floor level, applied at the windward
        (left) column (N). The value is applied as given.
    self_weight : bool
        Include steel self-weight of all members.
    steel_grade : str
        Steel grade from sections.STEEL_GRADES.
    """

    # Serviceability limits (engineer-owned, typical values)
    DRIFT_LIMIT = 1 / 300        # interstorey drift / storey height
    DEFLECTION_LIMIT = 1 / 250   # beam deflection / span

    def __init__(
        self,
        n_bays=2,
        bay_width=6.0,
        n_storeys=3,
        storey_height=3.6,
        column_section="HEA 240",
        beam_section="IPE 360",
        base="fixed",
        floor_load=25e3,
        roof_load=15e3,
        wind_load=12e3,
        self_weight=True,
        steel_grade="S355",
        E=E_STEEL,
        n_points=21,
    ):
        if n_bays < 1 or n_storeys < 1:
            raise ValueError("The frame needs at least one bay and one storey.")
        if bay_width <= 0 or storey_height <= 0:
            raise ValueError("Bay width and storey height must be positive.")
        if base not in ("fixed", "pinned"):
            raise ValueError(f"Unknown base condition '{base}'.")
        if column_section not in SECTIONS or beam_section not in SECTIONS:
            raise ValueError("Unknown section name.")
        if steel_grade not in STEEL_GRADES:
            raise ValueError(f"Unknown steel grade '{steel_grade}'.")

        super().__init__(E=E, fy=STEEL_GRADES[steel_grade], n_points=n_points)

        self.n_bays = int(n_bays)
        self.bay_width = float(bay_width)
        self.n_storeys = int(n_storeys)
        self.storey_height = float(storey_height)
        self.column_section = column_section
        self.beam_section = beam_section
        self.base = base
        self.floor_load = float(floor_load)
        self.roof_load = float(roof_load)
        self.wind_load = float(wind_load)
        self.self_weight = bool(self_weight)
        self.steel_grade = steel_grade

        self.columns = []   # member indices
        self.beams = []     # member indices
        self.build()

    def node(self, column_line, level):
        """Node index at column line 0..n_bays and level 0..n_storeys."""
        return level * (self.n_bays + 1) + column_line

    @property
    def width(self):
        return self.n_bays * self.bay_width

    @property
    def height(self):
        return self.n_storeys * self.storey_height

    def build(self):
        for level in range(self.n_storeys + 1):
            for col in range(self.n_bays + 1):
                self.add_node(col * self.bay_width, level * self.storey_height)

        for level in range(self.n_storeys):
            for col in range(self.n_bays + 1):
                self.columns.append(self.add_member(
                    self.node(col, level), self.node(col, level + 1),
                    self.column_section, "column"))

        for level in range(1, self.n_storeys + 1):
            q = self.roof_load if level == self.n_storeys else self.floor_load
            for bay in range(self.n_bays):
                k = self.add_member(
                    self.node(bay, level), self.node(bay + 1, level),
                    self.beam_section, "beam")
                self.beams.append(k)
                self.add_line_load(k, qy=-q)

        fixed = self.base == "fixed"
        for col in range(self.n_bays + 1):
            self.add_support(self.node(col, 0), x=True, y=True, rotation=fixed)

        for level in range(1, self.n_storeys + 1):
            self.add_point_load(self.node(0, level), fx=self.wind_load)

        if self.self_weight:
            self.add_self_weight()

    # ------------------------------------------------------------------
    # Engineering summary
    # ------------------------------------------------------------------

    def storey_drifts(self):
        """Maximum interstorey drift (m) of each storey, bottom to top."""
        if self.results is None:
            self.solve()
        u = self.results.a[0::3, 0]
        drifts = []
        for level in range(1, self.n_storeys + 1):
            drifts.append(max(
                abs(u[self.node(c, level)] - u[self.node(c, level - 1)])
                for c in range(self.n_bays + 1)
            ))
        return np.array(drifts)

    def steel_mass(self):
        """Total steel mass (kg)."""
        return sum(
            m.section.mass_per_m * self.member_geometry(m)[2] for m in self.members
        )

    def summary(self):
        """Key results and serviceability/strength checks as a dict."""
        res = self.results if self.results is not None else self.solve()
        drifts = self.storey_drifts()
        beam_defl = np.array([res.members[k].max_deflection for k in self.beams])
        util = res.utilisation
        top = [self.node(c, self.n_storeys) for c in range(self.n_bays + 1)]
        crit = int(np.argmax(util))
        eq = res.equilibrium_error()

        drift_ratio = drifts.max() / self.storey_height
        defl_ratio = beam_defl.max() / self.bay_width

        return {
            # Sway = mean horizontal roof displacement. Individual roof
            # nodes also move due to beam axial deformation.
            "top_sway": abs(np.mean([res.a[3 * n, 0] for n in top])),
            "max_drift": drifts.max(),
            "max_drift_storey": int(np.argmax(drifts)) + 1,
            "drift_ratio": drift_ratio,
            "drift_ok": drift_ratio <= self.DRIFT_LIMIT,
            "max_beam_deflection": beam_defl.max(),
            "deflection_ratio": defl_ratio,
            "deflection_ok": defl_ratio <= self.DEFLECTION_LIMIT,
            "max_utilisation": util[crit],
            "critical_member": crit,
            "critical_kind": self.members[crit].kind,
            "utilisation_ok": util[crit] <= 1.0,
            "max_moment": max(m.max_abs_moment for m in res.members),
            "max_compression": -min(m.N.min() for m in res.members),
            "equilibrium_error": max(eq.values()),
            "steel_mass": self.steel_mass(),
        }
