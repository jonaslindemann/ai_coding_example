# Problem specification

* Truss types (Pratt, Howe, Warren), span L, height h and number of panels n. No end panels: there are no vertical members over the supports (see Geometry below).
* Linear elastic material, small displacements, pin-jointed members, axial force only.
* Supports: a pin at the left end and a roller (rolls in the horizontal direction) at the right end.
* Loads: P at each interior bottom-chord node (except the supports). Positive downward. No other loads (no self-weight, no horizontal loads, no top-chord loads).
* Units: SI, with N, m and Pa throughout (areas in m²). No unit conversion at the interface.
* Sign convention: tension is positive.
* Required outputs: nodal displacements, normal forces, reactions.
* Material properties: Young's modulus E, cross-sectional area A for each member. Same value for all members.
* Geometric properties: span L, height h (distance between top and bottom chords centerlines), number of panels n (even, n ≥ 2).
* Coordinates: nodal coordinates for the truss nodes, defined based on the span L, height h, and number of panels n. Left support is at the origin (0,0), x to the right, y upward.
* Verification: the model should be verified against known analytical solutions or benchmark problems for 2D truss bridges. Global equilibrium and member force consistency should be checked.
* Assumptions: all members are pin-jointed, only axial forces are considered, and displacements are small.

## Geometry

Panel width is L/n. The bottom chord has n + 1 nodes at x = i·L/n, y = 0 (i = 0..n). The supports are the two end nodes of the bottom chord, at (0, 0) and (L, 0).

* **Pratt**: trapezoidal with inclined end posts. Top nodes at x = i·L/n, y = h for i = 1..n−1, and none above the supports. Verticals at every interior bottom node. One diagonal per interior panel, sloping down toward midspan. The diagonals are mirrored about midspan.
* **Howe**: same nodes, chords, verticals and end posts as Pratt. The diagonals slope down toward the supports.
* **Warren**: top nodes above the bottom-panel midpoints, at x = (i + ½)·L/n, y = h for i = 0..n−1. No verticals. Two diagonals per panel, alternating up and down.

| Type | Nodes j | Members m | Reactions r |
| --- | --- | --- | --- |
| Pratt | 2n | 4n − 3 | 3 |
| Howe | 2n | 4n − 3 | 3 |
| Warren | 2n + 1 | 4n − 1 | 3 |

All three layouts are statically determinate: m + r = 2j.

## Numbering conventions

* Nodes (1-based): the bottom chord left to right (1..n+1), then the top chord left to right.
* DOFs (1-based, as CALFEM expects): node i has [2i−1, 2i] = [ux, uy].
* Elements: bottom chord, top chord, verticals, then diagonals, each group left to right. The end posts count as diagonals.
* Constrained DOFs: ux and uy at node 1 (pin), and uy at node n+1 (roller). Prescribed displacements are zero, so no support settlement.

## Interface and outputs

* `TrussBridge(truss_type, L, h, n)` builds the geometry and topology. `truss_type` is "pratt", "howe" or "warren", case-insensitive.
* `solve(E, A, P)` runs the analysis and returns `(a, r, N)`, which are also stored as attributes:
  * `a`: nodal displacements [m], column vector of length 2j, in DOF order.
  * `r`: reactions [N], column vector of length 2j in global x/y directions, so an upward support force is positive. Non-zero only at the constrained DOFs, up to round-off.
  * `N`: normal force [N] per member, length m, tension positive.
* Invalid input raises an error instead of being replaced by a default:
  * the truss type is not one of the three
  * n is not an even integer ≥ 2
  * L, h, E or A is not positive
  * P is not finite

  P may be negative, which means it acts upward.
* No default values for any input.

## Implementation rules

* Mechanics uses only `calfem.core`: `bar2e`, `bar2s`, `assem`, `solveq`, `extract_eldisp`. No custom element formulations.
* No plotting or UI code in the model module (`truss_model.py`). Visualization lives in a separate module (`plot_truss.py`).
