# Footbridge truss: specification

Status: **Revision 7, complete.** All questions are answered, and section 10
records where each answer went. Revision 7 resolves the implementation review
(items R1–R13, section 10). There are no open items. Any later change to this
specification is made here first, before the code changes.

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

Out of scope for this version (Q21): connections, fatigue, vibration and
pedestrian comfort, wind and other lateral loads, deck and cross-beam design,
and bracing design.

---

## 2. Values derived from the text

| ID | Quantity | Symbol | Value | Derivation |
|---|---|---|---|---|
| D1 | Span | L | 20 m | "cross a 20 m wide stream". L is the distance between support centrelines and equals the stream width (Q1). |
| D2 | Deck width | b | 2.5 m | Stated directly. |
| D3 | Crowd load (area) | q | 4 kN/m² | Stated directly. Characteristic value. |
| D4 | Deck load per metre of bridge | q·b | 10 kN/m | 4 kN/m² · 2.5 m = 10 kN/m |
| D5 | Line load on one truss | w | 5 kN/m | See D5 below. |
| D6 | Total load on one truss | W | 100 kN | w·L = 5 kN/m · 20 m |
| D7 | Nodal loads | P, P_end | w·L/n, w·L/(2n) | See D7 below. |
| D8 | Deflection limit | δ_lim | 50 mm | L/400 = 20 000 mm / 400 |
| D9 | Yield strength | f_y | 355 MPa (t ≤ 40 mm) | See D9 below. |
| D10 | Loads included | | crowd load only | "ignore self-weight in this first version". This excludes the deck, cross beams, parapets and the truss itself (Q6). |
| D11 | Truss types | | Pratt, Howe, Warren | Stated directly. |
| D12 | Objective | | minimum steel mass of one truss | "lightest design" (Q20) |

**D5: load on one truss.** The two trusses are identical and placed
symmetrically, one on each side of the deck. With the crowd load over the full
deck width, the resultant q·b acts on the deck centreline, so by symmetry each
truss carries half of it:

  w = q·b/2 = 4 · 2.5 / 2 = 5 kN/m.

A crowd on only one half of the width gives less load on the near truss. With
the deck spanning simply supported between the trusses, the resultant
q·b/2 acts at b/4 from the near truss. That truss then takes
q·(b/2)·(3/4) = 3·q·b/8 = 3.75 kN/m < 5 kN/m. Full-width loading therefore
governs across the width. Along the span, partial loading is considered
(section 3.5).

**D7: nodal loads.** The deck load reaches the truss through cross beams at
every bottom-chord node, with the deck simply supported between them (Q3,
Q4). With panel length Δ = L/n, each node takes the load from its tributary
length:

- interior node B_1 … B_{n−1}: P = w·Δ = w·L/n
- end node B_0, B_n: P_end = w·Δ/2 = w·L/(2n), applied (Q4)

Check: (n − 1)·P + 2·P_end = w·L·(n − 1)/n + w·L/n = w·L = W. ✓

| n | Δ [m] | P [kN] | P_end [kN] |
|---|---|---|---|
| 2 | 10.0 | 50.0 | 25.0 |
| 4 | 5.0 | 25.0 | 12.5 |
| 6 | 3.333 | 16.667 | 8.333 |
| 8 | 2.5 | 12.5 | 6.25 |
| 10 | 2.0 | 10.0 | 5.0 |

The end-node loads act on supported DOFs. They change the reactions but not
the member forces or the displacements. Under full-span load each reaction is
R = W/2 = 50 kN, of which P·(n − 1)/2 comes from the interior loads and P_end
from the end node itself.

**D9: yield strength.** The grade name S355 gives the nominal yield strength
in MPa. EN 1993-1-1 Table 3.1 gives:

| Wall/flange thickness t | f_y |
|---|---|
| t ≤ 40 mm | 355 MPa |
| 40 < t ≤ 80 mm (EN 10025-2), 40 < t ≤ 65 mm (hollow, EN 10210-1) | 335 MPa |

f_y is taken from this table for each section's thickness t (Q12).

---

## 3. Structural model

### 3.1 Geometry parameters

| Parameter | Symbol | Value |
|---|---|---|
| Span | L | 20 m (D1) |
| Truss height (centreline of top chord to centreline of bottom chord) | h | design variable: 3.0, 3.5, …, 6.0 m (7 values, Q10) |
| Number of panels | n | design variable: {4, 6, 8, 10} (Q9) |
| Panel length | Δ | L/n: 5.0, 3.333, 2.5, 2.0 m |

n must be even, so that the truss is symmetric and has a bottom-chord node
B_{n/2} at midspan for the deflection check (Q9).

### 3.2 Topology (Q7, Q8)

Bottom-chord nodes B_i are at (i·Δ, 0) for i = 0 … n in every type.

**Pratt and Howe** (inclined end posts, no top node over the supports):

- Top nodes T_i at (i·Δ, h), i = 1 … n − 1
- Bottom chord: B_i–B_{i+1}, i = 0 … n − 1 (n members)
- Top chord: T_i–T_{i+1}, i = 1 … n − 2 (n − 2 members)
- Verticals: B_i–T_i, i = 1 … n − 1 (n − 1 members)
- End posts: B_0–T_1 and B_n–T_{n−1} (2 members)
- Diagonals in the interior panels i = 1 … n − 2 (the panel between x_i and
  x_{i+1}), n − 2 members. Left half: panels i ≤ n/2 − 1. Right half: panels
  i ≥ n/2. Panel i is the panel between B_i and B_{i+1} (0-based, as in 3.5).
  - Pratt: the lower end points towards midspan. Left half: T_i–B_{i+1}.
    Right half: B_i–T_{i+1}. Under full-span gravity load the diagonals are
    in tension.
  - Howe: the lower end points towards the supports. Left half:
    B_i–T_{i+1}. Right half: T_i–B_{i+1}. Under full-span gravity load the
    diagonals are in compression.
- Totals: nodes j = 2n, members m = 4n − 3.
- For n = 2 Pratt and Howe are identical (no interior diagonals).

**Warren** (no verticals, top nodes over the panel midpoints):

- Top nodes T_i at ((i + ½)·Δ, h), i = 0 … n − 1
- Bottom chord: B_i–B_{i+1}, i = 0 … n − 1 (n members)
- Top chord: T_i–T_{i+1}, i = 0 … n − 2 (n − 1 members)
- Diagonals: B_i–T_i and T_i–B_{i+1}, i = 0 … n − 1 (2n members)
- The end diagonals B_0–T_0 and T_{n−1}–B_n are ordinary diagonals: group
  "diagonal", web class (R2). Warren has no verticals and no end posts.
- Totals: nodes j = 2n + 1, members m = 4n − 1.

**Statical determinacy.** With r = 3 support reactions, m + r = 2j holds for
both families: (4n − 3) + 3 = 2·2n, and (4n − 1) + 3 = 2·(2n + 1). Member
forces are therefore independent of E and A.

### 3.3 Numbering and member groups (Q22)

- Nodes, 1-based as CALFEM's `edof` requires: bottom nodes B_0 … B_n first,
  left to right, then top nodes left to right.
- Node k has DOFs 2k − 1 (x) and 2k (y).
- Elements in group order: bottom chord, top chord, verticals, end posts,
  diagonals. Each element carries a group label.
- Section classes (Q15, R1, R2): **chord** = bottom chord, top chord and end
  posts (Pratt/Howe only), which all share one section S_c with area A_c.
  **Web** = verticals and diagonals, including Warren's end diagonals, which
  all share one section S_w with area A_w. S_c and S_w are independent design
  variables, each searched over the whole section list. The model takes A_c
  and A_w as inputs and gives each member the area of its class.

### 3.4 Supports (Q2)

Simply supported at the bottom-chord end nodes:

- B_0 (node 1): pinned, u_x = u_y = 0, so DOFs 1 and 2 are fixed.
- B_n (node n + 1): roller, u_y = 0, so DOF 2(n + 1) is fixed.

### 3.5 Loads and load cases (Q3, Q4, Q5)

All loads act downwards at bottom-chord nodes. DOF 2k (1-based, as in 3.3)
of node k receives −(nodal load). In 0-based Python arrays this is index
2k − 1 (R5).

The model takes the line load w [N/m] as input. It computes Δ, P and P_end
and builds LC-full and LC-0 … LC-(n−1) itself (R3).

A load case is defined by its set of **loaded panels**. Panel i lies between
B_i and B_{i+1}, for i = 0 … n − 1. Each loaded panel puts w·Δ/2 on each of
its two end nodes (tributary loading, Q4). A node therefore receives:

- interior node: 0, w·Δ/2 or w·Δ = P, depending on how many of its two
  adjacent panels are loaded;
- support node: P_end = w·Δ/2 if its adjacent end panel is loaded, otherwise
  0 (Q5a).

Load cases:

- **LC-full:** all panels loaded. This gives −P at B_1 … B_{n−1} and −P_end
  at B_0 and B_n.
- **LC-i (single panel), i = 0 … n − 1:** only panel i is loaded, with
  −w·Δ/2 at B_i and at B_{i+1}. That is n load cases.
- **Partial-span patterns:** the full envelope (Q5a). Any set of panels may
  be loaded, independently of the others.

Because the model is linear, the worst result over all 2ⁿ panel sets follows
from the n single-panel cases. With N_e,i the force in member e under LC-i:

  N_max,e = Σ_i max(N_e,i, 0)  (largest tension; 0 if the member is never in tension)
  N_min,e = Σ_i min(N_e,i, 0)  (largest compression; 0 if never in compression)

By superposition, LC-full = Σ_i LC-i, so LC-full is included in the
envelope.

N_max,e and N_min,e are used in checks C1 and C2. The deflection check C3
uses LC-full only (Q5b).

### 3.6 Zero-force tolerance (R8)

N_tol = 10⁻⁹ · W, where W = w·L. A force with |N| < N_tol is treated as zero
in the envelope, in the checks and in reports. A member is a compression
member for C2 when N_min,e < −N_tol.

---

## 4. Material and section properties

| Property | Symbol | Value | Source |
|---|---|---|---|
| Young's modulus | E | 210 GPa | Q11 |
| Yield strength | f_y | from t, D9 table | Q12 |
| Density | ρ | 7850 kg/m³ | Q13 |
| Section types | | SHS and I-sections, in one combined list | Q14 |
| Section list | name, A, I_y, I_z, t | 24 sections, see 4.1 | Q14, approved |
| Section assignment | S_c (chords, end posts), S_w (web) | independent | Q15, 3.3 |

S_c and S_w each choose from the whole combined list, so a design may mix
an SHS and an I-section. Each section entry gives: name, area A, second moment of area about both
axes, I_y (strong axis) and I_z (weak axis), and thickness t. C2 uses
min(I_y, I_z), so it doesn't matter how the section is oriented in the
truss plane (R13). For an SHS,
I_y = I_z. Mass is computed as ρ·A·ℓ (section 7), so the tabulated mass per
metre is used only as a cross-check.

### 4.1 Section list (Q14, approved)

**Sources:**

- SHS: hot-finished square hollow sections to EN 10210-2, nominal corner
  radii. Values from Eurocode Applied, "Design properties of hot finished
  SHS",
  <https://cdn.eurocodeapplied.com/design/en1993/shs-design-properties>.
  A and I are geometric properties, so they apply to S355 even though that
  page is labelled S235.
- IPE: European I-sections (EN 10365, formerly Euronorm 19-57). Values from
  Stad, "Technical data, IPE",
  <https://www.stad.fr/en/sections-products-ranges-ipe>.

**Cross-checks done:**

- ρ·A reproduces the tabulated mass per metre for every row checked:
  SHS 60/4, 100/5 and 200/10, and IPE 100, 200 and 300.
- The values agree with the Tata Steel Blue Book (SHS) and with the
  ArcelorMittal tables (IPE) as known to the AI.
- **Recomputed from dimensions.** A and I were computed independently from
  each section's geometry: the SHS with outer and inner corner radii
  r_o = 1.5t and r_i = t (EN 10210-2), and the IPE from h, b, t_w, t_f and
  the root radius r. All A, all SHS I and all IPE I_y agree with the table
  within 0.1 %. IPE I_z agrees within 1.2 %, and the largest differences
  occur where the table rounds I_z to whole cm⁴ (IPE 100: 15.9 vs 16; IPE 120:
  27.7 vs 28). The table values are used as given. This check confirms that
  the properties are consistent with the dimensions. It does not confirm
  that the dimensions themselves are correct.
- The engineer approved the list as is for this first version (Q14).

**Units:** A in cm², I in cm⁴, t in mm. Convert to SI at input:
1 cm² = 10⁻⁴ m², 1 cm⁴ = 10⁻⁸ m⁴.

**Thickness for f_y:** for an SHS, t is the wall thickness. For an IPE, t is
the flange thickness t_f, which is the larger of t_f and t_w for every IPE
listed. All t ≤ 40 mm, so f_y = 355 MPa for every section (D9).

**Orientation of IPE sections:** I_y is the strong axis. The C2 buckling
check uses min(I_y, I_z) = I_z, so the orientation does not affect the
checks.

| # | Name | A [cm²] | I_y [cm⁴] | I_z [cm⁴] | t [mm] | mass [kg/m] |
|---|---|---|---|---|---|---|
| 1 | SHS 60×4 | 8.79 | 45.39 | 45.39 | 4.0 | 6.90 |
| 2 | SHS 80×4 | 11.99 | 114.5 | 114.5 | 4.0 | 9.41 |
| 3 | SHS 80×5 | 14.73 | 136.6 | 136.6 | 5.0 | 11.6 |
| 4 | SHS 100×4 | 15.19 | 231.8 | 231.8 | 4.0 | 11.9 |
| 5 | SHS 100×5 | 18.73 | 279.4 | 279.4 | 5.0 | 14.7 |
| 6 | SHS 100×6.3 | 23.19 | 335.6 | 335.6 | 6.3 | 18.2 |
| 7 | SHS 120×5 | 22.73 | 497.7 | 497.7 | 5.0 | 17.8 |
| 8 | SHS 120×6.3 | 28.23 | 602.9 | 602.9 | 6.3 | 22.2 |
| 9 | SHS 140×6.3 | 33.27 | 983.9 | 983.9 | 6.3 | 26.1 |
| 10 | SHS 150×6.3 | 35.79 | 1223 | 1223 | 6.3 | 28.1 |
| 11 | SHS 150×8 | 44.75 | 1491 | 1491 | 8.0 | 35.1 |
| 12 | SHS 160×8 | 47.95 | 1831 | 1831 | 8.0 | 37.6 |
| 13 | SHS 200×8 | 60.75 | 3709 | 3709 | 8.0 | 47.7 |
| 14 | SHS 200×10 | 74.93 | 4471 | 4471 | 10.0 | 58.8 |
| 15 | IPE 100 | 10.32 | 171 | 16 | 5.7 | 8.1 |
| 16 | IPE 120 | 13.21 | 318 | 28 | 6.3 | 10.4 |
| 17 | IPE 140 | 16.43 | 541 | 45 | 6.9 | 12.9 |
| 18 | IPE 160 | 20.09 | 869 | 68 | 7.4 | 15.8 |
| 19 | IPE 180 | 23.95 | 1317 | 101 | 8.0 | 18.8 |
| 20 | IPE 200 | 28.48 | 1943 | 142 | 8.5 | 22.4 |
| 21 | IPE 220 | 33.37 | 2772 | 205 | 9.2 | 26.2 |
| 22 | IPE 240 | 39.12 | 3892 | 284 | 9.8 | 30.7 |
| 23 | IPE 270 | 45.95 | 5790 | 420 | 10.2 | 36.1 |
| 24 | IPE 300 | 53.81 | 8356 | 604 | 10.7 | 42.2 |

**Search size:** N_s = 24, so 84·24² = 48 384 designs. Because the truss is
statically determinate, the member forces and their envelope depend only on
the geometry (type, n, h), not on the sections (section 3.2). Only the
deflection depends on the sections.

**Range check:** for Pratt with n = 4 and h = 3 m, the top chord carries
83.3 kN over 5 m. Euler then needs
I ≥ N·ℓ²/(π²·E) = 83.3·10³ · 5² / (π² · 210·10⁹) = 1.0·10⁻⁶ m⁴ = 100 cm⁴.
The list covers this from both sides: some sections fail (for example
SHS 60×4, and IPE 160 about z), and some pass.

---

## 5. Units and sign conventions (Q22)

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

1. Element stiffness: `bar2e(ex, ey, [E, A_e])` for each member, where A_e
   is A_c or A_w by class (R1).
2. Assembly: `assem(edof_row, K, Ke)`.
3. Solve for each load case: `a, r = solveq(K, f, bc)`, with `bc` from
   section 3.4. `bc` is a numpy integer array of 1-based DOFs. `solveq`
   returns r = K·a − f. At support DOFs, r is the support reaction, including
   any load applied at that DOF. At free DOFs, r ≈ 0 (R10).
4. Element displacements: `ed = extract_eldisp(edof, a)`.
5. Normal forces: `es = bar2s(ex, ey, [E, A_e], ed_row)` for each member.
   `es` has shape (2, 1) and holds N at both member ends. The two values are
   equal for a bar with no distributed load, and N_e is taken as the first
   value, `es[0, 0]` (R6).

### 6.2 Model interface and outputs, per analysis

Model inputs (R1, R3): truss type, L, h and n (geometry), and E, A_c, A_w and
w (analysis).

Outputs:

- node coordinates, element connectivity, `edof`, constrained DOFs
- member group labels, section class (chord or web) and member lengths ℓ_e
- for each load case: displacement vector a (m), reaction vector r (N),
  normal force N_e for each member (N)
- midspan vertical displacement u_y at B_{n/2} (m)
- the envelope N_max,e and N_min,e for each member (3.5, 3.6). The model
  computes it (R3).

### 6.3 Outputs of the design checks, per design

- P and P_end used
- envelope N_max,e and N_min,e for each member, taken from the model
- for each member: stress utilisation, plus buckling utilisation if
  N_min,e < 0
- deflection utilisation
- governing member and the governing check
- pass/fail for each check, and overall
- steel mass of one truss

### 6.4 Outputs of the design search

The search space is every combination of:

- type ∈ {Pratt, Howe, Warren}
- n ∈ {4, 6, 8, 10}
- h ∈ {3.0, 3.5, …, 6.0} m
- S_c and S_w from the section list

That is 3 · 4 · 7 · N_s² = 84·N_s² designs, where N_s is the number of
sections.

The output is a table of all passing designs, sorted by mass M in ascending
order (R7):

- Two masses count as equal when |M₁ − M₂| ≤ 10⁻⁹ · max(M₁, M₂).
- Equal-mass designs are ordered by the lower maximum utilisation U_max. This
  is the largest U_y,e, U_b,e or U_δ over all members.
- Remaining ties are ordered by type: Pratt, Howe, Warren.

The first row is the lightest design. Each row shows its maximum utilisation
for each check (C1, C2, C3).

If no design passes, the pass table is empty. The search then reports the
design with the lowest U_max, its governing member and its governing check
(R9).

---

## 7. Design checks

All checks use the characteristic crowd load. No partial factors are
applied: γ_Q = γ_M0 = γ_M1 = 1 (Q16). "No member may yield" is taken
literally.

**C1. No member may yield (tension and compression)**

  U_y,e = max(|N_max,e|, |N_min,e|) / (A_e · f_y(t_e)) ≤ 1

**C2. No compression member may buckle (only members with N_min,e < 0)**

Elastic Euler buckling with no reduction factor (Q17):

  N_cr,e = π² · E · I_e / L_cr,e²,  U_b,e = |N_min,e| / N_cr,e ≤ 1

Buckling lengths (Q18):

- In-plane: L_cr = ℓ_e (pinned-pinned).
- Out-of-plane: the top chord is laterally restrained at every node, so
  L_cr = ℓ_e as well.

- Out-of-plane, web members and end posts: L_cr = ℓ_e (Q18a).

Because both lengths are ℓ_e for every member, the governing value is
I_e = min(I_y, I_z). For an SHS I_y = I_z. For an I-section the weak axis
governs, whichever way the section is oriented.

Note: Euler buckling without imperfections overestimates the capacity of
members with intermediate slenderness. C1 still limits stocky members to
A·f_y. This is accepted for this first version (Q17).

**C3. Midspan deflection**

  U_δ = |u_y(B_{n/2})| / (L/400) ≤ 1,  with L/400 = 50 mm (D8)

This is the total deflection at the midspan bottom-chord node under the
characteristic crowd load, LC-full only (Q5b), with no precamber (Q19).

**Pass:** a design passes when every U_y,e, U_b,e and U_δ is ≤ 1.

**Objective:** mass of one truss, members only, no allowance for connections
(Q20):

  M = ρ · Σ_e A_e · ℓ_e

---

## 8. Verification criteria

The model is accepted when it shows all of the following:

1. **Counts:** j and m as in section 3.2, and 3 constrained DOFs, for
   n = 2, 4, 6, 8, 10 (R11).
2. **Determinacy:** m + r = 2j. Scaling E, or A_c and A_w together, changes
   no normal force and scales the displacements by the inverse factor.
   Scaling only A_c or only A_w also changes no normal force (R1).
3. **Equilibrium:** Σ R_y + Σ f_y = 0 and Σ R_x = 0, to machine precision,
   with the loads including P_end. Under LC-full, Σ R_y = +W (R10).
4. **Symmetry:** members in mirrored positions carry equal forces under
   LC-full.
5. **Linearity:** doubling w doubles all forces and displacements (R3).
6. **Superposition:** the sum of the single-panel load cases LC-0 … LC-(n−1)
   equals LC-full. The LC-full forces lie within the envelope
   [N_min,e, N_max,e]. For a member whose single-panel forces all have the
   same sign, the envelope equals its LC-full force.
7. **Hand-calculation reference** (verified by the engineer, R12):
   Pratt, L = 20 m, h = 3 m, n = 4, w = 5 kN/m, giving P = 25 kN and
   P_end = 12.5 kN (LC-full). Each support reaction is 50 kN: 37.5 kN from the
   interior loads (R in the formulas below) plus P_end. The midspan moment is
   M(L/2) = P·n·L/8 = 250 kNm. P_end acts on supported DOFs, so it does not
   affect the member forces.

   | Member | Hand formula | N [kN] |
   |---|---|---|
   | Top chord (both members) | −M(L/2)/h | −83.333 |
   | Bottom chord, all four members (panels 0–3) | R·Δ/h, R = 37.5 kN | +62.5 |
   | End post B_0–T_1 | −R·√(Δ² + h²)/h | −72.887 |
   | Diagonal T_1–B_2 | (R − P)·√(Δ² + h²)/h | +24.296 |
   | Vertical B_1–T_1 | +P | +25.0 |
   | Vertical B_2–T_2 (midspan) | 0 | 0 |

---

## 9. Open questions

None.

---

## 10. Decision log

| Q | Decision | Where |
|---|---|---|
| Q1 | L = 20 m between support centrelines | D1, 3.1 |
| Q2 | Pin at B_0, roller at B_n | 3.4 |
| Q3 | Deck at bottom chord, loads at bottom nodes | D7, 3.5 |
| Q4 | Cross beams at every node, tributary Δ, P_end applied | D7, 3.5 |
| Q5 | Full-span and critical partial-span patterns | 3.5 |
| Q5a | Full envelope from n single-panel cases; P_end applied at a support when its adjacent panel is loaded | 3.5 |
| Q5b | Deflection checked under LC-full only | 3.5, 7 C3 |
| Q6 | All self-weight ignored | D10 |
| Q7 | Pratt and Howe with inclined end posts, diagonals as in 3.2 | 3.2 |
| Q8 | Warren without verticals | 3.2 |
| Q9 | n ∈ {4, 6, 8, 10} | 3.1, 6.4 |
| Q10 | h = 3.0 … 6.0 m, step 0.5 m | 3.1, 6.4 |
| Q11 | E = 210 GPa | 4 |
| Q12 | f_y by thickness, EN 1993-1-1 Table 3.1 | D9 |
| Q13 | ρ = 7850 kg/m³ | 4 |
| Q14 | SHS and I-sections in one combined list; 24 sections retrieved by the AI, checked against their dimensions, approved as is | 4.1 |
| Q15 | Independent S_c (top chord, bottom chord, end posts) and S_w (web) | 3.3, 4, 6.4 |
| Q16 | Characteristic load, no partial factors | 7 |
| Q17 | Euler buckling, no reduction factor | 7 C2 |
| Q18 | In-plane L_cr = ℓ_e, top chord restrained at every node | 7 C2 |
| Q18a | Out-of-plane L_cr = ℓ_e for web members and end posts, I = min(I_y, I_z) | 7 C2 |
| Q19 | Total midspan deflection, characteristic load, no precamber | 7 C3 |
| Q20 | Mass of one truss, members only, ties go to the lower maximum utilisation | 6.4, 7 |
| Q21 | Out-of-scope list confirmed | 1 |
| Q22 | Units, axes, signs and numbering accepted | 3.3, 5 |

### Implementation review (Revision 7)

| R | Issue | Decision | Where |
|---|---|---|---|
| R1 | Area input with two section classes | Model takes A_c and A_w, assigned by class | 3.3, 6.1, 6.2, 8.2 |
| R2 | Class of Warren end diagonals | Web class, group "diagonal" | 3.2, 3.3 |
| R3 | Load input and load cases | Model takes w and builds LC-full and LC-0 … LC-(n−1). Model computes the envelope | 3.5, 6.2, 8.5, 8.7 |
| R4 | Left and right half of the panels | Left i ≤ n/2 − 1, right i ≥ n/2 | 3.2 |
| R5 | Mixed 0- and 1-based indexing | DOFs 1-based (Python index 2k − 1), panels 0-based | 3.5, 8.7 |
| R6 | Which `bar2s` value is N | N_e = es[0, 0] | 6.1 |
| R7 | Mass ties | Relative tolerance 10⁻⁹, then lower U_max, then type Pratt, Howe, Warren | 6.4 |
| R8 | Zero-force noise | N_tol = 10⁻⁹·W; compression when N_min,e < −N_tol | 3.6 |
| R9 | No passing design | Empty table plus the design with the lowest U_max | 6.4 |
| R10 | Reaction sign and `solveq` output | Σ R_y + Σ f_y = 0; r = K·a − f | 6.1, 8.3 |
| R11 | Verification range of n | n = 2, 4, 6, 8, 10; D7 table extended to n = 10 | D7, 8.1 |
| R12 | Hand-calculation reference | Verified by the engineer | 8.7 |
| R13 | I_y and I_z wording | I_y strong axis, I_z weak axis | 4 |
