# Debugging in Practice

## Scenario

The supplied Python program models steady-state heat conduction in a square
plate:

- plate dimensions: 1 x 1
- constant isotropic conductivity
- left boundary: **T = 0**
- right boundary: **T = 100**
- top and bottom boundaries: insulated
- no internal heat source

The program runs, but the result is not consistent with the stated physical
problem.

Your task is to diagnose the problem and make the smallest possible fix.

## Suggested AI-assisted workflow

### 1. Start from the symptom

> This Python program runs without an exception, but I suspect that the
> temperature field does not represent the physical problem described in the
> module docstring. Diagnose possible causes. Do not change the code yet.

### 2. Look at the result

Run the program with the temperature plot:

```bash
python debug_temperature.py --plot
```

> Here is the temperature field produced by the program. Before looking at
> the code again: what should the field look like for the problem described
> in the module docstring (T=0 on the left, T=100 on the right, insulated top
> and bottom)? Which features of the plot contradict that expectation?

Optionally, ask the AI to help you visualise the model definition itself:

> Add a plot of the geometry that shows which boundary marker is attached to
> each edge. Do not change the solver.

### 3. Trace the model into the code

> Trace the boundary-condition information from the geometry definition to
> the calls to `applybc`. Explain which physical edge each marker refers to.
> Be precise and quote the relevant code locations.

### 4. Challenge the diagnosis

> What evidence would distinguish a boundary-condition error from a numerical
> solver error? Suggest concrete checks I can perform without rewriting the
> whole program.

### 5. Request a minimal fix

> Propose the smallest code change that makes the implementation match the
> stated physical problem. Do not introduce unrelated refactoring.

### 6. Verify

> After the fix, what numerical properties should hold for the solution?
> Suggest tests that check the physical boundary conditions and the expected
> qualitative behaviour of the temperature field.

Run `python debug_temperature.py --plot` again and check that the plot now
matches your expectation from step 2.

## Rule for this exercise

Do not accept a proposed fix just because the code runs. Connect:

**code → physical model → numerical result → verification**
