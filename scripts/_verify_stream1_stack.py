"""Real-number verification of Stream 1 ML/statistical engines."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from src.analysis.sensitivity import most_sensitive_parameter
from src.calibration.fisher import FisherInformationDesigner
from src.calibration.fit import fit_model_with_identifiability_check
from src.experiment_design.bayesian_selector import BayesianExperimentSelector
from src.gp_model.residual_gp import ResidualGP
from src.gp_model.stacked_ensemble import StackedEnsemblePredictor
from src.predictions.freeze import compare_to_frozen, freeze_prediction, verify_frozen_checksum

OK = True


def check(label, cond, detail=""):
    global OK
    s = "PASS" if cond else "FAIL"
    if not cond:
        OK = False
    print(f"  [{s}] {label} {detail}")


print("=" * 60)
print("5. ResidualGP (Matern) on synthetic dose-response")
print("=" * 60)
ens = StackedEnsemblePredictor()
ca = np.logspace(-7, -4, 6)
X = np.column_stack([ca, np.full(6, 1e-6), np.full(6, 1e-6)])
y_mech = np.array([ens.mechanistic_predict(float(c)) for c in ca])
y_obs = y_mech * 1.12 + 5.0  # systematic offset
st = ens.fit_observations(X, y_obs, y_mechanistic=y_mech, try_xgb=False)
check("GP fitted", st["gp_fitted"])
check("XGB skipped (<15)", "skipped" in str(st["xgb_status"]).lower() or "inactive" in str(st["xgb_status"]))
pred = ens.predict(calcium_M=1e-5)
check("corrected prediction finite", np.isfinite(pred.predicted_value))
check("95% CI ordered", pred.uncertainty_95_lower <= pred.predicted_value <= pred.uncertainty_95_upper)
check("GP moved prediction toward obs", abs(pred.gp_correction) > 1e-6, f"(corr={pred.gp_correction:.2f})")
print(f"  mech={pred.mechanistic_prediction:.1f} corrected={pred.predicted_value:.1f} tier={pred.confidence_tier}")

print()
print("=" * 60)
print("6. Fisher information + identifiability (recover k_off,k_lock)")
print("=" * 60)
from src.core.clasp_assembly import CLASPParameters, simulate_assembly


def model_bl(theta, conditions):
    # theta=[k_off, k_lock]; conditions rows = [calcium_M, t_end]
    out = []
    for row in conditions:
        ca, tend = float(row[0]), float(row[1])
        p = CLASPParameters(k_off=theta[0], k_lock=theta[1])
        _, c = simulate_assembly(ca, params=p, E_T=1e-6, M_T=1e-6, t_end=tend, num_points=40)
        out.append(c["B"][-1])  # use reversibly-bound B (dynamic), not saturated L
    return np.asarray(out)


conds = np.array([[1e-6, 60.0], [2e-6, 120.0], [5e-6, 180.0], [8e-6, 240.0], [1e-5, 300.0]])
true = np.array([0.01, 0.003])
y_true = model_bl(true, conds)
fit = fit_model_with_identifiability_check(
    model_bl, ["k_off", "k_lock"], theta0=np.array([0.02, 0.005]),
    conditions=conds, observations=y_true,
    bounds=(np.array([1e-4, 1e-4]), np.array([0.1, 0.1])),
    noise_variance=1e-14,
)
print(f"  fitted k_off={fit.fitted_values['k_off']:.5f} (true 0.01), k_lock={fit.fitted_values['k_lock']:.5f} (true 0.003)")
check("fit converged", fit.success)
check("k_off recovered within 30%", abs(fit.fitted_values["k_off"] - 0.01) / 0.01 < 0.30)
check("k_lock recovered within 30%", abs(fit.fitted_values["k_lock"] - 0.003) / 0.003 < 0.30)
# Note: on a *saturated* toy the fitter correctly flags non-identifiability;
# here conditions are dynamic so both params should be recoverable.

print()
print("=" * 60)
print("7. Bayesian EIG + Sobol sensitivity")
print("=" * 60)
gp = ResidualGP()
Xg = np.linspace(0, 1, 8).reshape(-1, 1)
ym = np.sin(2 * np.pi * Xg[:, 0])
yo = ym + 0.05 * np.random.default_rng(3).normal(size=8)
gp.fit(Xg, yo, ym)
sel = BayesianExperimentSelector(gp)
recs = sel.recommend(Xg, ym, objective="information_gain", n_recommendations=3)
check("EIG returns 3 ranked recs", len(recs) == 3 and recs[0].rank == 1)
check("EIG scores non-increasing by rank", recs[0].acquisition_score >= recs[1].acquisition_score)

def toy(theta):
    return 10.0 * theta[0] + 0.1 * theta[1]
best, scores = most_sensitive_parameter(toy, ["a", "b"], [(0.0, 1.0), (0.0, 1.0)], n_samples=96)
check("Sobol identifies dominant param 'a'", best == "a", f"(S_a={scores['a']:.3f}, S_b={scores['b']:.3f})")

print()
print("=" * 60)
print("8. Freeze / compare (prospective prediction)")
print("=" * 60)
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    fp = freeze_prediction(
        "audit_freeze_v1",
        design_spec={"E_T": 1e-6},
        predictions={"opt": {"predicted_value": 0.70, "uncertainty_95_lower": 0.5,
                              "uncertainty_95_upper": 0.9, "confidence_tier": "hypothesis_only"}},
        model_version="1.0.0",
        output_dir=td,
    )
    check("frozen checksum valid", verify_frozen_checksum(fp))
    cp = compare_to_frozen(fp, {"opt": 0.72}, comparison_id="c1", output_dir=td)
    payload = json.loads(cp.read_text())
    check("within 95% CI detected", payload["comparisons"]["opt"]["within_95ci"] is True)

print()
print("=" * 60)
print("RESULT:", "ALL PASS" if OK else "FAILURES PRESENT")
print("=" * 60)
raise SystemExit(0 if OK else 1)
