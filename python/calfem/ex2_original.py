# exm_stress_2d_materials_profile.py

import time
import numpy as np
from scipy.sparse import coo_matrix

import calfem.core as cfc
import calfem.geometry as cfg
import calfem.mesh as cfm
import calfem.utils as cfu
# import calfem.vis_mpl as cfv   # keep plotting optional

cfu.enableLogging()

# -----------------------------
# Controls for workshop scaling
# -----------------------------
#MESH_SIZES = [0.05, 0.025, 0.0125]   # small, medium, large
MESH_SIZES = [0.025]   # small, medium, large
PROFILE_REPEATS = 3                  # repeat compute path for clearer timings
ENABLE_PLOTTING = False              # disable during profiling
PRINT_SUMMARY = True

# ---- General parameters ----
t = 0.2
v = 0.35
E1 = 2e9
E2 = 0.2e9

ptype = 1
ep = [ptype, t]
D1 = cfc.hooke(ptype, E1, v)
D2 = cfc.hooke(ptype, E2, v)

mark_E1 = 55
mark_E2 = 66
mark_fixed = 70
mark_load = 90

elprop = {
    mark_E1: [ep, D1],
    mark_E2: [ep, D2],
}

el_type = 3
dofs_per_node = 2

def build_geometry():
    g = cfg.Geometry()

    g.point([0, 0])      # 0
    g.point([1, 0])      # 1
    g.point([1, 1])      # 2
    g.point([0, 1])      # 3
    g.point([0.2, 0.2])  # 4
    g.point([0.8, 0.2])  # 5
    g.point([0.8, 0.8])  # 6
    g.point([0.2, 0.8])  # 7

    g.spline([0, 1], marker=mark_fixed)
    g.spline([2, 1])
    g.spline([3, 2], marker=mark_load)
    g.spline([0, 3])

    g.spline([4, 5])
    g.spline([5, 6])
    g.spline([6, 7])
    g.spline([7, 4])

    g.surface([0, 1, 2, 3], holes=[[4, 5, 6, 7]], marker=mark_E1)
    g.surface([4, 5, 6, 7], marker=mark_E2)

    return g

# ---------------------------------------------------------------
# Batched versions of cfc.planqe / cfc.planqs (all elements at once)
#
# Same formulation as CALFEM: each quad is split into 4 linear
# triangles meeting at the centroid, and the centre node dofs (9, 10)
# are condensed out. Only plane stress/strain with a 3x3 D and no
# body load (eq) is supported.
# ---------------------------------------------------------------

def _planq_subtriangles(ex, ey, t, D):
    """Return the 10x10 sub-triangle stiffness, plus (A, B, dofs) per triangle."""
    if D.shape[1:] != (3, 3):
        raise ValueError("Batched planq routines require a 3x3 D matrix")

    n = ex.shape[0]
    xm = ex.mean(axis=1)
    ym = ey.mean(axis=1)

    K10 = np.zeros((n, 10, 10))
    triangles = []
    for i in range(4):
        j = (i + 1) % 4
        x = np.stack([ex[:, i], ex[:, j], xm], axis=1)
        y = np.stack([ey[:, i], ey[:, j], ym], axis=1)

        # Linear triangle shape function derivatives (b = dN/dx*2A, c = dN/dy*2A)
        b = np.roll(y, -1, axis=1) - np.roll(y, -2, axis=1)
        c = np.roll(x, -2, axis=1) - np.roll(x, -1, axis=1)
        A = 0.5 * np.sum(x * b, axis=1)          # signed, as in cfc.plante

        B = np.zeros((n, 3, 6))
        B[:, 0, 0::2] = b
        B[:, 1, 1::2] = c
        B[:, 2, 0::2] = c
        B[:, 2, 1::2] = b
        B /= (2 * A)[:, None, None]

        Ke = np.einsum("nki,nkl,nlj->nij", B, D, B) * (A * t)[:, None, None]

        dofs = np.array([2 * i, 2 * i + 1, 2 * j, 2 * j + 1, 8, 9])
        K10[:, dofs[:, None], dofs] += Ke
        triangles.append((A, B, dofs))

    return K10, triangles

def planqe_batch(ex, ey, t, D):
    """Element stiffness matrices, shape (n_el, 8, 8)."""
    K10, _ = _planq_subtriangles(ex, ey, t, D)
    Kaa = K10[:, :8, :8]
    Kab = K10[:, :8, 8:]
    Kbb = K10[:, 8:, 8:]
    return Kaa - Kab @ np.linalg.solve(Kbb, np.swapaxes(Kab, 1, 2))

def planqs_batch(ex, ey, t, D, ed):
    """Area-averaged element stresses [sx, sy, txy], shape (n_el, 3)."""
    K10, triangles = _planq_subtriangles(ex, ey, t, D)

    # Recover the condensed centre node displacements
    rhs = -np.einsum("nij,nj->ni", K10[:, 8:, :8], ed)
    a_mid = np.linalg.solve(K10[:, 8:, 8:], rhs[..., None])[..., 0]
    a = np.concatenate([ed, a_mid], axis=1)

    es = np.zeros((ex.shape[0], 3))
    A_tot = np.zeros(ex.shape[0])
    for A, B, dofs in triangles:
        es += A[:, None] * np.einsum("nij,njk,nk->ni", D, B, a[:, dofs])
        A_tot += A
    return es / A_tot[:, None]

def run_case(el_size_factor):
    timings = {}

    t0 = time.perf_counter()
    g = build_geometry()
    mesh = cfm.GmshMeshGenerator(g)
    mesh.el_size_factor = el_size_factor
    mesh.el_type = el_type
    mesh.dofs_per_node = dofs_per_node
    coords, edof, dofs, bdofs, elementmarkers = mesh.create()
    timings["mesh"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    nDofs = np.size(dofs)
    ex, ey = cfc.coordxtr(edof, coords, dofs)

    # Per-element thickness and material matrix
    t_el = np.array([elprop[m][0][1] for m in elementmarkers])
    D_el = np.array([elprop[m][1] for m in elementmarkers])

    n_edof = edof.shape[1]
    Ke_all = planqe_batch(ex, ey, t_el, D_el)

    # Assemble all element matrices in one go (duplicate entries are summed)
    idx = edof - 1
    rows = np.repeat(idx, n_edof, axis=1).ravel()
    cols = np.tile(idx, (1, n_edof)).ravel()
    K = coo_matrix((Ke_all.ravel(), (rows, cols)), shape=(nDofs, nDofs)).tocsr()
    timings["assembly"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    bc = np.array([], "i")
    bcVal = np.array([], "i")
    bc, bcVal = cfu.applybc(bdofs, bc, bcVal, mark_fixed, 0.0)

    f = np.zeros((nDofs, 1))
    cfu.applyforcetotal(bdofs, f, mark_load, value=-10e5, dimension=2)

    a, r = cfc.spsolveq(K, f, bc, bcVal)
    timings["solve"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    ed = cfc.extract_eldisp(edof, a)
    es = planqs_batch(ex, ey, t_el, D_el, ed)
    sx, sy, txy = es[:, 0], es[:, 1], es[:, 2]
    von_mises = np.sqrt(sx**2 - sx*sy + sy**2 + 3*txy**2)
    timings["postprocess"] = time.perf_counter() - t0

    return {
        "n_dofs": nDofs,
        "n_elements": edof.shape[0],
        "timings": timings,
    }

def main():
    for h in MESH_SIZES:
        results = []
        for _ in range(PROFILE_REPEATS):
            results.append(run_case(h))

        n_dofs = results[0]["n_dofs"]
        n_elements = results[0]["n_elements"]

        avg = {}
        for key in results[0]["timings"]:
            avg[key] = sum(r["timings"][key] for r in results) / len(results)

        if PRINT_SUMMARY:
            print(f"\nMesh size factor: {h}")
            print(f"Elements: {n_elements}")
            print(f"DOFs:     {n_dofs}")
            for key, value in avg.items():
                print(f"{key:12s}: {value:.4f} s")

if __name__ == "__main__":
    main()