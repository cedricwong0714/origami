"""ORIGAMI / CLASP design engine — geometry, steric probability, residual GP, BO."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from origami.engine import ClaspDesignEngine, Observation
from origami.mechanisms.intermediate_transfer import simulate_from_ceff
from origami.physical.recruitment import recruitment_occupancy
from origami.physical.steric import payload_center
from origami.priors import CAM_M13_KD_M, all_priors

st.set_page_config(page_title="ORIGAMI CLASP engine", layout="wide")
st.title("ORIGAMI — CLASP proximity design engine")
st.warning(
    "Structural numbers are **literature placeholders**, not this project's wet-lab data. "
    "The Gaussian process only updates from observations you enter. "
    "Those entries are **user-entered** until real assays are imported."
)

if "observations" not in st.session_state:
    st.session_state.observations = []

with st.sidebar:
    st.header("Scaffold library")
    n_min, n_max = st.slider("CTPR repeat range", 3, 24, (4, 18))
    r1 = st.number_input("Payload A radius (Å)", 5.0, 40.0, 22.0, 1.0)
    r2 = st.number_input("Payload B radius (Å)", 5.0, 40.0, 22.0, 1.0)
    n_inspect = st.slider("Inspect this n", n_min, n_max, min(8, n_max))
    acq = st.selectbox("Acquisition", ["ucb", "entropy", "ei"], format_func=lambda x: {
        "ucb": "UCB (exploit + explore)",
        "entropy": "Posterior entropy (information)",
        "ei": "Expected improvement",
    }[x])
    st.header("Add an observation")
    obs_n = st.number_input("Measured n_repeats", n_min, n_max, n_min)
    obs_y = st.number_input("Observed relative output y", 0.0, 10.0, 0.5, 0.05)
    if st.button("Record user-entered observation"):
        st.session_state.observations.append(
            Observation(n_repeats=int(obs_n), y=float(obs_y), source="user_entered")
        )
    if st.button("Clear observations"):
        st.session_state.observations = []

eng = ClaspDesignEngine(payload_radii_A=[float(r1), float(r2)], n_min=int(n_min), n_max=int(n_max), acquisition=acq)
for obs in st.session_state.observations:
    eng.add_observation(obs)
result = eng.run()
rep = result.reports[n_inspect]
nxt = result.next_experiment

c1, c2, c3, c4 = st.columns(4)
c1.metric("Inspect n", n_inspect)
c2.metric("P(any steric instability)", f"{rep.steric.p_any_instability:.3f}")
c3.metric("Physics score", f"{rep.physics_score:.3f}")
c4.metric("Next assay n", nxt.n_repeats)

st.caption(
    f"Evidence level: **{result.evidence_level}**. "
    f"Next experiment via **{nxt.acquisition_name}**. {nxt.reason}"
)

tab_geo, tab_ai, tab_kin, tab_priors = st.tabs(
    ["Geometry & steric", "GP + active learning", "ODE + Damköhler", "Priors"]
)

with tab_geo:
    coords = rep.geometry.coordinates
    fig = go.Figure()
    fig.add_trace(
        go.Scatter3d(
            x=coords[:, 0],
            y=coords[:, 1],
            z=coords[:, 2],
            mode="lines+markers",
            name="CTPR docking sites",
            marker=dict(size=4),
        )
    )
    payload_xyz = np.stack(
        [
            payload_center(rep.geometry.site(i), r)
            for i, r in zip(rep.payload_indices, [float(r1), float(r2)])
        ],
        axis=0,
    )
    fig.add_trace(
        go.Scatter3d(
            x=payload_xyz[:, 0],
            y=payload_xyz[:, 1],
            z=payload_xyz[:, 2],
            mode="markers",
            name="payload centres",
            marker=dict(size=12, color="crimson"),
        )
    )
    fig.update_layout(
        height=480,
        scene=dict(xaxis_title="x (Å)", yaxis_title="y (Å)", zaxis_title="z (Å)", aspectmode="data"),
        margin=dict(l=0, r=0, t=30, b=0),
        title=f"SE(3) superhelix, n={n_inspect} (not a linear ruler)",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Pairwise clashes")
    if rep.steric.pairs:
        st.dataframe(
            {
                "i": [p.i for p in rep.steric.pairs],
                "j": [p.j for p in rep.steric.pairs],
                "distance_Å": [round(p.distance_A, 2) for p in rep.steric.pairs],
                "contact_Å": [round(p.contact_A, 2) for p in rep.steric.pairs],
                "P(clash)": [round(p.p_clash, 4) for p in rep.steric.pairs],
            },
            use_container_width=True,
        )
    st.write("C_eff (Gaussian chain, molar):")
    st.json(
        {
            f"{i}-{j}": {"r_A": round(ce.r_A, 2), "C_eff_M": ce.C_eff_M, "sigma_A": ce.sigma_A}
            for (i, j), ce in rep.ceff.items()
        }
    )
    for w in rep.warnings:
        st.info(w)

with tab_ai:
    n = np.array(result.candidates)
    lo, hi = result.posterior.interval_95()
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=n, y=result.physics_scores, name="physics score S(n)", mode="lines+markers"))
    fig2.add_trace(go.Scatter(x=n, y=result.posterior.mean, name="GP posterior mean", mode="lines"))
    fig2.add_trace(
        go.Scatter(
            x=list(n) + list(n[::-1]),
            y=list(hi) + list(lo[::-1]),
            fill="toself",
            name="95% interval",
            line=dict(width=0),
            opacity=0.25,
        )
    )
    if result.observations:
        fig2.add_trace(
            go.Scatter(
                x=[o.n_repeats for o in result.observations],
                y=[o.y for o in result.observations],
                mode="markers",
                name="observations",
                marker=dict(size=12, color="black", symbol="x"),
            )
        )
    fig2.add_vline(x=nxt.n_repeats, line_dash="dash", annotation_text="next assay")
    fig2.update_layout(
        height=460,
        xaxis_title="CTPR repeats n",
        yaxis_title="relative output / score",
        title="Residual GP (Matérn-5/2, Cholesky) + discrete BO",
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.write(
        f"Affine physics map: y ≈ {result.posterior.alpha:.3f}·S + {result.posterior.beta:.3f} + r(n). "
        f"Kernel lengthscale={result.posterior.hyperparameters.lengthscale:.3f}, "
        f"variance={result.posterior.hyperparameters.variance:.3f}, "
        f"noise={result.posterior.hyperparameters.noise:.3f}."
    )
    if not result.observations:
        st.info("No observations yet: the GP posterior equals the physics mean plus a prior uncertainty band. Add points to start active learning.")

with tab_kin:
    st.caption(
        "Recruitment uses the published CaM–M13 peptide Kd only. "
        "Capture rates are whatever you type. Nothing here is this team's wet lab."
    )
    c_free_nM = st.number_input("Free payload (nM)", 0.0, 1e6, 10.0, 1.0)
    kon = st.number_input("k_on (M⁻¹ s⁻¹), 0 = steady state only", 0.0, 1e9, 0.0, 1e5, format="%.1f")
    k_escape = st.number_input("k_escape (s⁻¹)", 1e-4, 1e4, 1.0, format="%.4f")
    spec = st.number_input("k_cat/K_m (M⁻¹ s⁻¹)", 0.0, 1e9, 1e5, format="%.1f")
    v_prod = st.number_input("v_prod (M/s)", 0.0, 1.0, 1e-6, format="%.2e")
    occ = recruitment_occupancy(
        c_free_M=c_free_nM * 1e-9,
        kon_per_M_s=None if kon == 0 else float(kon),
    )
    pair = next(iter(rep.ceff.values())) if rep.ceff else None
    st.metric(
        "Steady occupancy θ",
        f"{occ.theta_ss:.3f}",
        help=f"95% Kd interval [{occ.theta_95_lower:.3f}, {occ.theta_95_upper:.3f}]",
    )
    st.write(
        f"Kd = {CAM_M13_KD_M.value*1e9:.2f} ± {CAM_M13_KD_M.sigma*1e9:.2f} nM "
        f"(DOI 10.1021/bi060857u). Tier: {occ.confidence_tier}."
    )
    if pair is not None:
        xfer = simulate_from_ceff(float(v_prod), float(k_escape), float(spec), pair.C_eff_M)
        st.write(
            f"C_eff = {pair.C_eff_M:.3e} M. Da = {xfer.da:.3e}. "
            f"P(capture) = {xfer.p_capture:.3f}. "
            f"Product flux = {xfer.product_flux_M_per_s:.3e} M/s. "
            f"Tier: {xfer.confidence_tier}."
        )
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=xfer.time_s, y=xfer.intermediate_M, name="intermediate I(t)"))
        fig3.add_trace(go.Scatter(x=xfer.time_s, y=xfer.product_M, name="product P(t)"))
        fig3.update_layout(height=360, xaxis_title="t (s)", yaxis_title="M", title="Damköhler-reduced ODE")
        st.plotly_chart(fig3, use_container_width=True)
        for w in xfer.warnings:
            st.info(w)
    for w in occ.warnings:
        st.info(w)

with tab_priors:
    st.markdown("Every constant is tagged. **calibrated=False** until lab data replace it.")
    st.table(
        {
            "name": [p.name for p in all_priors()],
            "value": [p.value for p in all_priors()],
            "units": [p.units for p in all_priors()],
            "sigma": [p.sigma for p in all_priors()],
            "provenance": [p.provenance for p in all_priors()],
            "source": [p.source for p in all_priors()],
        }
    )
