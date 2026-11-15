"""Plot the geometry of a TrussBridge for visual checking.

Usage::

    python plot_truss.py TYPE L H N

for example ``python plot_truss.py pratt 20 3 4``. TYPE is pratt, howe or
warren, L and H are the span and height in metres, and N is the number of
panels. All four arguments are required.

The plot shows node numbers, element numbers, the supports (a pin at B_0 and
a roller at B_n) and arrows at the loaded bottom-chord nodes. The arrows show
only where loads act, not how large they are. Chord members are drawn as
thick lines and web members as thin lines.
"""

import argparse

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon

from truss_model import CLASS_CHORD, TRUSS_TYPES, TrussBridge


def parse_args(argv=None):
    """Parse the command-line arguments. All four arguments are required."""
    parser = argparse.ArgumentParser(description="Plot the geometry of a footbridge truss.")
    parser.add_argument("truss_type", choices=TRUSS_TYPES, type=str.lower,
                        help="truss type")
    parser.add_argument("L", type=float, help="span between support centrelines [m]")
    parser.add_argument("h", type=float, help="truss height between chord centrelines [m]")
    parser.add_argument("n", type=int, help="number of panels (even, >= 2)")
    return parser.parse_args(argv)


def _draw_pin(ax, x, y, size):
    """Draw a pinned support: a triangle under the node and a hatched ground line."""
    ax.add_patch(Polygon([[x, y], [x - size, y - size], [x + size, y - size]],
                         closed=True, facecolor="lightgrey", edgecolor="black", zorder=1))
    ax.plot([x - 1.5 * size, x + 1.5 * size], [y - size, y - size], color="black", lw=1.5)


def _draw_roller(ax, x, y, size):
    """Draw a roller support: a triangle on two wheels above a ground line."""
    ax.add_patch(Polygon([[x, y], [x - size, y - size * 0.75], [x + size, y - size * 0.75]],
                         closed=True, facecolor="lightgrey", edgecolor="black", zorder=1))
    r = size * 0.125
    for dx in (-size * 0.5, size * 0.5):
        ax.add_patch(Circle((x + dx, y - size * 0.75 - r), r,
                            facecolor="white", edgecolor="black", zorder=1))
    ground = y - size * 0.75 - 2 * r
    ax.plot([x - 1.5 * size, x + 1.5 * size], [ground, ground], color="black", lw=1.5)


def plot_bridge(bridge, ax=None):
    """Plot the geometry of a TrussBridge on a matplotlib axes and return the axes."""
    if ax is None:
        _, ax = plt.subplots(figsize=(12, 5))

    # Symbol sizes scale with the span so plots look alike for any L, n and h.
    size = 0.04 * bridge.L

    # Members, numbered 1 ... m at their midpoints.
    for e in range(bridge.num_elements):
        x, y = bridge.ex[e], bridge.ey[e]
        is_chord = bridge.section_classes[e] == CLASS_CHORD
        ax.plot(x, y, color="tab:blue" if is_chord else "tab:orange",
                lw=3.0 if is_chord else 1.5, zorder=2)
        ax.text(x.mean(), y.mean(), str(e + 1), fontsize=8, color="tab:blue",
                ha="center", va="center", zorder=4,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="tab:blue", lw=0.5))

    # Nodes, numbered 1 ... j.
    ax.plot(bridge.coords[:, 0], bridge.coords[:, 1], "o", color="black", ms=5, zorder=3)
    for k, (x, y) in enumerate(bridge.coords, start=1):
        ax.annotate(str(k), (x, y), xytext=(5, 6), textcoords="offset points",
                    fontsize=9, fontweight="bold", color="black", zorder=5)

    # Supports: a pin at the first support node and a roller at the second.
    pin_node, roller_node = bridge.support_nodes
    _draw_pin(ax, *bridge.coords[pin_node - 1], size)
    _draw_roller(ax, *bridge.coords[roller_node - 1], size)

    # Load positions: downward arrows ending just above each loaded node.
    for k in bridge.loaded_nodes:
        x, y = bridge.coords[k - 1]
        ax.annotate("", xy=(x, y + 0.1 * size), xytext=(x, y + 1.6 * size),
                    arrowprops=dict(arrowstyle="-|>", color="tab:red", lw=1.5), zorder=4)

    ax.plot([], [], color="tab:blue", lw=3.0, label="chord members")
    ax.plot([], [], color="tab:orange", lw=1.5, label="web members")
    ax.plot([], [], color="tab:red", marker=r"$\downarrow$", ls="none", ms=10,
            label="load positions")
    # The legend sits below the axes so it never covers a node.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize=8,
              frameon=False)

    ax.set_aspect("equal")
    margin = 2 * size
    ax.set_xlim(-margin, bridge.L + margin)
    ax.set_ylim(-2 * size, bridge.h + margin + size)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title(f"{bridge.truss_type.capitalize()} truss: L = {bridge.L:g} m, "
                 f"h = {bridge.h:g} m, n = {bridge.n}  "
                 f"({bridge.num_nodes} nodes, {bridge.num_elements} elements)")
    ax.grid(True, ls=":", lw=0.5)
    return ax


def main(argv=None):
    """Create a TrussBridge from the command-line arguments and show its plot."""
    args = parse_args(argv)
    bridge = TrussBridge(args.truss_type, args.L, args.h, args.n)
    plot_bridge(bridge)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
