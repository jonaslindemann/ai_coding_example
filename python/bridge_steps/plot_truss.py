"""
Visualize the geometry and topology of a TrussBridge with matplotlib.

The plotting lives here, not in truss_model.py, so the model module stays free
of plotting and UI code.

Usage
-----
    python plot_truss.py TYPE L h n [--save FILE]

    TYPE   pratt | howe | warren
    L      span [m]
    h      height between chord centerlines [m]
    n      number of panels (even, >= 2)

Example:
    python plot_truss.py pratt 12 2 6
"""

import argparse

import matplotlib.pyplot as plt

from truss_model import TrussBridge, TRUSS_TYPES, MEMBER_GROUPS

# Visual style per member group (display only, no physical meaning)
GROUP_STYLE = {
    "bottom": dict(color="tab:blue", lw=2.5),
    "top": dict(color="tab:green", lw=2.5),
    "vertical": dict(color="tab:orange", lw=1.8),
    "diagonal": dict(color="tab:red", lw=1.8),
}


def plot_truss(truss, ax=None, show_labels=True):
    """Draw the truss geometry on a matplotlib Axes.

    Parameters
    ----------
    truss : TrussBridge
        The model to draw.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on. If None, a new figure and axes are created.
    show_labels : bool
        If True, write the node numbers and element numbers (both 1-based).

    Returns
    -------
    matplotlib.axes.Axes
        The axes the truss was drawn on.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))

    # Members, coloured by group. Plot one dummy line per group for the legend.
    for group in MEMBER_GROUPS:
        if group in truss.member_groups:
            ax.plot([], [], label=group, **GROUP_STYLE[group])
    for e, group in enumerate(truss.member_groups):
        ax.plot(truss.ex[e], truss.ey[e], solid_capstyle="round", **GROUP_STYLE[group])
        if show_labels:
            # Element number at the member midpoint
            xm, ym = truss.ex[e].mean(), truss.ey[e].mean()
            ax.annotate(str(e + 1), (xm, ym), fontsize=7, color="dimgray",
                        ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))

    # Nodes
    ax.plot(truss.coords[:, 0], truss.coords[:, 1], "o", color="black", ms=5, zorder=3)
    if show_labels:
        # Top nodes: label above. Bottom nodes: label below-right, clear of
        # the support symbols and the load arrows hanging under the node.
        dy = 0.06 * truss.h
        dx = 0.012 * truss.L
        for k, (x, y) in enumerate(truss.coords):
            if y > 0:
                ax.annotate(str(k + 1), (x, y + dy), fontsize=8, fontweight="bold",
                            ha="center", va="bottom")
            else:
                ax.annotate(str(k + 1), (x + dx, y - dy), fontsize=8, fontweight="bold",
                            ha="left", va="top")

    # Supports: triangle for the pin, circle for the roller
    pin, roller = truss.support_nodes
    xp, yp = truss.coords[pin - 1]
    xr, yr = truss.coords[roller - 1]
    s = 0.12 * truss.h  # symbol size, scaled to the drawing
    ax.fill([xp, xp - s, xp + s], [yp, yp - 1.5 * s, yp - 1.5 * s],
            color="gray", zorder=2, label="pin")
    ax.add_patch(plt.Circle((xr, yr - 0.75 * s), 0.75 * s, color="gray", zorder=2))
    ax.plot([], [], "o", color="gray", label="roller")

    # Load positions (direction only; P has no value at this stage). Drawn
    # hanging below the bottom chord so they don't hide the verticals.
    for node in truss.loaded_nodes:
        x, y = truss.coords[node - 1]
        ax.annotate("", xy=(x, y - 0.35 * truss.h), xytext=(x, y),
                    arrowprops=dict(arrowstyle="->", color="purple", lw=1.2))
    ax.plot([], [], color="purple", label="load P (positions)")

    ax.set_aspect("equal")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title(
        f"{truss.truss_type.capitalize()} truss: L = {truss.L:g} m, h = {truss.h:g} m, "
        f"n = {truss.n}  (j = {truss.n_nodes}, m = {truss.n_elements}, r = {truss.n_reactions})"
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=4, fontsize=8, frameon=False)
    # Annotations (load arrows, labels) don't extend autoscaling, so set limits
    # explicitly to include the arrows below the chord and the labels above it.
    pad_x = 0.06 * truss.L
    ax.set_xlim(-pad_x, truss.L + pad_x)
    ax.set_ylim(-0.5 * truss.h, 1.25 * truss.h)
    return ax


def main(argv=None):
    """Build a TrussBridge from command-line arguments, print a summary and plot it.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments (defaults to sys.argv[1:]). All model inputs are
        required; no default geometry is assumed.
    """
    parser = argparse.ArgumentParser(description="Plot a 2D truss bridge geometry.")
    parser.add_argument("truss_type", choices=TRUSS_TYPES, help="truss type")
    parser.add_argument("L", type=float, help="span [m]")
    parser.add_argument("h", type=float, help="height between chord centerlines [m]")
    parser.add_argument("n", type=int, help="number of panels (even, >= 2)")
    parser.add_argument("--save", metavar="FILE", help="save the figure to FILE instead of showing it")
    args = parser.parse_args(argv)

    truss = TrussBridge(args.truss_type, args.L, args.h, args.n)

    # Text summary of the model
    print(f"{truss.truss_type.capitalize()} truss, L = {truss.L:g} m, h = {truss.h:g} m, n = {truss.n}")
    print(f"  nodes j = {truss.n_nodes}, members m = {truss.n_elements}, "
          f"reactions r = {truss.n_reactions}, m + r = {truss.n_elements + truss.n_reactions}, "
          f"2j = {truss.n_dofs}")
    print(f"  constrained DOFs: {truss.bc_dofs.tolist()}")
    print(f"  loaded nodes:     {truss.loaded_nodes.tolist()}")

    plot_truss(truss)
    plt.tight_layout()
    if args.save:
        plt.savefig(args.save, dpi=150, bbox_inches="tight")
        print(f"  figure saved to {args.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
