"""
ORIGAMI Streamlit UI — Explore / Design / Learn.

Run from repo root:
    pip install -e ".[ui]"
    streamlit run app.py
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import streamlit as st

from src.compiler.expression_vector import ExpressionPlan
from src.core.schema import DesignSpec, MechanismType, MoCloPart, ScaffoldSpec
from src.ui.design_mode import DesignMode
from src.ui.explore_mode import ExploreMode
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
}


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --ink: #1a2332;
          --muted: #5c6b7a;
          --paper: #f7f4ef;
          --accent: #0f6b5c;
          --warn: #9a3412;
          --line: #d5cfc4;
        }
        .stApp { background: linear-gradient(165deg, #f7f4ef 0%, #e8eef2 55%, #dfe8e4 100%); }
        h1, h2, h3 { color: var(--ink) !important; letter-spacing: -0.02em; }
        .origami-banner {
          border-left: 4px solid var(--accent);
          background: rgba(255,255,255,0.72);
          padding: 0.85rem 1rem;
          margin-bottom: 1rem;
          color: var(--ink);
        }
        .origami-refuse {
          border: 1px solid #f0b4a0;
          background: #fff7f3;
          color: var(--warn);
          padding: 1rem;
          border-radius: 2px;
        }
        .origami-ok {
          border: 1px solid #9dcec3;
          background: #f2faf7;
          padding: 1rem;
          border-radius: 2px;
        }
        div[data-testid="stSidebar"] {
          background: #1a2332;
        }
        div[data-testid="stSidebar"] * { color: #e8eef2 !important; }
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
    st.write("Parameters currently in the local evidence store:")
    st.code(", ".join(keys) if keys else "(empty)")

    col1, col2 = st.columns([2, 1])
    with col1:
        parameter_key = st.text_input(
            "Parameter key",
            value="k_cat_OtsA",
            help="Try a missing key (e.g. made_up_kcat) to see an honest refusal.",
        )
    with col2:
        st.write("")
        st.write("")
        run = st.button("Ask evidence engine", type="primary", use_container_width=True)

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


def page_design() -> None:
    st.header("Design a CLASP system")
    st.caption("Geometry → mechanism prediction → allowlist / coexpression checks → Design Passport.")

    mechanism = st.selectbox(
        "Mechanism profile",
        options=list(MechanismType),
        format_func=lambda m: _MECHANISM_LABELS[m],
    )
    chassis = st.selectbox("Chassis", ["E_coli", "cell_free", "B_subtilis"])
    design_id = st.text_input("Design ID", value="UI_DESIGN_001")

    c1, c2, c3 = st.columns(3)
    with c1:
        repeat_count = st.slider("CTPR repeats", 2, 20, 5)
    with c2:
        dock_a = st.number_input("Docking site A (1-based)", 1, repeat_count, 1)
    with c3:
        dock_b = st.number_input("Docking site B (1-based)", 1, repeat_count, min(3, repeat_count))

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
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Profile", passport.get("mechanism_profile", "—"))
        m2.metric("Evidence maturity", str(passport.get("evidence_maturity", "—"))[:28])
        m3.metric("Biosecurity", passport.get("biosecurity_review_state", "—"))
        m4.metric("Steric OK", str(passport.get("steric_feasible")))
        if passport.get("payload_roles"):
            st.caption("Payload roles: " + ", ".join(
                f"{k}→{v}" for k, v in passport["payload_roles"].items()
            ))

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
            g1, g2, g3 = st.columns(3)
            g1.metric("Length (nm)", f"{geo.get('total_length_nm', 0):.2f}")
            g2.metric("Rigid", str(geo.get("is_rigid")))
            g3.metric("Docking sites", len(geo.get("docking_sites") or []))
            # Simple 2D projection of backbone
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
                            name="CTPR backbone (x–z)",
                            line=dict(color="#0f6b5c"),
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
                                marker=dict(size=12, color="#9a3412"),
                            )
                        )
                    fig.update_layout(
                        height=360,
                        margin=dict(l=20, r=20, t=30, b=20),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(255,255,255,0.65)",
                        xaxis_title="x (nm)",
                        yaxis_title="z (nm)",
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:  # plotly optional at runtime
                st.info(f"Geometry plot unavailable: {exc}")

        with st.expander("Full passport JSON"):
            st.code(json.dumps(passport, indent=2, default=str))
        with st.expander("Required controls & measurements"):
            st.json(passport.get("required_controls"))
            st.write(passport.get("required_measurements"))


def page_learn() -> None:
    st.header("Learn from data")
    st.caption(
        "Compare mechanistic ODE baseline with observations; recommend the next informative measurement. "
        "GP correction is a residual model — not proof of a molecular mechanism."
    )

    mechanism = st.selectbox(
        "Mechanism profile",
        options=list(MechanismType),
        format_func=lambda m: _MECHANISM_LABELS[m],
        key="learn_mech",
    )
    strategy = st.selectbox("Acquisition strategy", ["UCB", "EI"])
    n_points = st.slider("Time points", 10, 100, 40)

    source = st.radio(
        "Observation source",
        ["Synthetic demo curve (labeled fixture)", "Upload CSV (time, product)"],
        horizontal=True,
    )

    experimental = None
    if source.startswith("Synthetic"):
        st.warning(
            "Synthetic fixture for UI demo only — not Tier-1 experimental data. "
            "Do not put these numbers on the wiki as measurements."
        )
        amp = st.slider("Synthetic amplitude", 0.1, 1.5, 0.8)
        rate = st.slider("Synthetic rate", 0.01, 0.2, 0.04)
        t = np.linspace(0.0, 100.0, n_points)
        experimental = amp * (1.0 - np.exp(-rate * t))
        st.line_chart({"synthetic_product": experimental})
    else:
        upload = st.file_uploader("CSV with columns: time, product", type=["csv"])
        if upload is not None:
            try:
                import pandas as pd

                df = pd.read_csv(upload)
                cols = {c.lower(): c for c in df.columns}
                t_col = cols.get("time") or list(df.columns)[0]
                p_col = cols.get("product") or list(df.columns)[1]
                experimental = df[p_col].to_numpy(dtype=float)
                n_points = len(experimental)
                st.write(f"Loaded {n_points} points from `{t_col}`, `{p_col}`.")
            except Exception as exc:
                st.error(f"Could not parse CSV: {exc}")

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
                strategy=strategy,  # type: ignore[arg-type]
                top_k=3,
            )

        if result["status"] != "SUCCESS":
            st.error(result.get("errors"))
            return

        st.success(
            f"Learn Mode finished · evidence maturity reported as: {result['evidence_maturity']}"
        )
        st.caption(
            "Maturity reflects that observations were supplied to the software — "
            "confirm in the lab notebook before calling data Tier-1 on the wiki."
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
            fig.add_trace(go.Scatter(x=t, y=ode, name="ODE baseline", line=dict(color="#5c6b7a")))
            fig.add_trace(
                go.Scatter(
                    x=t,
                    y=exp,
                    name="Observations",
                    mode="markers",
                    marker=dict(color="#9a3412", size=7),
                )
            )
            fig.add_trace(go.Scatter(x=t, y=mean, name="Augmented mean", line=dict(color="#0f6b5c")))
            fig.add_trace(
                go.Scatter(
                    x=np.concatenate([t, t[::-1]]),
                    y=np.concatenate([mean + std, (mean - std)[::-1]]),
                    fill="toself",
                    fillcolor="rgba(15,107,92,0.15)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="±1σ",
                    hoverinfo="skip",
                )
            )
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=30, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.65)",
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

        st.subheader("Next experiment recommendations")
        st.dataframe(result["next_experiment_recommendations"], use_container_width=True)
        st.subheader("Mandatory controls (do not skip)")
        st.json(result["required_controls"])


def run() -> None:
    st.set_page_config(
        page_title="ORIGAMI · CLASP Design Engine",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()

    with st.sidebar:
        st.markdown("## ORIGAMI")
        st.caption("Hong Kong team · ISEF 2026")
        mode = st.radio(
            "Mode",
            ["Explore evidence", "Design a CLASP system", "Learn from data"],
            index=0,
        )
        st.markdown("---")
        st.caption(
            "Mechanism-aware · uncertainty shown · allowlist enforced · "
            "refusal when evidence is insufficient"
        )

    _banner()
    st.title("ORIGAMI")
    st.subheader("Mechanism-aware design for conditional protein assembly")

    if mode.startswith("Explore"):
        page_explore()
    elif mode.startswith("Design"):
        page_design()
    else:
        page_learn()


if __name__ == "__main__":
    run()
