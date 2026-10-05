# exm_stress_2d_materials_profile.py

import time
import math
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
REUSE_MESH_IN_REPEATS = True         # mesh once, repeat compute path

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

def prepare_case(el_size_factor):
    t0 = time.perf_counter()
    g = build_geometry()
    mesh = cfm.GmshMeshGenerator(g)
    mesh.el_size_factor = el_size_factor
    mesh.el_type = el_type
    mesh.dofs_per_node = dofs_per_node
    coords, edof, dofs, bdofs, elementmarkers = mesh.create()
    mesh_time = time.perf_counter() - t0

    return {
        "coords": coords,
        "edof": edof,
        "dofs": dofs,
        "bdofs": bdofs,
        "elementmarkers": elementmarkers,
        "mesh_time": mesh_time,
    }

def compute_case(prepared):
    timings = {}

    coords = prepared["coords"]
    edof = prepared["edof"]
    dofs = prepared["dofs"]
    bdofs = prepared["bdofs"]
    elementmarkers = prepared["elementmarkers"]

    t0 = time.perf_counter()
    nDofs = np.size(dofs)
    ex, ey = cfc.coordxtr(edof, coords, dofs)
    n_elements = edof.shape[0]
    elementmarkers_arr = np.asarray(elementmarkers)
    marker_groups = {
        marker: np.where(elementmarkers_arr == marker)[0]
        for marker in elprop
    }

    edof0 = np.asarray(edof, dtype=np.int64) - 1
    n_el, n_edof = edof0.shape
    block_size = n_edof * n_edof
    total_nnz = n_el * block_size
    rows = np.empty(total_nnz, dtype=np.int64)
    cols = np.empty(total_nnz, dtype=np.int64)
    data = np.empty(total_nnz, dtype=np.float64)
    row_pattern = np.repeat(np.arange(n_edof), n_edof)
    col_pattern = np.tile(np.arange(n_edof), n_edof)
    planqe = cfc.planqe
    elprop_local = elprop

    for marker, idxs in marker_groups.items():
        ep_marker, D_marker = elprop_local[marker]
        for i in idxs:
            dof_idx = edof0[i]
            Ke = planqe(ex[i, :], ey[i, :], ep_marker, D_marker)

            start = i * block_size
            end = start + block_size
            rows[start:end] = dof_idx[row_pattern]
            cols[start:end] = dof_idx[col_pattern]
            data[start:end] = np.ravel(Ke)

    K = coo_matrix((data, (rows, cols)), shape=(nDofs, nDofs)).tocsr()
    timings["assembly"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    bc = np.array([], "i")
    bcVal = np.array([], float)
    bc, bcVal = cfu.applybc(bdofs, bc, bcVal, mark_fixed, 0.0)

    f = np.zeros((nDofs, 1))
    cfu.applyforcetotal(bdofs, f, mark_load, value=-10e5, dimension=2)

    a, r = cfc.spsolveq(K, f, bc, bcVal)
    timings["solve"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    ed = cfc.extract_eldisp(edof, a)
    von_mises = np.zeros(n_elements)
    planqs = cfc.planqs

    for marker, idxs in marker_groups.items():
        ep_marker, D_marker = elprop_local[marker]
        for i in idxs:
            es, et = planqs(ex[i, :], ey[i, :], ep_marker, D_marker, ed[i, :])
            s0, s1, s2 = es[0], es[1], es[2]
            von_mises[i] = math.sqrt(s0 * s0 - s0 * s1 + s1 * s1 + 3.0 * s2 * s2)
    timings["postprocess"] = time.perf_counter() - t0

    return {
        "n_dofs": nDofs,
        "n_elements": n_elements,
        "timings": timings,
    }

def run_case(el_size_factor):
    prepared = prepare_case(el_size_factor)
    result = compute_case(prepared)
    result["timings"]["mesh"] = prepared["mesh_time"]
    return result

def main():
    for h in MESH_SIZES:
        results = []

        if REUSE_MESH_IN_REPEATS:
            prepared = prepare_case(h)
            for _ in range(PROFILE_REPEATS):
                current = compute_case(prepared)
                current["timings"]["mesh"] = 0.0
                results.append(current)
            mesh_once_time = prepared["mesh_time"]
        else:
            for _ in range(PROFILE_REPEATS):
                results.append(run_case(h))
            mesh_once_time = None

        n_dofs = results[0]["n_dofs"]
        n_elements = results[0]["n_elements"]

        avg = {}
        for key in results[0]["timings"]:
            avg[key] = sum(r["timings"][key] for r in results) / len(results)

        if PRINT_SUMMARY:
            print(f"\nMesh size factor: {h}")
            print(f"Elements: {n_elements}")
            print(f"DOFs:     {n_dofs}")
            if mesh_once_time is not None:
                print(f"mesh_once   : {mesh_once_time:.4f} s")
            for key, value in avg.items():
                print(f"{key:12s}: {value:.4f} s")

if __name__ == "__main__":
    main()