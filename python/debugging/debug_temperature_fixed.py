"""2-D steady-state heat conduction example for the debugging workshop.

The script models a square plate with constant conductivity. The intended
boundary conditions are T=0 on the left edge and T=100 on the right edge.
The top and bottom edges are insulated.

This version intentionally contains a scientific bug. The 100-degree boundary
condition is associated with the wrong geometry marker. The program therefore
runs and produces a temperature field, but it does not represent the stated
physical problem.
"""

import numpy as np
import calfem.core as cfc
import calfem.geometry as cfg
import calfem.mesh as cfm
import calfem.utils as cfu


WIDTH = 1.0
HEIGHT = 1.0
TEMPERATURE_LEFT = 0.0
TEMPERATURE_RIGHT = 100.0

MARK_LEFT = 10
MARK_RIGHT = 20


def build_geometry():
    """Create the plate geometry and boundary markers."""
    g = cfg.Geometry()

    g.point([0.0, 0.0])
    g.point([WIDTH, 0.0])
    g.point([WIDTH, HEIGHT])
    g.point([0.0, HEIGHT])

    g.spline([0, 1])
    g.spline([1, 2], marker=MARK_RIGHT)
    g.spline([2, 3])
    g.spline([3, 0], marker=MARK_LEFT)

    g.surface([0, 1, 2, 3])
    return g


def solve_temperature():
    """Solve the steady-state heat-conduction problem.

    Returns
    -------
    tuple
        Coordinates, nodal temperatures, and boundary degrees of freedom.
    """
    g = build_geometry()

    mesh = cfm.GmshMesh(g)
    mesh.el_size_factor = 0.15
    mesh.el_type = 3
    mesh.dofs_per_node = 1

    coords, edof, dofs, bdofs, _ = mesh.create()

    n_dofs = np.size(dofs)
    ex, ey = cfc.coordxtr(edof, coords, dofs)
    conductivity = np.identity(2, dtype=float)
    ep = [1.0, 1]

    K = np.zeros((n_dofs, n_dofs))
    for eltopo, elx, ely in zip(edof, ex, ey):
        Ke = cfc.flw2i4e(elx, ely, ep, conductivity)
        cfc.assem(eltopo, K, Ke)

    f = np.zeros((n_dofs, 1))

    bc = np.array([], dtype=int)
    bc_val = np.array([], dtype=float)
    bc, bc_val = cfu.applybc(
        bdofs, bc, bc_val, MARK_LEFT, TEMPERATURE_LEFT
    )

    # Boundary conditions for the two prescribed-temperature edges.
    bc, bc_val = cfu.applybc(
        bdofs, bc, bc_val, MARK_RIGHT, TEMPERATURE_RIGHT
    )

    temperature, reaction = cfc.solveq(K, f, bc, bc_val)
    return coords, temperature, reaction


def plot_temperature(coords, temperature, title="Temperature field"):
    """Plot the nodal temperatures as filled contours over the plate."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 5))
    contours = ax.tricontourf(
        coords[:, 0], coords[:, 1], temperature[:, 0], levels=21, cmap="inferno"
    )
    ax.plot(coords[:, 0], coords[:, 1], "k.", markersize=2)
    fig.colorbar(contours, ax=ax, label="Temperature")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(title)
    ax.set_aspect("equal")
    plt.show()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--plot", action="store_true", help="show the temperature field"
    )
    args = parser.parse_args()

    coords, temperature, _ = solve_temperature()
    print(f"Number of nodes: {len(coords)}")
    print(f"Minimum temperature: {temperature.min():.6f}")
    print(f"Maximum temperature: {temperature.max():.6f}")

    if args.plot:
        plot_temperature(coords, temperature)
