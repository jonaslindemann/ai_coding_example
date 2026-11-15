Write pytest tests for a Pratt truss with L = 20 m, h = 3 m, n = 4, P = 10 kN, E = 210 GPa and A = 0.01 m². The expected values are:

* Support reactions: R = P(n−1)/2.
* Midspan moment: M = P·n·L/8.
* Force in the central bottom-chord member: N = M/h (tension).
* Diagonal left to midspan: Should around 9.718 kN
* midspan deflection: 0.6728 mm

e-9 for forces and 1e-6 for deflection. Do not change the expected values. If a test fails, report it and diagnose the cause, but don’t change the test.