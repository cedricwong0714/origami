"""
ORIGAMI Streamlit UI — Explore / Design / Learn.

Run from repo root:
    pip install -e ".[ui]"
    streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import streamlit as st

from src.compiler.expression_vector import ExpressionPlan
from src.core.asset_paths import REPO_ROOT
from src.core.schema import DesignSpec, MechanismType, MoCloPart, ScaffoldSpec
from src.scaffold_optimizer import InteractionClass, optimize_ctpr_spacing
from src.ui.design_mode import DesignMode
from src.ui.explore_mode import ExploreMode
from src.ui.export_utils import (
    interaction_class_to_mechanism,
    passport_json_bytes,
    wiki_markdown_snippet,
)
from src.ui.learn_mode import LearnMode

# Demo MoClo cassette (allowlisted short parts only — no invented ORFs)
_DEMO_PARTS = [
    MoCloPart(
        part_id="Promoter_J23100",
        overhang_5prime="GGAG",
        overhang_3prime="AATG",
        sequence="TTGACAGCTAGCTCAGTCCTAGGTATAATACTAGT",
    ),
    MoCloPart(
        part_id="RBS_B0034",
        overhang_5prime="AATG",
        overhang_3prime="CGCT",
        sequence="AAAGAGGAGAAA",
    ),
]

_MECHANISM_LABELS = {
    MechanismType.INTERMEDIATE_TRANSFER: "Intermediate transfer (trehalose / OtsA–OtsB)",
    MechanismType.TARGET_COMPLEMENTATION: "Target complementation (screening assay POC)",
    MechanismType.REDOX_TRANSFER: "Redox transfer (relative ranking only)",
    MechanismType.COVALENT_CAPTURE: "Covalent capture (SpyTag / SpyCatcher)",
    MechanismType.TRANS_ACTIVATION: "Trans-activation (proximity-induced phosphorylation)",
    MechanismType.PROTEASE_CLEAVAGE: "Protease cleavage (proximity-gated; Tier-3)",
}


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --canvas-bg: #F3EFE9;
          --frame-bg: #EBE4D9;
          --charcoal-txt: #242220;
          --mascot-orange: #FF8000;
          --orange-hover: #D66B00;
          --blue-lively: #266FB1;
          --card-shadow: 0 10px 30px rgba(36, 34, 32, 0.04);
        }
        .stApp {
          background:
            radial-gradient(ellipse 80% 50% at 10% 0%, rgba(255, 128, 0, 0.08), transparent 55%),
            radial-gradient(ellipse 70% 45% at 90% 10%, rgba(38, 111, 177, 0.08), transparent 50%),
            var(--canvas-bg);
          color: var(--charcoal-txt);
        }
        h1, h2, h3 {
          color: var(--charcoal-txt) !important;
          letter-spacing: -0.02em;
        }
        p, label, span, .stMarkdown, .stCaption {
          color: var(--charcoal-txt);
        }
        .origami-banner {
          border-left: 4px solid var(--mascot-orange);
          background: var(--frame-bg);
          box-shadow: var(--card-shadow);
          padding: 0.85rem 1rem;
          margin-bottom: 1rem;
          color: var(--charcoal-txt);
        }
        .origami-refuse {
          border: 1px solid rgba(214, 107, 0, 0.45);
          background: #FFF4E8;
          color: var(--orange-hover);
          padding: 1rem;
          border-radius: 4px;
          box-shadow: var(--card-shadow);
        }
        .origami-ok {
          border: 1px solid rgba(38, 111, 177, 0.35);
          background: #EEF5FB;
          color: var(--charcoal-txt);
          padding: 1rem;
          border-radius: 4px;
          box-shadow: var(--card-shadow);
        }
        div[data-testid="stSidebar"] {
          background: var(--frame-bg);
          border-right: 1px solid rgba(36, 34, 32, 0.08);
        }
        div[data-testid="stSidebar"] * {
          color: var(--charcoal-txt) !important;
        }
        div[data-testid="stSidebar"] .stRadio label {
          color: var(--charcoal-txt) !important;
        }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {
          background-color: var(--mascot-orange) !important;
          border-color: var(--mascot-orange) !important;
          color: #fff !important;
        }
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover {
          background-color: var(--orange-hover) !important;
          border-color: var(--orange-hover) !important;
        }
        .stButton > button:focus,
        .stTextInput input:focus,
        .stSelectbox [data-baseweb="select"] > div:focus-within,
        .stNumberInput input:focus {
          border-color: var(--blue-lively) !important;
          box-shadow: 0 0 0 1px var(--blue-lively) !important;
        }
        div[data-testid="stMetric"] {
          background: var(--frame-bg);
          box-shadow: var(--card-shadow);
          padding: 0.75rem 1rem;
          border-radius: 6px;
        }
        div[data-testid="stExpander"] {
          background: var(--frame-bg);
          box-shadow: var(--card-shadow);
          border-radius: 6px;
        }
        a { color: var(--blue-lively) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _banner() -> None:
    st.markdown(
        """
        <div class="origami-banner">
          <strong>ORIGAMI</strong> — mechanism-aware design for CLASP.
          Predictions show uncertainty and evidence maturity.
          Insufficient evidence is a valid answer. Passing software tests ≠ wet-lab validation.
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_explore() -> None:
    st.header("Explore evidence")
    st.caption("One job: retrieve what is known. Never invent citations or parameters.")

    explorer = ExploreMode()
    keys = explorer.list_available_evidence()
    st.write(f"Local evidence corpus: **{len(keys)}** parameters")
    with st.expander("All parameter keys"):
        st.code("\n".join(keys) if keys else "(empty)")

    pick = st.selectbox(
        "Select a curated parameter",
        options=keys,
        index=keys.index("k_cat_OtsA") if "k_cat_OtsA" in keys else 0,
    )
    custom = st.text_input(
        "Or type a key (including unknown keys to test refusal)",
        value="",
        placeholder="e.g. made_up_kcat",
    )
    parameter_key = custom.strip() or pick
    run = st.button("Ask evidence engine", type="primary")

    if run and parameter_key.strip():
        result = explorer.ask(parameter_key.strip())
        if result["status"] == "INSUFFICIENT_EVIDENCE":
            st.markdown(
                f'<div class="origami-refuse"><strong>Refusal</strong><br/>{result["message"]}</div>',
                unsafe_allow_html=True,
            )
            st.json(result)
        else:
            st.markdown(
                f'<div class="origami-ok"><strong>{result["evidence_class"]}</strong> · '
                f'confidence {result["confidence_score"]:.2f}</div>',
                unsafe_allow_html=True,
            )
            m1, m2, m3 = st.columns(3)
            m1.metric("Value", f"{result['value']}")
            m2.metric("Unit", result["unit"])
            m3.metric("Class", result["evidence_class"])
            if result.get("inference_note"):
                st.info(result["inference_note"])
            st.subheader("Citation")
            st.json(result.get("citation") or {})
            st.subheader("Full record")
            st.json(result)


def _design_prefill() -> dict[str, Any]:
    return st.session_state.get("design_prefill") or {}


def page_design() -> None:
    st.header("Design a CLASP system")
    st.caption("Geometry → mechanism prediction → allowlist / coexpression checks → Design Passport.")

    prefill = _design_prefill()
    if prefill.get("source") == "optimizer":
        st.info(
            f"Pre-filled from CTPR optimizer: **CTPR-{prefill.get('repeat_count')}** · "
            f"docking **{prefill.get('dock_a')}** & **{prefill.get('dock_b')}** · "
            f"Δi* = {prefill.get('optimal_delta_i')} · Φ = {prefill.get('best_score', '—')}"
        )

    default_repeats = int(prefill.get("repeat_count", 5))
    default_dock_a = int(prefill.get("dock_a", 1))
    default_dock_b = int(prefill.get("dock_b", min(3, default_repeats)))
    default_mechanism = prefill.get("mechanism_type", MechanismType.INTERMEDIATE_TRANSFER)
    if isinstance(default_mechanism, str):
        default_mechanism = MechanismType(default_mechanism)
    default_design_id = prefill.get("design_id", "UI_DESIGN_001")

    # Persist docking choices across reruns (changing repeats must not wipe them).
    if prefill.get("source") == "optimizer" and not st.session_state.get(
        "_design_prefill_docks_applied"
    ):
        st.session_state["design_dock_a"] = default_dock_a
        st.session_state["design_dock_b"] = default_dock_b
        st.session_state["design_repeat_count"] = default_repeats
        st.session_state["_design_prefill_docks_applied"] = True
    if "design_dock_a" not in st.session_state:
        st.session_state["design_dock_a"] = default_dock_a
    if "design_dock_b" not in st.session_state:
        st.session_state["design_dock_b"] = default_dock_b
    if "design_repeat_count" not in st.session_state:
        st.session_state["design_repeat_count"] = default_repeats

    mechanism = st.selectbox(
        "Mechanism profile",
        options=list(MechanismType),
        format_func=lambda m: _MECHANISM_LABELS[m],
        index=list(MechanismType).index(default_mechanism),
    )
    chassis = st.selectbox("Chassis", ["E_coli", "cell_free", "B_subtilis"])
    design_id = st.text_input("Design ID", value=default_design_id)

    c1, c2, c3 = st.columns(3)
    with c1:
        repeat_count = st.slider(
            "CTPR repeats",
            2,
            20,
            key="design_repeat_count",
        )
    # Only clamp docks that fall outside the new repeat range — never reset to defaults.
    if st.session_state["design_dock_a"] > repeat_count:
        st.session_state["design_dock_a"] = int(repeat_count)
    if st.session_state["design_dock_b"] > repeat_count:
        st.session_state["design_dock_b"] = int(repeat_count)
    if st.session_state["design_dock_a"] < 1:
        st.session_state["design_dock_a"] = 1
    if st.session_state["design_dock_b"] < 1:
        st.session_state["design_dock_b"] = 1

    with c2:
        dock_a = st.number_input(
            "Docking site A (1-based)",
            min_value=1,
            max_value=int(repeat_count),
            step=1,
            key="design_dock_a",
        )
    with c3:
        dock_b = st.number_input(
            "Docking site B (1-based)",
            min_value=1,
            max_value=int(repeat_count),
            step=1,
            key="design_dock_b",
        )

    payload_default = "OtsA, OtsB"
    if mechanism == MechanismType.TARGET_COMPLEMENTATION:
        payload_default = "recognition, SmBiT"
        operating_default = "target_triggered"
    elif mechanism == MechanismType.COVALENT_CAPTURE:
        payload_default = "SpyTagged_payload"
        operating_default = "locking"
    elif mechanism == MechanismType.REDOX_TRANSFER:
        payload_default = "redox_donor, redox_acceptor"
        operating_default = "reversible"
    elif mechanism == MechanismType.TRANS_ACTIVATION:
        payload_default = "kinase_donor, kinase_acceptor"
        operating_default = "reversible"
    elif mechanism == MechanismType.PROTEASE_CLEAVAGE:
        payload_default = "protease_effector, cleavage_target"
        operating_default = "reversible"
    else:
        operating_default = "reversible"

    payloads_raw = st.text_input("Payload IDs (comma-separated)", value=payload_default)
    operating_mode = st.selectbox(
        "Operating mode",
        ["reversible", "locking", "target_triggered"],
        index=["reversible", "locking", "target_triggered"].index(operating_default),
    )
    ca2_uM = st.slider("Free [Ca²⁺] (µM)", 0.0, 50.0, 10.0, 0.5)
    linker = st.text_input("Linker", value="(GGGGS)3")

    st.subheader("Expression strategy (biosecurity)")
    e1, e2, e3 = st.columns(3)
    with e1:
        scaffold_vector = st.selectbox(
            "Scaffold vector",
            ["vector_pETDuet", "vector_dual_plasmid_set", "pET28a+"],
            index=0,
        )
    with e2:
        payload_vector = st.selectbox(
            "Payload vector",
            ["vector_dual_plasmid_set", "vector_pETDuet", "pET28a+"],
            index=0,
        )
    with e3:
        coex = st.selectbox(
            "Coexpression strategy",
            ["dual_cassette", "dual_plasmid", "operon", "other"],
            index=0,
        )

    if st.button("Run Design Mode", type="primary"):
        payload_ids = [p.strip() for p in payloads_raw.split(",") if p.strip()]
        docks = sorted({int(dock_a), int(dock_b)})
        spec = DesignSpec(
            design_id=design_id,
            chassis=chassis,
            mechanism_type=mechanism,
            scaffold=ScaffoldSpec(
                scaffold_id=f"CTPR{repeat_count}",
                repeat_count=int(repeat_count),
                docking_positions=docks,
                persistence_length_nm=15.0,
            ),
            payload_ids=payload_ids,
            operating_mode=operating_mode,
        )
        plan = ExpressionPlan(
            scaffold_vector_id=scaffold_vector,
            payload_vector_ids=[payload_vector],
            coexpression_strategy=coex,
        )
        with st.spinner("Running shared physical engine + mechanism profile..."):
            result = DesignMode().run(
                spec,
                _DEMO_PARTS,
                expression_plan=plan,
                ca2_free_M=ca2_uM * 1e-6,
                linker_sequence=linker,
            )
        result["design_id"] = design_id
        st.session_state["last_design_result"] = result
        st.session_state["last_design_spec"] = spec
        st.session_state["last_design_id"] = design_id

    result = st.session_state.get("last_design_result")
    if not result:
        return

    design_id = result.get("design_id") or st.session_state.get("last_design_id", "UI_DESIGN_001")
    spec = st.session_state.get("last_design_spec")
    mechanism = (
        spec.mechanism_type
        if spec is not None
        else MechanismType.INTERMEDIATE_TRANSFER
    )

    if result["status"] == "SUCCESS":
        st.success("Design accepted (software checks). Not a wet-lab validation.")
    else:
        st.error("Design rejected — see blocking errors.")
        for err in result.get("errors", []):
            st.write(f"- {err}")

    for w in result.get("warnings", []):
        st.warning(w)

    passport = result.get("passport") or {}
    st.subheader("Proximity Design Passport")
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "Download passport JSON",
            data=passport_json_bytes(result),
            file_name=f"{design_id}_passport.json",
            mime="application/json",
        )
    with dl2:
        st.download_button(
            "Download wiki markdown snippet",
            data=wiki_markdown_snippet(result, spec=spec).encode("utf-8"),
            file_name=f"{design_id}_wiki_snippet.md",
            mime="text/markdown",
        )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Profile", passport.get("mechanism_profile", "—"))
    m2.metric("Evidence maturity", str(passport.get("evidence_maturity", "—"))[:28])
    m3.metric("Biosecurity", passport.get("biosecurity_review_state", "—"))
    m4.metric("Steric OK", str(passport.get("steric_feasible")))
    if passport.get("payload_roles"):
        st.caption(
            "Payload roles: "
            + ", ".join(f"{k}→{v}" for k, v in passport["payload_roles"].items())
        )

    pred = result.get("prediction")
    if pred:
        st.subheader("Prediction (with uncertainty)")
        lo, hi = pred["uncertainty_95ci"]
        st.metric(
            pred["primary_metric_name"],
            f"{pred['primary_metric_value']:.4g} {pred['unit']}",
            help=f"95% CI [{lo:.4g}, {hi:.4g}] — computational/literature tier until calibrated",
        )
        st.caption(f"95% CI: [{lo:.4g}, {hi:.4g}]")
        for a in pred.get("assumptions", []):
            st.write(f"- assumption: {a}")
        for w in pred.get("warnings", []):
            st.write(f"- warning: {w}")

    geo = result.get("geometry") or {}
    if geo:
        st.subheader("Geometry summary")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Length (nm)", f"{geo.get('total_length_nm', 0):.2f}")
        g2.metric("Rigid", str(geo.get("is_rigid")))
        g3.metric("Docking sites", len(geo.get("docking_sites") or []))
        dist = result.get("inter_site_distance_nm")
        dunc = result.get("inter_site_distance_uncertainty_nm")
        if dist is not None:
            g4.metric(
                "Inter-site (nm)",
                f"{dist:.2f}",
                help=(f"1σ uncertainty ≈ {dunc:.3f} nm" if dunc is not None else None),
            )
        if geo.get("wlc_end_to_end_rms_nm") is not None and not geo.get("is_rigid"):
            st.caption(
                f"WLC end-to-end RMS ≈ {geo['wlc_end_to_end_rms_nm']:.2f} nm "
                f"(rigid rod would be {geo.get('total_length_nm', 0):.2f} nm)"
            )
        try:
            import plotly.graph_objects as go

            backbone = geo.get("backbone_coordinates_nm") or []
            if backbone:
                xs = [p[0] for p in backbone]
                ys = [p[2] for p in backbone]
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=xs,
                        y=ys,
                        mode="lines+markers",
                        name="CTPR superhelix (x–z)",
                        line=dict(color="#266FB1"),
                    )
                )
                for site in geo.get("docking_sites") or []:
                    pos = site["position_nm"]
                    fig.add_trace(
                        go.Scatter(
                            x=[pos[0]],
                            y=[pos[2]],
                            mode="markers",
                            name=f"dock r{site['repeat_index']}",
                            marker=dict(size=12, color="#FF8000"),
                        )
                    )
                fig.update_layout(
                    height=360,
                    margin=dict(l=20, r=20, t=30, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(235,228,217,0.65)",
                    font=dict(color="#242220"),
                    xaxis_title="x (nm) — cylindrical screw",
                    yaxis_title="z (nm) — axial rise",
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            st.info(f"Geometry plot unavailable: {exc}")

    adr = result.get("assembly_dose_response")
    if adr:
        st.subheader("CLASP assembly Ca²⁺ dose-response (Stream 1 ODE)")
        st.caption(adr.get("note", ""))
        ec50_M = adr.get("ec50_M")
        hill = adr.get("hill_fit") or {}
        if hill.get("success"):
            h1, h2, h3, h4 = st.columns(4)
            ec50_fit = float(hill["ec50_M"])
            ec_lo, ec_hi = hill["ec50_M_ci95"]
            h1.metric(
                "Hill EC50",
                f"{ec50_fit * 1e6:.3g} µM",
                help="SCALE Stage A phenomenological fit (covariance CI, not wet-lab CI).",
            )
            h2.metric(
                "EC50 95% (fit)",
                f"{ec_lo * 1e6:.3g}–{ec_hi * 1e6:.3g} µM",
            )
            n_fit = float(hill["hill_n"])
            n_lo, n_hi = hill["hill_n_ci95"]
            h3.metric("Hill n", f"{n_fit:.2f}", help=f"fit CI {n_lo:.2f}–{n_hi:.2f}")
            dr = float(hill["dynamic_range"])
            h4.metric("Dynamic range", f"{dr:.2g}×")
            st.caption(
                "Hill EC50 / n / DR summarize the ODE curve. "
                f"CaM priors: EC50={float(adr.get('cam_parameter_ec50_M', 2e-6)) * 1e6:g} µM, "
                f"n={adr.get('cam_parameter_hill_n', 4)}."
            )
        elif ec50_M is not None:
            lo = adr.get("ec50_uncertainty_lower_M")
            hi = adr.get("ec50_uncertainty_upper_M")
            cam_ec50 = adr.get("cam_parameter_ec50_M")
            e1, e2, e3 = st.columns(3)
            e1.metric("Apparent EC50", f"{ec50_M * 1e6:.3g} µM")
            if lo is not None and hi is not None:
                e2.metric("EC50 grid bracket", f"{lo * 1e6:.3g}–{hi * 1e6:.3g} µM")
            if cam_ec50 is not None:
                e3.metric("CaM parameter EC50", f"{cam_ec50 * 1e6:.3g} µM")
            if adr.get("ec50_note"):
                st.caption(adr["ec50_note"])
        try:
            import plotly.graph_objects as go

            ca_uM_axis = [c * 1e6 for c in adr["calcium_M"]]
            x_min = float(adr.get("calcium_uM_min", min(ca_uM_axis)))
            x_max = float(adr.get("calcium_uM_max", max(ca_uM_axis)))
            fig2 = go.Figure()
            fig2.add_trace(
                go.Scatter(
                    x=ca_uM_axis,
                    y=adr["luminescence_RLU"],
                    mode="lines",
                    name="ODE predicted RLU",
                    line=dict(color="#FF8000", width=2.5),
                )
            )
            if hill.get("success"):
                from src.calibration.dose_response_metrics import hill_response

                ca_M = np.asarray(adr["calcium_M"], dtype=float)
                y_hill = hill_response(
                    ca_M,
                    float(hill["r0"]),
                    float(hill["r_amp"]),
                    float(hill["ec50_M"]),
                    float(hill["hill_n"]),
                )
                fig2.add_trace(
                    go.Scatter(
                        x=ca_uM_axis,
                        y=y_hill.tolist(),
                        mode="lines",
                        name="Hill fit",
                        line=dict(color="#1B7F4E", width=2, dash="dash"),
                    )
                )
            op_uM = float(adr["operating_ca2_M"]) * 1e6
            if x_min <= op_uM <= x_max:
                fig2.add_vline(
                    x=op_uM,
                    line_dash="dash",
                    line_color="#266FB1",
                    annotation_text=f"operating {op_uM:.2g} µM",
                )
            mark_ec50 = float(hill["ec50_M"]) if hill.get("success") else ec50_M
            if mark_ec50 is not None:
                ec50_uM = float(mark_ec50) * 1e6
                if x_min <= ec50_uM <= x_max:
                    fig2.add_vline(
                        x=ec50_uM,
                        line_dash="dot",
                        line_color="#1B7F4E",
                        annotation_text=f"EC50 {ec50_uM:.3g} µM",
                    )
            fig2.update_layout(
                height=340,
                width=640,
                autosize=False,
                margin=dict(l=20, r=20, t=30, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(235,228,217,0.65)",
                font=dict(color="#242220"),
                xaxis_title="free Ca²⁺ (µM)",
                yaxis_title="predicted luminescence (RLU)",
                xaxis_type="log",
                xaxis_range=[np.log10(x_min), np.log10(x_max)],
            )
            st.plotly_chart(fig2, use_container_width=False)
        except Exception as exc:
            st.info(f"Dose-response plot unavailable: {exc}")

        with st.expander("AES converter (SCALE Stage A — needs your calibration)"):
            st.caption(
                "AES = absolute assembled NanoLuc. Requires measured NanoLuc slope "
                "and cell/OD factors — ORIGAMI will not invent them."
            )
            a1, a2, a3 = st.columns(3)
            with a1:
                rlu_sat = st.number_input(
                    "RLU (e.g. saturating Ca²⁺)",
                    value=float(max(adr["luminescence_RLU"])),
                    format="%.4g",
                )
                rlu_blank = st.number_input("Blank RLU", value=0.0, format="%.4g")
            with a2:
                rlu_per_fmol = st.number_input(
                    "RLU per fmol NanoLuc (curve slope)",
                    value=0.0,
                    help="Leave 0 if not measured yet.",
                    format="%.6g",
                )
                od600 = st.number_input("OD600", value=0.0, format="%.4g")
            with a3:
                cells_per_od = st.number_input(
                    "cells per OD·mL",
                    value=0.0,
                    help="From OD→cells calibration.",
                    format="%.6g",
                )
                vol_ml = st.number_input("Sample volume (mL)", value=1.0, format="%.4g")
            if st.button("Compute AES from calibration"):
                from src.calibration.dose_response_metrics import compute_aes

                aes = compute_aes(
                    float(rlu_sat),
                    float(rlu_blank),
                    rlu_per_fmol=float(rlu_per_fmol) if rlu_per_fmol > 0 else None,
                    od600=float(od600) if od600 > 0 else None,
                    cells_per_od_ml=float(cells_per_od) if cells_per_od > 0 else None,
                    sample_volume_ml=float(vol_ml),
                    calibration_sources=["user-supplied Design Mode calibration"],
                )
                if aes.aes_molecules_per_cell is not None:
                    st.metric("AES", f"{aes.aes_molecules_per_cell:.4g} molecules/cell")
                elif aes.fmol_nanoluc is not None:
                    st.metric("Net NanoLuc", f"{aes.fmol_nanoluc:.4g} fmol")
                    for w in aes.warnings:
                        st.warning(w)
                else:
                    for w in aes.warnings:
                        st.warning(w)

    st.subheader("Freeze prospective prediction (Docs §1.6)")
    st.caption(
        "Writes a checksummed prediction file before wet-lab comparison. "
        "Immutable once written — use a new prediction_id to revise."
    )
    freeze_id = st.text_input("Prediction ID", value=f"{design_id}_assembly_v1")
    if st.button("Freeze this Design prediction"):
        try:
            from src.predictions.freeze import freeze_prediction

            pred_block: dict[str, Any] = {}
            if result.get("prediction"):
                p = result["prediction"]
                lo, hi = p["uncertainty_95ci"]
                pred_block["primary"] = {
                    "predicted_value": p["primary_metric_value"],
                    "uncertainty_95_lower": lo,
                    "uncertainty_95_upper": hi,
                    "confidence_tier": "hypothesis_only",
                    "units": p.get("unit", ""),
                }
            if adr:
                for ca, rlu in zip(adr["calcium_M"], adr["luminescence_RLU"]):
                    pred_block[f"ca_{ca * 1e6:g}uM"] = {
                        "predicted_value": rlu,
                        "uncertainty_95_lower": rlu * 0.7,
                        "uncertainty_95_upper": rlu * 1.3,
                        "confidence_tier": "hypothesis_only",
                        "units": "RLU",
                    }
            path = freeze_prediction(
                freeze_id.strip() or f"{design_id}_v1",
                design_spec={
                    "design_id": design_id,
                    "mechanism": mechanism.value,
                    "scaffold": geo,
                },
                predictions=pred_block,
                model_version=str(passport.get("profile_version", "unknown")),
                parameter_sources=[
                    "models/kinetic_models/",
                    "src/core/clasp_assembly.py",
                ],
                assumptions=[
                    "Frozen before wet-lab comparison",
                    "Assembly dose-response is literature-parameterized",
                ],
            )
            st.success(f"Frozen at `{path}`")
        except Exception as exc:
            st.error(f"Freeze failed: {exc}")

    st.subheader("Compare observations to a frozen prediction")
    st.caption(
        "Docs §1.6: load a frozen file, enter observed values for matching keys "
        "(e.g. primary or ca_10uM), write a comparison record. Does not overwrite Tier-1 data."
    )
    from src.core.asset_paths import FROZEN_PREDICTIONS_DIR

    frozen_files = sorted(FROZEN_PREDICTIONS_DIR.glob("*.json"))
    frozen_names = [p.name for p in frozen_files if p.name != "README.md"]
    if not frozen_names:
        st.info("No frozen predictions yet — freeze one above first.")
    else:
        pick = st.selectbox("Frozen prediction file", frozen_names)
        obs_json = st.text_area(
            "Observations JSON (key → observed float)",
            value='{"primary": 0.5}',
            height=100,
        )
        cmp_id = st.text_input(
            "Comparison ID",
            value=f"{Path(pick).stem}_cmp1",
        )
        if st.button("Write comparison"):
            try:
                from src.predictions.freeze import compare_to_frozen

                observations = json.loads(obs_json)
                if not isinstance(observations, dict) or not observations:
                    raise ValueError("Observations must be a non-empty JSON object")
                out = compare_to_frozen(
                    FROZEN_PREDICTIONS_DIR / pick,
                    {str(k): float(v) for k, v in observations.items()},
                    comparison_id=cmp_id.strip() or f"{Path(pick).stem}_cmp",
                )
                st.success(f"Comparison written to `{out}`")
                st.json(json.loads(out.read_text(encoding="utf-8"))["comparisons"])
            except Exception as exc:
                st.error(f"Compare failed: {exc}")

    with st.expander("Full passport JSON"):
        st.code(json.dumps(passport, indent=2, default=str))
    with st.expander("Required controls & measurements"):
        st.json(passport.get("required_controls"))
        st.write(passport.get("required_measurements"))


def page_learn() -> None:
    st.header("Learn from data")
    st.caption(
        "Compare mechanistic ODE baseline with observations; recommend the next informative measurement. "
        "GP correction is a residual model — not proof of a molecular mechanism. "
        "Tier-1 uploads need the CSV + metadata sidecar from `data/stage1_ingestion/templates/`."
    )

    mechanism = st.selectbox(
        "Mechanism profile",
        options=list(MechanismType),
        format_func=lambda m: _MECHANISM_LABELS[m],
        key="learn_mech",
    )
    strategy = st.selectbox(
        "Acquisition strategy",
        ["UCB", "EI", "information_gain"],
        help="information_gain (EIG) maximizes learning for model calibration",
    )
    n_points = st.slider("Time points", 10, 100, 40)

    source = st.radio(
        "Observation source",
        [
            "Synthetic demo curve (labeled fixture)",
            "Upload Learn package (CSV + metadata JSON)",
            "Synthetic Ca²⁺ luminescence (stacked ensemble)",
        ],
        horizontal=True,
    )

    experimental = None
    experimental_time = None
    data_class: str | None = None
    package_warnings: list[str] = []
    stacked_result: dict[str, Any] | None = None

    if source.startswith("Synthetic demo"):
        st.warning(
            "Synthetic fixture for UI demo only — not Tier-1 experimental data. "
            "Do not put these numbers on the wiki as measurements."
        )
        amp = st.slider("Synthetic amplitude", 0.1, 1.5, 0.8)
        rate = st.slider("Synthetic rate", 0.01, 0.2, 0.04)
        experimental_time = np.linspace(0.0, 100.0, n_points)
        experimental = amp * (1.0 - np.exp(-rate * experimental_time))
        data_class = "synthetic_fixture"
        st.line_chart({"synthetic_product": experimental})
    elif source.startswith("Synthetic Ca"):
        st.warning(
            "Synthetic Ca²⁺ luminescence for stacked-ensemble demo only — not Tier-1 data."
        )
        from src.core.clasp_assembly import CLASPParameters, predict_luminescence
        from src.gp_model.stacked_ensemble import StackedEnsemblePredictor

        ca_uM = np.logspace(-1, 1.5, 8)  # 0.1–~30 µM
        ca_M = ca_uM * 1e-6
        params = CLASPParameters()
        y_mech = predict_luminescence(ca_M, params)
        # Synthetic residual bias + noise (demo)
        rng = np.random.default_rng(0)
        y_obs = y_mech * 1.08 + rng.normal(0.0, 0.02 * np.max(y_mech), size=len(y_mech))
        X = np.column_stack([ca_M, np.full_like(ca_M, 1e-6), np.full_like(ca_M, 1e-6)])
        ens = StackedEnsemblePredictor(params=params)
        fit_info = ens.fit_observations(X, y_obs, y_mechanistic=y_mech, try_xgb=True)
        preds = [ens.predict(float(c)).model_dump() for c in ca_M]
        stacked_result = {
            "fit_info": fit_info,
            "calcium_uM": ca_uM.tolist(),
            "observed_RLU": y_obs.tolist(),
            "mechanistic_RLU": y_mech.tolist(),
            "stacked_predictions": preds,
            "note": (
                "Layer 1 = CLASP assembly ODE; Layer 2 = ResidualGP; "
                "Layer 3 = XGBoost only if ≥15 points and xgboost installed."
            ),
        }
        data_class = "synthetic_fixture"
        st.line_chart(
            {
                "mechanistic": y_mech,
                "observed": y_obs,
                "stacked": [p["predicted_value"] for p in preds],
            }
        )
        st.json(fit_info)
    else:
        from src.data_ingestion import (
            LearnTimeseriesValidationError,
            load_learn_timeseries_package,
        )
        from src.data_ingestion.learn_timeseries import resolve_example_package

        csv_upload = st.file_uploader("Product CSV (`time`, `product`)", type=["csv"])
        meta_upload = st.file_uploader(
            "Metadata sidecar (`.metadata.json` from templates/)",
            type=["json"],
        )
        if st.button("Load tracked synthetic example", help="SYN_LEARN_001 fixture from repo"):
            try:
                csv_path, meta_path = resolve_example_package()
                pkg = load_learn_timeseries_package(csv_path, meta_path)
                st.session_state["learn_pkg"] = {
                    "product": np.asarray(pkg.product, dtype=float),
                    "time": np.asarray(pkg.time, dtype=float),
                    "data_class": pkg.metadata.data_class,
                    "warnings": list(pkg.warnings),
                    "mechanism": pkg.metadata.mechanism_type,
                    "record_id": pkg.metadata.record_id,
                }
            except Exception as exc:
                st.error(f"Could not load example: {exc}")

        loaded = st.session_state.get("learn_pkg")
        if csv_upload is not None and meta_upload is not None:
            try:
                pkg = load_learn_timeseries_package(csv_upload, meta_upload)
                st.session_state["learn_pkg"] = {
                    "product": np.asarray(pkg.product, dtype=float),
                    "time": np.asarray(pkg.time, dtype=float),
                    "data_class": pkg.metadata.data_class,
                    "warnings": list(pkg.warnings),
                    "mechanism": pkg.metadata.mechanism_type,
                    "record_id": pkg.metadata.record_id,
                }
                loaded = st.session_state["learn_pkg"]
            except LearnTimeseriesValidationError as exc:
                st.error(f"Package rejected: {exc}")
            except Exception as exc:
                st.error(f"Could not load package: {exc}")
        elif csv_upload is not None or meta_upload is not None:
            st.info("Upload both the CSV and its metadata JSON sidecar.")
        elif loaded is None:
            st.info("Upload CSV + metadata, or load the tracked synthetic example.")

        if loaded:
            experimental = loaded["product"]
            experimental_time = loaded["time"]
            data_class = loaded["data_class"]
            package_warnings = loaded["warnings"]
            mechanism = loaded["mechanism"]
            st.write(
                f"Loaded `{loaded['record_id']}` · {len(experimental)} points · "
                f"data_class=`{data_class}` · mechanism=`{mechanism.value}`"
            )
            for warning in package_warnings:
                st.warning(warning)
            st.line_chart({"product": experimental})

    if stacked_result is not None:
        st.subheader("Stacked ensemble (Docs-6 Layers 1–3)")
        st.caption(stacked_result["note"])
        st.dataframe(stacked_result["stacked_predictions"], use_container_width=True)
        return

    if st.button("Run Learn Mode", type="primary") and experimental is not None:
        payload_ids = ["OtsA", "OtsB"]
        if mechanism == MechanismType.COVALENT_CAPTURE:
            op_mode = "locking"
        elif mechanism == MechanismType.TARGET_COMPLEMENTATION:
            op_mode = "target_triggered"
        else:
            op_mode = "reversible"

        spec = DesignSpec(
            design_id="UI_LEARN_001",
            chassis="E_coli" if mechanism != MechanismType.TARGET_COMPLEMENTATION else "cell_free",
            mechanism_type=mechanism,
            scaffold=ScaffoldSpec(
                scaffold_id="CTPR5",
                repeat_count=5,
                docking_positions=[1, 3],
            ),
            payload_ids=payload_ids,
            operating_mode=op_mode,
        )
        with st.spinner("Fitting residual GP and ranking experiments..."):
            result = LearnMode().run(
                spec,
                experimental_product=np.asarray(experimental, dtype=float),
                experimental_time=experimental_time,
                strategy=strategy,  # type: ignore[arg-type]
                top_k=3,
                data_class=data_class,
                package_warnings=package_warnings,
            )

        if result["status"] != "SUCCESS":
            st.error(result.get("errors"))
            return

        st.success(
            f"Learn Mode finished · evidence maturity reported as: {result['evidence_maturity']}"
        )
        if result.get("data_class"):
            st.caption(f"Input data_class: `{result['data_class']}`")
        st.caption(
            "Maturity reflects that observations were supplied to the software — "
            "confirm in the lab notebook before calling data Tier-1 on the wiki. "
            "RMSE review is a human gate before wiki use."
        )

        t = np.asarray(result["time_points"])
        ode = np.asarray(result["ode_baseline_product"])
        exp = np.asarray(result["experimental_product"])
        aug = result["augmented_kinetics"]
        mean = np.asarray(aug["mean"])
        std = np.asarray(aug["std"])

        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=t, y=ode, name="ODE baseline", line=dict(color="#242220")))
            fig.add_trace(
                go.Scatter(
                    x=t,
                    y=exp,
                    name="Observations",
                    mode="markers",
                    marker=dict(color="#FF8000", size=7),
                )
            )
            fig.add_trace(go.Scatter(x=t, y=mean, name="Augmented mean", line=dict(color="#266FB1")))
            fig.add_trace(
                go.Scatter(
                    x=np.concatenate([t, t[::-1]]),
                    y=np.concatenate([mean + std, (mean - std)[::-1]]),
                    fill="toself",
                    fillcolor="rgba(38,111,177,0.15)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="±1σ",
                    hoverinfo="skip",
                )
            )
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=30, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(235,228,217,0.65)",
                font=dict(color="#242220"),
                xaxis_title="time",
                yaxis_title="product",
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.line_chart({"ode": ode, "obs": exp, "augmented": mean})

        cmp_ = result["comparison"]
        c1, c2 = st.columns(2)
        c1.metric("RMSE", f"{cmp_['rmse']:.4g}")
        c2.metric("Max |error|", f"{cmp_['max_abs_error']:.4g}")
        st.info(cmp_["note"])

        ident = result.get("identifiability")
        if ident:
            st.subheader("Identifiability (Fisher / CRLB)")
            st.caption(ident.get("note", ""))
            if ident.get("success"):
                if ident.get("non_identifiable_parameters"):
                    st.warning(
                        "Non-identifiable parameters (do not present as fitted values): "
                        + ", ".join(ident["non_identifiable_parameters"])
                    )
                else:
                    st.success("All phenomenological parameters identifiable at this design.")
                st.json(
                    {
                        "fitted_values": ident.get("fitted_values"),
                        "uncertainties": ident.get("uncertainties"),
                        "rmse": ident.get("rmse"),
                    }
                )
            else:
                st.info(ident.get("error") or "Identifiability unavailable.")

        st.subheader("Next experiment recommendations")
        st.dataframe(result["next_experiment_recommendations"], use_container_width=True)
        st.subheader("Mandatory controls (do not skip)")
        st.json(result["required_controls"])


def page_optimize() -> None:
    st.header("Optimize CTPR spacing")
    st.caption(
        "Rank docking-repeat spacings (Δi) with ORIGAMI screw geometry "
        "(1.1 nm rise, 45° twist, cylindrical screw). Scores are Tier-3 computational rankings."
    )

    col_in, col_out = st.columns([1, 2], gap="large")
    with col_in:
        st.subheader("Target parameters")
        radius_a = st.number_input("Payload A radius R_A [Å]", value=45.0, min_value=1.0, step=0.5)
        radius_b = st.number_input("Payload B radius R_B [Å]", value=25.0, min_value=1.0, step=0.5)
        p_class = st.selectbox(
            "Interaction class",
            options=list(InteractionClass),
            format_func=lambda c: {
                InteractionClass.METABOLIC: "Metabolic cascade (reaction–diffusion heuristic)",
                InteractionClass.BINDING: "Binding pair / NanoBiT",
                InteractionClass.KINASE: "Kinase / phosphatase reach heuristic",
                InteractionClass.ELECTRON: "Electron transfer distance decay",
            }[c],
        )
        km = st.number_input(
            "Substrate K_m [M] (metabolic class)",
            value=1e-4,
            min_value=1e-12,
            format="%.6g",
        )
        run_opt = st.button("Calculate optimum", type="primary")

    static_html = REPO_ROOT / "web" / "ctpr_scaffold_optimizer.html"
    with st.expander("Standalone HTML demo"):
        st.write(
            f"Browser-only copy lives at `{static_html.relative_to(REPO_ROOT)}`. "
            "This Streamlit page uses the Python optimizer (`src/scaffold_optimizer`)."
        )
        if static_html.is_file() and st.checkbox("Embed HTML demo (client-side JS)"):
            import streamlit.components.v1 as components

            components.html(static_html.read_text(encoding="utf-8"), height=920, scrolling=True)

    if not run_opt:
        st.info("Set payload radii and interaction class, then calculate optimum.")
        return

    try:
        result = optimize_ctpr_spacing(radius_a, radius_b, p_class, km_M=float(km))
    except Exception as exc:
        st.error(f"Optimizer rejected inputs: {exc}")
        return

    with col_out:
        st.subheader("Optimization results")
        m1, m2, m3 = st.columns(3)
        m1.metric("Optimal spacing (Δi*)", f"{result.optimal_delta_i} repeats")
        m2.metric("Recommended scaffold", f"CTPR-{result.recommended_scaffold_repeats}")
        m3.metric("System score (Φ)", f"{result.best_score:.3f}")
        st.caption(result.honesty_note)

        rows = []
        for c in result.candidates:
            c_local = (
                f"{c.c_local_M * 1000:.2f} mM"
                if c.c_local_M is not None
                else "N/A"
            )
            rows.append(
                {
                    "Δi": c.delta_i,
                    "Docking pairs": f"(Repeat {c.docking_pair[0]}, Repeat {c.docking_pair[1]})",
                    "d_center (Å)": round(c.d_center_A, 2),
                    "d_active (Å)": round(c.d_active_A, 2),
                    "P_steric": f"{c.p_steric * 100:.1f}%",
                    "C_local": c_local,
                    "Score (Φ)": round(c.score, 3),
                    "State": c.state,
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.subheader("3D superhelix docking architecture")
        st.code(result.ascii_map, language=None)
        with st.expander("Geometry constants"):
            st.json(result.geometry_constants)

        best = next(c for c in result.candidates if c.delta_i == result.optimal_delta_i)
        if st.button("Send to Design Mode", type="primary"):
            st.session_state["design_prefill"] = {
                "source": "optimizer",
                "repeat_count": result.recommended_scaffold_repeats,
                "dock_a": best.docking_pair[0],
                "dock_b": best.docking_pair[1],
                "optimal_delta_i": result.optimal_delta_i,
                "best_score": round(result.best_score, 3),
                "mechanism_type": interaction_class_to_mechanism(result.interaction_class).value,
                "design_id": f"OPT_CTPR{result.recommended_scaffold_repeats}",
            }
            # Allow Design Mode to apply these docks once (without later repeat edits wiping them).
            st.session_state.pop("_design_prefill_docks_applied", None)
            st.session_state["app_mode"] = "Design a CLASP system"
            st.rerun()


def run() -> None:
    st.set_page_config(
        page_title="ORIGAMI · CLASP Design Engine",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()

    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "Explore evidence"

    with st.sidebar:
        st.markdown("## ORIGAMI")
        st.caption("Hong Kong team · ISEF 2026")
        mode = st.radio(
            "Mode",
            [
                "Explore evidence",
                "Design a CLASP system",
                "Optimize CTPR spacing",
                "Learn from data",
            ],
            key="app_mode",
        )
        st.markdown("---")
        st.caption(
            "Mechanism-aware · uncertainty shown · allowlist enforced · "
            "refusal when evidence is insufficient"
        )
        st.caption("[5-min demo script](docs/DEMO.md)")

    _banner()
    st.title("ORIGAMI")
    st.subheader("Mechanism-aware design for conditional protein assembly")

    if mode.startswith("Explore"):
        page_explore()
    elif mode.startswith("Design"):
        page_design()
    elif mode.startswith("Optimize"):
        page_optimize()
    else:
        page_learn()


if __name__ == "__main__":
    run()
