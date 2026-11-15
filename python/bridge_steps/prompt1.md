I’m building a verified 2D truss bridge model with CALFEM for Python. Rules for this whole session:

Use only calfem.core functions (bar2e, bar2s, assem, solveq, extract_eldisp) for the mechanics. Do not write your own element formulations.
No plotting or UI code in the model module.
Never introduce an assumption, default value or unit that isn’t in the spec. If something is missing, ask me.

Here is my specification: bridge_spec.md. Don’t write any code yet. List anything that is ambiguous, inconsistent or missing for implementing it.