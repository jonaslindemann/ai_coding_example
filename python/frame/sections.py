# -*- coding: utf-8 -*-
"""
Steel cross-section and material data for the plane frame model.

ENGINEER-OWNED DATA. Section properties are given in the units used in
manufacturer tables (cm^2, cm^4, cm^3) and converted to SI exactly once,
here. Values are nominal properties for bending about the strong axis
(y-y) of hot-rolled European IPE/HEA/HEB profiles. Check them against
your supplier's tables before using the model for anything real.
"""

from dataclasses import dataclass

CM2 = 1e-4   # cm^2 -> m^2
CM3 = 1e-6   # cm^3 -> m^3
CM4 = 1e-8   # cm^4 -> m^4


@dataclass(frozen=True)
class Section:
    """Cross-section properties in SI units."""

    name: str
    A: float     # area (m^2)
    I: float     # second moment of area, strong axis (m^4)
    W: float     # elastic section modulus, strong axis (m^3)

    @property
    def mass_per_m(self):
        """Mass per metre (kg/m) for steel density 7850 kg/m^3."""
        return STEEL_DENSITY * self.A


def _table(rows):
    return {
        name: Section(name, A * CM2, I * CM4, W * CM3)
        for name, A, I, W in rows
    }


#         name       A (cm^2)  Iy (cm^4)  Wel,y (cm^3)
SECTIONS = _table([
    ("IPE 200",   28.5,    1943,    194),
    ("IPE 240",   39.1,    3892,    324),
    ("IPE 270",   45.9,    5790,    429),
    ("IPE 300",   53.8,    8356,    557),
    ("IPE 330",   62.6,   11770,    713),
    ("IPE 360",   72.7,   16270,    904),
    ("IPE 400",   84.5,   23130,   1160),
    ("IPE 450",   98.8,   33740,   1500),
    ("HEA 160",   38.8,    1673,    220),
    ("HEA 200",   53.8,    3692,    389),
    ("HEA 240",   76.8,    7763,    675),
    ("HEA 280",   97.3,   13670,   1013),
    ("HEA 300",  112.5,   18260,   1260),
    ("HEB 200",   78.1,    5696,    570),
    ("HEB 240",  106.0,   11260,    938),
    ("HEB 300",  149.1,   25170,   1678),
])

E_STEEL = 210e9          # Young's modulus (Pa)
STEEL_DENSITY = 7850.0   # kg/m^3
GRAVITY = 9.81           # m/s^2

# Nominal yield strength (Pa) for thickness <= 40 mm
STEEL_GRADES = {
    "S235": 235e6,
    "S275": 275e6,
    "S355": 355e6,
}
