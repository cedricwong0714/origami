"""Real-number verification of Stream 1 math engines (one-off audit script)."""

from __future__ import annotations

import warnings

import numpy as np

from src.core.calcium_kinetics import (
    CAM_CA_EC50_M,
    CAM_CA_HILL_N,
    CAM_M13_KD_CA_SAT_M,
    cam_activation,
    recruitment_occupancy,
)
from src.core.clasp_assembly import (
    CLASPParameters,
    predict_luminescence,
    simulate_assembly,
)
from src.core.ctpr_geometry import (
    CTPR_RADIUS_NM,
    CTPR_RISE_NM,
    CTPR_TWIST_DEG,
    PERSISTENCE_LENGTH_NM,
    generate_scaffold_geometry,
    wlc_mean_square_end_to_end,
)
from src.core.schema import MechanismType, ScaffoldSpec
from src.ode_model.solver import run_system_simulation

OK = True


def check(label, cond, detail=""):
    global OK
    status = "PASS" if cond else "FAIL"
    if not cond:
        OK = False
    print(f"  [{status}] {label} {detail}")


print("=" * 60)
print("1. CTPR GEOMETRY")
print("=" * 60)
print(f"Constants: rise={CTPR_RISE_NM} nm twist={CTPR_TWIST_DEG} deg "
      f"radius={CTPR_RADIUS_NM} nm Lp={PERSISTENCE_LENGTH_NM} nm")
g = generate_scaffold_geometry(ScaffoldSpec(scaffold_id="CTPR5", repeat_count=5, docking_positions=[1, 3]))
check("CTPR5 length == 5*1.1 = 5.5", abs(g.total_length_nm - 5.5) < 1e-9, f"({g.total_length_nm})")
check("CTPR5 is rigid (<=15 nm)", g.is_rigid)
d = g.get_inter_site_distance_nm(0, 1)
print(f"  site1 pos={tuple(round(x, 4) for x in g.docking_sites[0].position_nm)}")
print(f"  site3 pos={tuple(round(x, 4) for x in g.docking_sites[1].position_nm)}")
check("inter-site distance finite and >0", np.isfinite(d) and d > 0, f"({d:.4f} nm)")
sig = g.get_inter_site_distance_uncertainty_nm(0, 1)
check("distance uncertainty > 0", sig > 0, f"({sig:.4f} nm)")

with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    g20 = generate_scaffold_geometry(ScaffoldSpec(scaffold_id="CTPR20", repeat_count=20, docking_positions=[1, 20]))
check("CTPR20 NOT rigid (22>15)", not g20.is_rigid)
check("CTPR20 WLC warning emitted", any("persistence" in str(x.message) for x in w))
print(f"  WLC end-to-end RMS={g20.wlc_end_to_end_rms_nm:.3f} nm vs rigid 22 nm")
check("WLC RMS < rigid length for long scaffold", g20.wlc_end_to_end_rms_nm < 22.0)

print("WLC limits:")
ms_rigid = wlc_mean_square_end_to_end(1.0, 100.0)
ms_flex = wlc_mean_square_end_to_end(100.0, 1.0)
check("Rigid limit <R2> close to L2", abs(ms_rigid - 1.0) / 1.0 < 0.05, f"({ms_rigid:.4f})")
check("Flexible limit <R2> close to 2*Lp*L", abs(ms_flex - 200.0) / 200.0 < 0.05, f"({ms_flex:.2f})")

print()
print("=" * 60)
print("2. CaM HILL + RECRUITMENT OCCUPANCY")
print("=" * 60)
print(f"Invariants: Kd(Ca-sat)={CAM_M13_KD_CA_SAT_M} M, Hill n={CAM_CA_HILL_N}, EC50={CAM_CA_EC50_M} M")
f_half = cam_activation(CAM_CA_EC50_M)
check("f_cam(EC50) == 0.5", abs(f_half - 0.5) < 1e-9, f"({f_half:.6f})")
ca = np.logspace(-9, -4, 13)
f = [cam_activation(float(c)) for c in ca]
check("monotonic increasing", all(f[i] <= f[i + 1] + 1e-12 for i in range(len(f) - 1)))
check("low Ca ~ 0", f[0] < 0.01, f"({f[0]:.2e})")
check("high Ca ~ 1", f[-1] > 0.99, f"({f[-1]:.4f})")
occ = recruitment_occupancy(1e-5)
check("occupancy in [0,1]", 0 <= occ.occupancy_fraction <= 1, f"({occ.occupancy_fraction:.4f})")
# Quadratic binding with cam=m13=1uM, Kd=0.1uM saturates at 0.7298 (ligand
# depletion). That is the physically correct plateau, not a bug.
occ_hi = recruitment_occupancy(1e-4, cam_total_M=1e-4, m13_total_M=1e-6)
check("excess CaM -> near-saturated occupancy", occ_hi.occupancy_fraction > 0.95,
      f"({occ_hi.occupancy_fraction:.4f})")
occ_low = recruitment_occupancy(1e-9)
check("low Ca -> unbound", occ_low.assembly_regime == "unbound", f"({occ_low.assembly_regime})")

print()
print("=" * 60)
print("3. CLASP ASSEMBLY ODE (Docs-6 exact)")
print("=" * 60)
p = CLASPParameters()
check("Hill n invariant n=4", p.n_h == 4.0)
check("K_C = 2e-6 M", p.k_c_M == 2e-6)
E_T = M_T = 1e-6
t, concs = simulate_assembly(calcium_M=1e-5, E_T=E_T, M_T=M_T, t_end=3600.0, num_points=100)
inv = concs["B"] + concs["L"]
check("B,L >= 0", np.all(concs["B"] >= -1e-15) and np.all(concs["L"] >= -1e-15))
check("B+L <= min(E_T,M_T)", np.all(inv <= min(E_T, M_T) + 1e-12), f"(max={inv.max():.3e})")
check("L non-decreasing (locking)", np.all(np.diff(concs["L"]) >= -1e-15))
R = concs["R"]
check("R >= r0 background", np.all(R >= p.r0 - 1e-9), f"(min R={R.min():.2f}, r0={p.r0})")
print(f"  endpoint B={concs['B'][-1]:.3e} L={concs['L'][-1]:.3e} R={R[-1]:.2f}")

ca_series = np.array([1e-8, 1e-7, 1e-6, 1e-5, 1e-4])
Rser = predict_luminescence(ca_series, t_end=1800.0)
check("dose-response non-decreasing", np.all(np.diff(Rser) >= -1e-6), f"(R={np.round(Rser,1)})")

print()
print("=" * 60)
print("4. INTERMEDIATE-TRANSFER (OtsA/OtsB) MASS BALANCE")
print("=" * 60)
t, concs = run_system_simulation(
    {"S": 1.0, "E": 0.1, "E2": 0.1, "ES": 0.0, "P": 0.0},
    mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
    num_points=100,
)
inventory = np.asarray(concs["S"]) + np.asarray(concs["ES"]) + np.asarray(concs["P"])
check("S+ES+P conserved", np.allclose(inventory, inventory[0], atol=1e-5),
      f"(drift={inventory[-1]-inventory[0]:.2e})")
check("P monotonic increasing", np.all(np.diff(concs["P"]) >= -1e-12))
check("S monotonic decreasing", np.all(np.diff(concs["S"]) <= 1e-12))
print(f"  final: S={concs['S'][-1]:.4f} P={concs['P'][-1]:.4f}")

print()
print("=" * 60)
print("RESULT:", "ALL PASS" if OK else "FAILURES PRESENT")
print("=" * 60)
raise SystemExit(0 if OK else 1)
