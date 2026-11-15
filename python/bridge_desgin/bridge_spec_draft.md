# Footbridge truss: specification

Status: **DRAFT.** Every item marked **[Qn]** is waiting for an answer from the
client or the engineer. Items marked *proposed* are conventions I have
suggested. They need confirmation before any code is written. Nothing in
this document is final until the open questions in section 9 are answered.

Source: `problem.md` (client text, quoted in full):

> A pedestrian bridge is to cross a 20 m wide stream. The deck is 2.5 m wide
> and is carried by two identical steel trusses, one on each side. Design for
> a crowd load of 4 kN/m² on the deck and ignore self-weight in this first
> version. The steel is S355. The midspan deflection under crowd load must
> not exceed L/400. No member may yield, and no compression member may
> buckle. Which truss type (Pratt, Howe or Warren), height and member size
> gives the lightest design?

---

## 1. Scope

- One of the two identical trusses is modelled as a plane (2D) pin-jointed
  truss in CALFEM for Python.
- Members carry axial force only. Joints are ideal pins, and loads act only
  at nodes.
- Analysis is linear elastic with small displacements.
- The model is used to compare Pratt, Howe and Warren trusses over a range of
  heights h, panel counts n and member sections. It returns the lightest
  design that passes all the design checks in section 7.

Out of scope until confirmed otherwise **[Q21]**: connections, fatigue,
vibration and pedestrian comfort, wind and other lateral loads, deck and
cross-beam design, and bracing design.

---

## 2. Values derived from the text

| ID | Quantity | Symbol | Value | Derivation |
|---|---|---|---|---|
| D1 | Span | L | 20 m | "cross a 20 m wide stream". Taking the span as the stream width **[Q1]**. |
| D2 | Deck width | b | 2.5 m | Stated directly. |
| D3 | Crowd load (area) | q | 4 kN/m² | Stated directly. Characteristic value. |
| D4 | Deck load per metre of bridge | q·b | 10 kN/m | 4 kN/m² · 2.5 m = 10 kN/m |
| D5 | Line load on one truss | w | 5 kN/m | See D5 below. |
| D6 | Total load on one truss | W | 100 kN | w·L = 5 kN/m · 20 m |
| D7 | Interior nodal load | P | w·L/n | See D7 below. |
| D8 | Deflection limit | δ_lim | 50 mm | L/400 = 20 000 mm / 400 |
| D9 | Yield strength | f_y | 355 MPa | See D9 below **[Q12]**. |
| D10 | Loads included | | crowd load only | "ignore self-weight in this first version" **[Q6]** |
| D11 | Truss types | | Pratt, Howe, Warren | Stated directly. |
| D12 | Objective | | minimum steel mass | "lightest design" **[Q20]** |

**D5: load on one truss.** The two trusses are identical and placed
symmetrically, one on each side of the deck. With the crowd load over the full
deck width, the resultant q·b acts on the deck centreline, so by symmetry each
truss carries half of it:

  w = q·b/2 = 4 · 2.5 / 2 = 5 kN/m.

A crowd on only one half of the width gives less load on the near truss. With
the deck spanning simply supported between the trusses, the resultant
q·b/2 acts at b/4 from the near truss. That truss then takes
q·(b/2)·(3/4) = 3·q·b/8 = 3.75 kN/m < 5 kN/m. Full-width loading therefore
governs for one truss.

**D7: nodal loads.** This assumes the deck load reaches the truss through
cross beams at every loaded chord node, with the deck simply supported
between them **[Q3, Q4]**. With panel length Δ = L/n, each node takes the load
from its tributary length:

- interior node: P = w·Δ = w·L/n
- end node (over a support): P_end = w·Δ/2 = w·L/(2n)

Check: (n − 1)·P + 2·P_end = w·L·(n − 1)/n + w·L/n = w·L = W. ✓

| n | Δ [m] | P [kN] | P_end [kN] |
|---|---|---|---|
| 2 | 10.0 | 50.0 | 25.0 |
| 4 | 5.0 | 25.0 | 12.5 |
| 6 | 3.333 | 16.667 | 8.333 |
| 8 | 2.5 | 12.5 | 6.25 |

The end-node loads act directly on the supports. They change the reactions
but not the member forces or the displacements. Whether they are applied is
**[Q4]**. Support reaction from the interior loads only:
R = P·(n − 1)/2. With the end loads included: R = W/2 = 50 kN.

**D9: yield strength.** The grade name S355 gives the nominal yield strength
in MPa. EN 1993-1-1 Table 3.1 gives f_y = 355 MPa for t ≤ 40 mm and
335 MPa for 40 < t ≤ 80 mm (EN 10025-2), or 40 < t ≤ 65 mm for hollow sections
to EN 10210-1. The value therefore depends on the wall thickness of the
chosen sections **[Q12, Q14]**.

---

## 3. Structural model

### 3.1 Geometry parameters

| Parameter | Symbol | Value |
|---|---|---|
| Span | L | 20 m (D1) |
| Truss height (centreline of top chord to centreline of bottom chord) | h | design variable, range **[Q10]** |
| Number of panels | n | design variable, range **[Q9]** |
| Panel length | Δ | L/n |

Proposed: n must be even, so that there is a bottom-chord node at midspan for
the deflection check and the truss is symmetric **[Q9]**.

### 3.2 Topology (*proposed*, **[Q7, Q8]**)

Bottom-chord nodes B_i are at (i·Δ, 0) for i = 0 … n in every type.

**Pratt and Howe** (inclined end posts, no top node over the supports):

- Top nodes T_i at (i·Δ, h), i = 1 … n − 1
- Bottom chord: B_i–B_{i+1}, i = 0 … n − 1 (n members)
- Top chord: T_i–T_{i+1}, i = 1 … n − 2 (n − 2 members)
- Verticals: B_i–T_i, i = 1 … n − 1 (n − 1 members)
- End posts: B_0–T_1 and B_n–T_{n−1} (2 members)
- Diagonals in the interior panels i = 1 … n − 2 (the panel between x_i and
  x_{i+1}), n − 2 members:
  - Pratt: the lower end points towards midspan. Left half: T_i–B_{i+1}.
    Right half: B_i–T_{i+1}. Under gravity load the diagonals are in tension.
  - Howe: the lower end points towards the supports. Left half:
    B_i–T_{i+1}. Right half: T_i–B_{i+1}. Under gravity load the diagonals
    are in compression.
- Totals: nodes j = 2n, members m = 4n − 3.
- For n = 2 Pratt and Howe are identical (no interior diagonals).

**Warren** (no verticals, top nodes over the panel midpoints):

- Top nodes T_i at ((i + ½)·Δ, h), i = 0 … n − 1
- Bottom chord: B_i–B_{i+1}, i = 0 … n − 1 (n members)
- Top chord: T_i–T_{i+1}, i = 0 … n − 2 (n − 1 members)
- Diagonals: B_i–T_i and T_i–B_{i+1}, i = 0 … n − 1 (2n members)
- Totals: nodes j = 2n + 1, members m = 4n − 1.

**Statical determinacy.** With r = 3 support reactions, m + r = 2j holds for
both families: (4n − 3) + 3 = 2·2n, and (4n − 1) + 3 = 2·(2n + 1). Member
forces are therefore independent of E and A.

### 3.3 Numbering (*proposed*)

- Nodes, 1-based as CALFEM's `edof` requires: bottom nodes B_0 … B_n first,
  left to right, then top nodes left to right.
- Node k has DOFs 2k − 1 (x) and 2k (y).
- Elements in group order: bottom chord, top chord, verticals, end posts,
  diagonals. Each element carries a group label.

### 3.4 Supports (**[Q2]**, *proposed*)

Simply supported at the bottom-chord end nodes:

- B_0 (node 1): pinned, u_x = u_y = 0, so DOFs 1 and 2 are fixed.
- B_n (node n + 1): roller, u_y = 0, so DOF 2(n + 1) is fixed.

### 3.5 Load vector

- Loads act downwards at the deck-level chord nodes **[Q3]**:
  f[2k] = −P at each interior loaded node, and −P_end at the end nodes if
  they are included **[Q4]**.
- Only the full-span uniform load case is used, unless pattern loading is
  required **[Q5]**.

---

## 4. Material and section properties

| Property | Symbol | Value | Source |
|---|---|---|---|
| Young's modulus | E | **[Q11]** | not in the text |
| Yield strength | f_y | 355 MPa (t ≤ 40 mm) | D9, **[Q12]** |
| Density | ρ | **[Q13]** | not in the text, needed for mass |
| Section list | A, I, t, (mass/m) | **[Q14]** | not in the text |
| Section assignment per member group | | **[Q15]** | not in the text |

A section entry needs at least: name, area A, second moment of area I for
in-plane buckling (and out-of-plane if relevant, **[Q18]**), wall thickness t
(for f_y), and mass per metre or ρ.

---

## 5. Units and sign conventions (*proposed*)

- **Units:** SI throughout the model: N, m, Pa, kg. Input and report values
  may be given in kN, mm, MPa, cm² or cm⁴, but are converted at the boundary.
- **Global axes:** x along the span from the left support (B_0), y vertically
  upwards.
- **Loads:** gravity loads are negative in y.
- **Displacements:** u_y < 0 means downwards. The deflection check uses |u_y|.
- **Normal force:** N > 0 is tension and N < 0 is compression. This is the
  CALFEM `bar2s` convention.
- **Reactions:** positive in the positive global axis directions.

---

## 6. Implementation and required outputs

### 6.1 CALFEM procedure

1. Element stiffness: `bar2e(ex, ey, [E, A])` for each member.
2. Assembly: `assem(edof_row, K, Ke)`.
3. Solve: `a, r = solveq(K, f, bc)`, with `bc` from section 3.4.
4. Element displacements: `ed = extract_eldisp(edof, a)`.
5. Normal forces: `bar2s(ex, ey, [E, A], ed_row)` for each member.

### 6.2 Outputs of the model, per analysis

- node coordinates, element connectivity, `edof`, constrained DOFs
- member group labels and member lengths ℓ_e
- displacement vector a (m) and reaction vector r (N)
- normal force N_e for each member (N)
- midspan vertical displacement u_y at B_{n/2} (m)

### 6.3 Outputs of the design checks, per design

- P (and P_end) used
- for each member: stress utilisation, plus buckling utilisation if N_e < 0
- deflection utilisation
- governing member and the governing check
- pass/fail for each check, and overall
- steel mass of the truss **[Q20]**

### 6.4 Outputs of the design search

A table of all combinations (type, h, n, sections) that pass, sorted by mass
in ascending order, with the lightest design identified. Each row shows its
maximum utilisations.

---

## 7. Design checks

The problem asks for three checks. The open items are which load level,
which partial factors and which buckling model to use **[Q16, Q17, Q18,
Q19]**.

N_Ed = γ_Q · N_e, where N_e is the member force from the characteristic load
P and γ_Q is **[Q16]**.

**C1. No member may yield (tension and compression)**

  U_y,e = |N_Ed| / (A · f_y / γ_M0) ≤ 1,  γ_M0 = **[Q16]**

**C2. No compression member may buckle (only members with N_e < 0)**

  U_b,e = |N_Ed| / N_b,Rd ≤ 1

with N_b,Rd either:

- (a) Euler: N_cr = π²·E·I / L_cr², optionally divided by a factor, or
- (b) EN 1993-1-1 6.3.1: χ·A·f_y / γ_M1, where χ comes from the buckling
  curve for the section type.

The choice of model **[Q17]** and the buckling length L_cr, both in-plane and
out-of-plane **[Q18]**, are open.

**C3. Midspan deflection**

  U_δ = |u_y(B_{n/2})| / (L/400) ≤ 1,  with L/400 = 50 mm (D8)

This uses the characteristic (unfactored) crowd load **[Q19]**.

**Pass:** a design passes when max(U_y,e, U_b,e, U_δ) ≤ 1.

**Objective:** mass = ρ · Σ A_e · ℓ_e for one truss **[Q20]**.

---

## 8. Verification criteria

The model is accepted when it shows all of the following:

1. **Counts:** j and m as in section 3.2, and 3 constrained DOFs, for
   n = 2, 4, 6, 8.
2. **Determinacy:** m + r = 2j. Scaling E or A changes no normal force and
   scales the displacements by the inverse factor.
3. **Equilibrium:** Σ R_y equals the sum of the applied loads, and
   Σ R_x = 0, to machine precision.
4. **Symmetry:** members in mirrored positions carry equal forces under the
   symmetric load.
5. **Linearity:** doubling P doubles all forces and displacements.
6. **Hand-calculation reference** (to be checked independently before use):
   Pratt, L = 20 m, h = 3 m, n = 4, P = 25 kN at the interior bottom nodes
   only. Here R = 37.5 kN and M(L/2) = P·n·L/8 = 250 kNm.

   | Member | Hand formula | N [kN] |
   |---|---|---|
   | Top chord (both members) | −M(L/2)/h | −83.333 |
   | Bottom chord, panels 1 and 2 | M(Δ)/h = R·Δ/h | +62.5 |
   | End post B_0–T_1 | −R·√(Δ² + h²)/h | −72.887 |
   | Diagonal T_1–B_2 | (R − P)·√(Δ² + h²)/h | +24.296 |
   | Vertical B_1–T_1 | +P | +25.0 |
   | Vertical B_2–T_2 (midspan) | 0 | 0 |

---

## 9. Open questions

Each one must be answered before implementation. The answers are written
into the sections above, and this list is then removed.

**Geometry and supports**

- **Q1 Span.** Is L = 20 m the distance between the support centrelines,
  equal to the stream width? Or is it longer, to allow for bearing seats
  on the banks?
- **Q2 Supports.** Simply supported, with a pin at one end and a roller at
  the other, both at the bottom-chord end nodes?
- **Q3 Deck level.** Is the deck at the bottom chord (through or pony
  truss, loads at the bottom nodes), or on the top chord (deck truss, loads
  at the top nodes)?
- **Q7 Pratt and Howe topology.** Inclined end posts (no top node over the
  supports), as proposed in 3.2? Or vertical end posts with a top node over
  each support? Is the diagonal orientation in 3.2 what you mean by Pratt
  and Howe?
- **Q8 Warren topology.** Without verticals, with the top nodes over the
  panel midpoints, as proposed? Or a Warren with verticals?
- **Q9 Panel count.** Is n a design variable? Over what range? Must it be
  even?
- **Q10 Height.** What range and step of h should be searched? Are there
  limits from clearance, parapet height or headroom (for overhead bracing)?

**Loads**

- **Q4 Load transfer.** Cross beams at every deck-level node, with tributary
  length Δ? Should the end-node loads w·Δ/2 be applied, or omitted because
  they go straight into the supports?
- **Q5 Load arrangements.** Only the full-span uniform crowd load? Or also
  partial-span patterns, which can govern the web members?
- **Q6 Self-weight.** Does "ignore self-weight" exclude the deck, cross
  beams and parapets as well as the truss itself?

**Material and sections**

- **Q11 Young's modulus.** E = ? (The text doesn't give it.)
- **Q12 Yield strength.** f_y = 355 MPa, assuming all wall thicknesses are
  ≤ 40 mm? Or should the thickness-dependent value be used?
- **Q13 Density.** ρ = ?
- **Q14 Section list.** Which sections are available? I need A, I (in-plane
  and out-of-plane if they differ), t and mass per metre, from a table you
  trust. Which section type (for example square hollow sections)?
- **Q15 Section assignment.** One section for all members? Or one for the
  chords and one for the web? Do the Pratt and Howe end posts belong to the
  chords or the web?

**Design checks**

- **Q16 Safety factors.** Should yield and buckling use the characteristic
  load ("no member may yield" taken literally), or a factored ULS load? If
  factored, what are γ_Q, γ_M0 and γ_M1?
- **Q17 Buckling model.** Elastic Euler buckling N_cr = π²EI/L_cr², or
  EN 1993-1-1 flexural buckling with a reduction factor χ? If Euler, is
  there any extra factor? If EC3, which buckling curve?
- **Q18 Buckling length.** In-plane L_cr equal to the member system length
  (pinned-pinned)? Out of plane: is the compression chord laterally
  restrained at every node? If not, how should out-of-plane buckling of the
  top chord be handled? It is often critical in a pony truss, and a 2D model
  cannot capture it by itself.
- **Q19 Deflection.** Under the characteristic crowd load, at the midspan
  bottom-chord node, total deflection with no precamber?
- **Q20 Objective.** Mass of one truss (ranking is the same as for both)?
  Truss members only, with no allowance for connections? How should ties be
  broken?
- **Q21 Exclusions.** Do you confirm that the items listed as out of scope
  in section 1 are excluded from this version? These include vibration
  comfort, which often governs light footbridges of this span.
- **Q22 Conventions.** Do you accept the units, axes, sign conventions and
  numbering proposed in 3.3 and 5?
