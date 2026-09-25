# Debugging: A Scientific Program That Runs but Is Wrong

This exercise is designed for approximately **25 minutes**.

The program models steady-state heat conduction in a square plate. It runs
without a Python exception, but its result does not match the stated physical
problem.

Participants use an AI assistant to diagnose the problem, propose a minimal
fix, and verify the result with tests.

## Files

- `debug_temperature.py` — intentionally faulty starting point
- `tests/test_debug_temperature.py` — verification tests
- `prompts.md` — suggested prompts and workflow
- `run_tests.md` — test instructions
- `instructor_solution.md` — diagnosis and discussion points
- `debug_temperature_fixed.py` — instructor reference implementation

## Learning objective

The exercise is deliberately a **scientific/model-definition bug**, rather
than a syntax error. The program can execute successfully while solving the
wrong physical problem.

The main lesson is:

> **AI proposes. Tests and physical reasoning determine correctness.**
