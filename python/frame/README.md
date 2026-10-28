# Steel frame: from equations to application

A multi-bay, multi-storey steel frame analysed with CALFEM `beam2e`
elements, turned into an interactive web application and a calculation
report.

The example follows one principle:

> **The engineer owns the model and its validation. AI helps build the
> application around it.**

The engineering problem itself (geometry, loads, supports, the beam
element, checks and verification) is described with illustrations in
[engineering_problem.md](engineering_problem.md). Its figures are
regenerated with `python figures/make_figures.py`.

## Who owns what

| Layer | Files | Owner |
|---|---|---|
| Data | `sections.py` | Engineer |
| Computational core | `frame_model.py` | Engineer |
| Verification | `verification.py`, `test_frame_model.py` | Engineer |
| Failure modes demo | `failure_modes.py` | Engineer |
| Calculation report | `final/frame_report.py` | AI-assisted |
| Web application | `final/frame_app.py`, `final/test_frame_app.py` | AI-assisted |
| Design search | `final/frame_design.py` | AI-assisted |

The application layer may only *present* results from the core. It never
computes engineering quantities itself.

## Running it

```bash
python verification.py         # analytical benchmarks, as a table
python -m pytest               # 46 tests: benchmarks, physics, failure-mode guards
python failure_modes.py        # three plausible-but-wrong variants

cd final
python frame_report.py         # writes frame_report.html
python frame_design.py         # lightest section combinations, pinned bases
python -m pytest               # simulated-user tests of the web application
python frame_app.py            # http://localhost:8080
```

Dependencies: `calfem-python numpy matplotlib pytest`, plus `nicegui plotly`
for the web application.

## The workflow

1. **Problem → equations.** A frame of Euler-Bernoulli beams, rigid joints,
   fixed or pinned bases, uniform beam loads, horizontal floor loads and
   self-weight.
2. **Numerical model.** One `beam2e` element per member. With element
   loads this is exact, so no mesh study is needed.
3. **Implementation.** `FrameModel` (a generic frame) and `PlaneFrame` (the
   parametric building frame), about 300 lines of code.
4. **Verification.** There are three kinds of evidence:
   - *Analytical benchmarks*: cantilevers, simply supported and fixed-fixed
     beams, an inclined member, an axially loaded column, and portal frames
     with fixed and pinned bases. These should match to round-off.
   - *Physical properties that must hold for any frame*: global equilibrium
     computed independently of K, symmetry, superposition, pinned bases with
     zero moment, and self-weight reactions equal to the steel weight.
   - *Data checks*: section depth from I/W, and mass per metre.
5. **Application (AI-assisted).** The report and the web app, from the
   prompts in `prompts.md`.

## Lessons found while building it

These came up while building the example, and they make good talk material:

- **The library had a bug.** `calfem.core.beam2s` (3.6.16, still present) builds its
  evaluation points with `np.arange` on floats. For a 3.6 m column with
  21 points it returns 22 points and crashes. The core now evaluates
  section forces with `linspace`, and a test checks that it gives the same
  results as `beam2s` wherever `beam2s` works.
- **The check needed checking.** The first version of the equilibrium
  check left out the moment of the reaction forces about the origin and
  reported a 98 % error. Verification code is code too.
- **The test was wrong, not the model.** Under symmetric gravity load the
  roof nodes move apart, so "max |ux| = 0" failed. Sway is the *mean*
  roof displacement. Deciding this took engineering judgement, not a
  code fix.

## Failure modes (`failure_modes.py`)

Each variant runs, plots nicely and is wrong:

| Mistake | Effect | Caught by |
|---|---|---|
| Global loads passed to `beam2e` as local loads | Column self-weight becomes a sideways load: sway +43 % | Equilibrium check, benchmarks |
| I converted with the cm² factor instead of cm⁴ | Deflections ~0, "all checks OK" | **Only** the section-data test |
| UI option typo: "Pinned" silently becomes "fixed" | Sway −55 %, "all checks OK" | **No automated check.** The input echo ("As modelled" line, report section 1) and the engineer's judgement |

The last two rows are the point of the talk. Errors that make the
structure look *safer* pass every numerical test. Autoscaled
deformation plots hide magnitude errors, which is why the app and the
report always print the real maximum displacement next to the scale
factor.

## Scope and limitations

This is a teaching example, not a design tool. It uses linear elastic,
first-order analysis. It does not check buckling or lateral-torsional
buckling, and it applies no partial factors or load combinations.
Utilisation is an elastic stress ratio, not a Eurocode check. Section
values are nominal and must be verified against supplier tables.
