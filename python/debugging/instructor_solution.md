# Instructor solution

## Intended diagnosis

The program is numerically executable, but the boundary marker `MARK_RIGHT`
is attached to the **top edge** in `build_geometry()`:

```python
g.spline([2, 3], marker=MARK_RIGHT)
```

The right edge is the segment from point 1 to point 2, so the marker should be
attached here:

```python
g.spline([1, 2], marker=MARK_RIGHT)
```

and removed from the top edge.

## Minimal fix

Change the geometry to:

```python
g.spline([1, 2], marker=MARK_RIGHT)
g.spline([2, 3])
```

No solver or numerical-algorithm change is required.

## Why this is a useful debugging example

The important point is that the code is syntactically valid and the linear
system can still be solved. The error is a **model-definition error**, not a
Python error.

An LLM may initially focus on matrix assembly, the solver, element type, or
numerical stability. Participants should learn to trace the scientific model
through the implementation before changing numerical code.

## Expected verification

After the fix:

- all nodes on x=0 have T=0
- all nodes on x=1 have T=100
- temperatures stay between 0 and 100
- the field should increase smoothly from left to right

## Visual check

`python debug_temperature.py --plot` shows the nodal temperature field.

- **Before the fix:** the hot region is along the top edge, and T drops
  towards the bottom-right corner. This is the field of a plate heated from
  the top, not the stated problem.
- **After the fix:** even vertical bands from 0 at x=0 to 100 at x=1. With
  insulated top and bottom edges the exact solution is T(x, y) = 100·x, so
  the contours should be straight vertical lines.

The optional prompt in step 2 of `prompts.md` has participants plot the
geometry markers themselves. This usually reveals the bug directly, so
consider holding it back until participants have formed a hypothesis.

The supplied tests should change from a failing right-boundary test to all
three tests passing.

## Instructor discussion points

Ask participants:

1. What did the LLM initially suspect?
2. Did it correctly identify the geometry marker?
3. Did it propose changing more code than necessary?
4. What evidence convinced you that the fix was correct?
5. Would a generic unit test have found this bug without knowing the physical
   boundary conditions?

The last question is particularly useful: scientific software often requires
**domain-aware tests**, not only tests for crashes or types.
