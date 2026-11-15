# From problem text to application: a footbridge, prompt by prompt

A sequence of eleven prompts that goes from a design problem written in plain
text, through a verified CALFEM truss model, to a Qt application that answers
the client's question.

Use one prompt per step. After each step, do the **check** yourself before you
go on, and commit what you approved. The git history is the audit trail.

The steps fall into four groups:

| Steps | What happens | Who owns it |
|---|---|---|
| 0–1 | Problem text → specification | You (the AI drafts and asks) |
| 2–7 | Specification → verified model core | You verify, the AI implements |
| 8 | Freeze the core | You |
| 9–10 | Design checks and application | The AI builds, you verify the checks |

---

## The problem

Save this as `problem.md`. It is written the way a client might write it. It
deliberately leaves out things the model needs.

> A pedestrian bridge is to cross a 20 m wide stream. The deck is 2.5 m wide
> and is carried by two identical steel trusses, one on each side. Design for
> a crowd load of 4 kN/m² on the deck and ignore self-weight in this first
> version. The steel is S355. The midspan deflection under crowd load must
> not exceed L/400. No member may yield, and no compression member may
> buckle. Which truss type (Pratt, Howe or Warren), height and member size
> gives the lightest design?

---

## Step 0: From problem text to specification

```text
problem.md contains a design problem from a client. Don't write any code.

Turn it into a specification, bridge_spec_draft.md, that a 2D truss model in CALFEM
for Python can be implemented and verified against. It should cover:
- the structural model: truss types, geometry parameters, supports
- loads: how the load on the deck becomes nodal loads on one truss
- material and section properties
- units and sign conventions
- required outputs
- the design checks the problem asks for

For every value you derive from the text, show the derivation. Then list
everything the text does not give but the model or the design checks need.
Ask me about each item instead of assuming an answer.
```

**Your check:** you approve the spec line by line. In particular:

- The load path: per truss q·b/2 = 4 · 2.5 / 2 = 5 kN/m, so P = 5 · L/n kN at
  each interior bottom-chord node (25 kN for n = 4) and P_end = P/2 at each
  support node.
- What the AI should have asked about: second moment of area I and buckling
  length for compression members, safety factors, the list of available
  sections, the range of heights to consider, and partial-span loading. If it
  didn't ask about buckling, that's a failure mode worth showing.
- You fill the gaps. Keep the AI's draft (`bridge_spec_draft.md`) and write
  your answers into a copy, `bridge_spec_final.md`. Let the AI work the
  answers in, and repeat until nothing is open.
- An answer such as "the range will be determined later" leaves the question
  open. Every answer has to give a value or a decision.
- The available sections (A and I for each section) come from a table you
  trust. If you let the AI retrieve them, have it recompute A and I from the
  section dimensions as a cross-check. Then approve the list yourself.

---

## Step 1: Ground rules and spec review

```text
I'm building a verified 2D truss bridge model with CALFEM for Python. Rules
for this whole session:
- Use only calfem.core functions (bar2e, bar2s, assem, solveq,
  extract_eldisp) for the mechanics. Do not write your own element
  formulations.
- No plotting or UI code in the model module.
- Never introduce an assumption, default value or unit that isn't in the
  spec. If something is missing, ask me.
- Put all tests in a folder called tests/.

The specification is in bridge_spec_final.md. Don't write any code yet. List
anything that is ambiguous, inconsistent or missing for implementing it.
```

**Your check:** update `bridge_spec_final.md` with the answers, *before* any
code is written. You decide; the AI may draft the wording, but only applies it
after you approve. Record each decision in the spec's decision log. The spec
should lead the code, not describe it afterwards.

This review typically finds:

- the model needs one area per section class (A_c for the chords, A_w for
  the web), not a single A;
- unclassified members, such as Warren's end diagonals;
- mixed 0- and 1-based indexing;
- tie-breaking and zero-force tolerances that the search needs.

---

## Step 2: Geometry and topology only

```text
Implement truss_model.py with a class TrussBridge that builds only the
geometry and topology for the three truss types as defined in
bridge_spec_final.md: node coordinates, element connectivity, member groups,
section classes (chord or web), the edof matrix and the boundary-condition
DOFs. No stiffness, no solving.

Also write pytest tests in tests/ that check the counts of nodes, elements and
constrained DOFs for n = 2, 4, 6, 8, 10, and that m + r = 2j holds (statical
determinacy).
```

**Your check:** sketch n = 4 for each type on paper, with member groups and
section classes. The expected counts in the tests come from your sketch.

---

## Step 3: Documentation

```text
Add docstrings to the TrussBridge class and its methods explaining purpose,
inputs and outputs. Explain the geometry and topology construction, the edof
matrix and the boundary-condition DOFs. Add inline comments where the logic
isn't obvious. Don't change any logic; all tests must still pass.
```

**Your check:** read the docstrings. Wrong documentation is also a failure.

---

## Step 4: Plot the geometry

```text
Write a separate script, plot_truss.py, with a main() function that creates a
TrussBridge and plots its geometry with matplotlib: node and element numbers,
supports and the positions of the loads. Take the truss type, L, h and n as
command-line arguments with no defaults.
```

**Your check:** compare the plot with your sketch from step 2.

---

## Step 5: Stiffness, solving and recovering forces

```text
Add a method solve(E, A_c, A_w, w) using bar2e, assem, solveq,
extract_eldisp and bar2s, as specified in sections 3.5, 3.6 and 6 of
bridge_spec_final.md. It should:
- build the nodal loads from the line load w, for LC-full and for the
  single-panel cases LC-0 … LC-(n−1)
- store displacements a, reactions r and normal forces N for each load case
- compute the envelope N_max and N_min for each member
- return (a, r, N, N_max, N_min), where a, r and N are for LC-full

Above each block of code, add a comment saying which step of the direct
stiffness method it implements, with reference to the spec. Then list every
assumption in your code that isn't stated explicitly in the spec.
```

**Your check:** read the assumption list carefully. Anything you agree with
goes into the spec now, written by you.

---

## Step 6: Benchmark against your own reference values

Derive the expected values yourself first. For a Pratt truss with L = 20 m,
h = 3 m, n = 4, w = 2 kN/m, E = 210 GPa and A_c = A_w = 0.01 m². The line
load gives P = w·L/n = 10 kN at the interior nodes and P_end = 5 kN at each
support node:

- Support reactions: R = P(n − 1)/2 + P_end = 15 + 5 = 20 kN. Only the 15 kN
  from the interior loads passes through the members, so the formulas below
  use R = 15 kN.
- Midspan moment: M(L/2) = P·n·L/8 = 100 kNm
- Top chord next to midspan: −M(L/2)/h = −33.33 kN (compression)
- Bottom chord next to midspan: M(L/2 − L/n)/h = 75/3 = 25 kN (tension).
  In a Pratt the bottom chord does **not** carry M(L/2)/h.
- Diagonal next to midspan: V·d/h with V = R − P = 5 kN and
  d = √(5² + 3²), so 5·√34/3 = 9.718253 kN
- Midspan deflection by the unit-load method: Σ N·n·ℓ/(EA) = 0.6728 mm.
  P_end acts on supported DOFs, so it does not change this.

```text
Write pytest tests in tests/test_benchmark.py for a Pratt truss with
L = 20 m, h = 3 m, n = 4, w = 2 kN/m, E = 210 GPa and A_c = A_w = 0.01 m²,
under LC-full. The expected values are:
- support reactions: 20 kN each
- top chord members next to midspan: -100000/3 N (compression)
- bottom chord members next to midspan: 25000 N (tension)
- diagonal next to midspan: 5*sqrt(34)/3 kN
- midspan deflection: 0.6728 mm downward (to four significant figures)

Use a relative tolerance of 1e-9 for forces and a relative tolerance of
1e-3 for the deflection. Do not change the expected values. If a test fails,
report it and diagnose the cause, but don't change the test.
```

**Your check:** the expected values are yours. If a test fails, the AI may
show that a reference value is wrong. If you agree, **verify the corrected
value independently** (by hand, with other software or in a separate
session) before you change the test. Otherwise model and reference values
come from the same source.

Give expected values exactly, as a formula or fraction (−100000/3 N), not
rounded (−33333.33 N). A value rounded to 7 significant figures has a
relative error of about 10⁻⁷, so it can never pass a 10⁻⁹ tolerance. This
is a typical first failure in this step. The model is right and the
reference value is wrong.

---

## Step 7: Property tests based on the physics

```text
Add property-based tests in tests/test_properties.py, parametrized over all
truss types and n = 2, 4, 6, 8, 10, that check (spec section 8):
1. Global equilibrium: sum of reactions + sum of applied loads = 0 in x and
   y, to machine precision, including P_end.
2. Linearity: doubling w doubles all displacements and forces.
3. Symmetry: under LC-full, members in mirrored positions carry equal forces.
4. Determinacy: multiplying E, or A_c and A_w together, by 10 leaves all
   normal forces unchanged and divides displacements by 10. Changing only
   A_c or only A_w leaves all normal forces unchanged.
5. Superposition: the sum of the single-panel cases LC-0 … LC-(n−1) equals
   LC-full, and the LC-full forces lie within the envelope [N_min, N_max].
```

**Your check:** read each test and confirm that it really tests its property.
Start with the symmetry mapping, the most complex one. Test 4 is the
strongest: if it fails, the topology or the supports are wrong.

---

## Step 8: Adversarial review, then freeze

In a **new session**, or with a different model:

```text
Here is a specification, a model implementation and its tests:
bridge_spec_final.md, truss_model.py and tests/. Act as a critical reviewer.
1. Where does the code deviate from the spec?
2. Describe concrete ways the model could be wrong while all the tests
   still pass.
3. Suggest the missing tests that would catch those cases.
Don't change any files.
```

**Your check:** decide which suggested tests to add (back to step 6 for any new
reference values). Then freeze the core:

```text
git tag model-v1
```

---

## Step 9: Design checks, separate from the model

```text
truss_model.py and tests/ are verified and frozen (git tag model-v1). Do not
modify them. Use only this public API:
  TrussBridge(truss_type, L, h, n),
  solve(E, A_c, A_w, w) -> (a, r, N, N_max, N_min),
  coords, elements, member_groups, section_classes, support_nodes,
  loaded_nodes, lengths, midspan_node, N_tol.

Implement the design checks in bridge_spec_final.md (section 7) in a new
module design_checks.py:
- the line load w = q*b/2 from the deck load, as derived in the spec (D5)
- for each member: stress utilisation max(|N_max|, |N_min|) / (A * fy)
- for compression members (N_min < -N_tol, spec 3.6): buckling utilisation
  |N_min| / (pi^2 * E * I / l^2), with I = min(I_y, I_z) and the buckling
  length l from the spec
- deflection utilisation: |uy| at the midspan node under LC-full / (L / 400)
- total steel mass of one truss
- the design search and ranking in spec section 6.4, including tie-breaking
  and the result when no design passes
Use the partial factors (all 1) and the section list in the spec. If
something the checks need isn't in the spec, ask me.

Write tests in tests/test_design_checks.py with expected values I give you.
```

**Your check:** derive at least one value of each check by hand. For example,
scale the step 6 case to the design load w = 5 kN/m (P = 25 kN): the top
chord next to midspan carries 2.5 · 100/3 = 250/3 kN ≈ 83.3 kN in compression. It is in
compression in every single-panel case, so its envelope N_min equals this
LC-full value. Its stress and buckling utilisations then follow from your
section's A and I. Give those numbers to the AI as the expected values,
as exact formulas, not rounded decimals.

---

## Step 10: The application

```text
truss_model.py, design_checks.py and tests/ are verified and frozen. Do not
modify them. Use only their public APIs.

Build a Qt (qtpy) application with two tabs:

Analysis
- select the truss type, adjust L, h, n and the deck load
- show the deformed shape with members coloured by normal force, using a
  diverging colour map centred on zero
- show the deformation scale factor on screen

Design
- choose a section from the spec's list for the chords and for the web
  members
- colour members by their highest utilisation and highlight the governing
  member
- show a pass/fail summary for stress, buckling and deflection, with the
  utilisation values, and the total steel mass
- a button that runs the design search in design_checks.py (all truss types,
  the panel counts and heights in the spec, and all section combinations)
  and lists the lightest designs that pass
- Produce a summary of the lightest passing designs, including their truss type, panel count, height, sections, and total steel mass. 
- Application should be able to generate an engineering summary of the lightest passing designs.

Update the plots as parameters change. The application must not compute
anything itself: every number comes from truss_model.py or design_checks.py.
```

**Your check:**

```text
pytest -q
git diff model-v1 -- truss_model.py design_checks.py tests/
```

Both must pass and the diff must be empty. Then check that the lightest
design reported by the application passes all three checks when you compute
them by hand.
