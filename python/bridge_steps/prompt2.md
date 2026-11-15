Implement truss_model.py with a class TrussBridge that builds only the geometry and topology for the three truss types: node coordinates, element connectivity, the edof matrix and the boundary-condition DOFs. No stiffness, no solving.

Also write pytest tests that check the counts of nodes, elements and constrained DOFs for n = 2, 4, 6, and that m + r = 2j holds (statical determinacy).