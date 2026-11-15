Add property-based tests, parametrized over all truss types and n = 2, 4, 6, 8, that check:

Global equilibrium: the reactions balance the applied loads to machine precision.
Linearity: doubling P doubles all displacements and forces.
Symmetry: under symmetric loading, members in mirrored positions carry equal forces.
Determinacy: multiplying E or A by 10 leaves all normal forces unchanged and divides displacements by 10.
Superposition: the result for two load cases combined equals the sum of the results for each case alone.