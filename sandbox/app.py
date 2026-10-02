"""ORIGAMI math-chassis sandbox: input, process, result data.

Run from the repo root:

    pip install -e ".[ui]"
    streamlit run sandbox/app.py --server.port 48621 --server.address 0.0.0.0
"""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from origami.priors import DEFAULT_PAYLOAD_RADIUS_A, LINKER_SIGMA_A, N_REPEATS_MAX, N_REPEATS_MIN
from origami.stability.series import DEFAULT_OPERATING_TEMPERATURE_C
from sandbox.service import run_sandbox


def _payload_row(
    payload_id: str,
    role: str,
    terminus: str,
    repeat_index: int,
    radius_A: float,
    linker_sigma_A: float,
    mw_Da: float,
    mw_source: str,
    sequence: str,
) -> dict:
    row = {
        "payload_id": payload_id,
        "role": role,
        "fusion_terminus": terminus,
        "repeat_index": repeat_index,
        "radius_A": radius_A,
        "linker_sigma_A": linker_sigma_A,
    }
    if mw_Da > 0.0:
        row["mw_Da"] = float(mw_Da)
        row["mw_source"] = mw_source
    if sequence.strip():
        row["protein_sequence"] = sequence
    return row

st.set_page_config(page_title="ORIGAMI design sandbox", layout="wide")
st.title("ORIGAMI design sandbox")
st.caption(
    "Input a scaffold. The process is ``run_design``. Result numbers come from "
    "that report. calibrated stays false. next_n is not a team optimum."
)

if "last_run" not in st.session_state:
    st.session_state.last_run = None
if "last_error" not in st.session_state:
    st.session_state.last_error = None
if "obs_rows" not in st.session_state:
    st.session_state.obs_rows = []

with st.sidebar:
    st.header("1. Input")
    design_id = st.text_input("Design id", value="sandbox-probe")
    n_repeats = st.number_input(
        "n_repeats",
        min_value=N_REPEATS_MIN,
        max_value=N_REPEATS_MAX,
        value=8,
        step=1,
    )
    supply_payloads = st.checkbox(
        "Supply two payload rows",
        value=False,
        help="Off: end-pair default CaM-M13 radii (PDB 2BBM-derived).",
    )
    payloads: list[dict] | None = None
    if supply_payloads:
        st.caption(
            "Every physical number must be typed. The form prefills the "
            f"(GGGGS)3 RMS {LINKER_SIGMA_A.value:.3f} Å. Change it if the "
            "tether is not that chain."
        )
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Payload A")
            a_id = st.text_input("A payload_id", value="payload_a")
            a_role = st.text_input("A role", value="enzyme")
            a_term = st.selectbox("A fusion_terminus", ["N", "C"], index=1)
            a_idx = st.number_input("A repeat_index (0-based)", 0, int(n_repeats) - 1, 0)
            a_r = st.number_input("A radius_A", min_value=0.1, value=round(DEFAULT_PAYLOAD_RADIUS_A.value, 1), step=0.5)
            a_s = st.number_input(
                "A linker_sigma_A",
                min_value=0.0,
                value=float(LINKER_SIGMA_A.value),
                step=0.1,
                format="%.6f",
            )
            a_mw = st.number_input("A mw_Da (optional, 0 = omit)", min_value=0.0, value=0.0, step=100.0)
            a_mw_src = st.text_input("A mw_source", value="")
            a_seq = st.text_area("A protein_sequence (optional)", value="")
        with col_b:
            st.subheader("Payload B")
            b_id = st.text_input("B payload_id", value="payload_b")
            b_role = st.text_input("B role", value="enzyme")
            b_term = st.selectbox("B fusion_terminus", ["N", "C"], index=0)
            b_idx = st.number_input(
                "B repeat_index (0-based)",
                0,
                int(n_repeats) - 1,
                int(n_repeats) - 1,
            )
            b_r = st.number_input("B radius_A", min_value=0.1, value=round(DEFAULT_PAYLOAD_RADIUS_A.value, 1), step=0.5, key="b_r")
            b_s = st.number_input(
                "B linker_sigma_A",
                min_value=0.0,
                value=float(LINKER_SIGMA_A.value),
                step=0.1,
                format="%.6f",
                key="b_s",
            )
            b_mw = st.number_input("B mw_Da (optional, 0 = omit)", min_value=0.0, value=0.0, step=100.0, key="b_mw")
            b_mw_src = st.text_input("B mw_source", value="", key="b_mw_src")
            b_seq = st.text_area("B protein_sequence (optional)", value="", key="b_seq")
        payloads = [
            _payload_row(a_id, a_role, a_term, int(a_idx), float(a_r), float(a_s), a_mw, a_mw_src, a_seq),
            _payload_row(b_id, b_role, b_term, int(b_idx), float(b_r), float(b_s), b_mw, b_mw_src, b_seq),
        ]
    else:
        st.info(
            f"Default payload radius is {DEFAULT_PAYLOAD_RADIUS_A.value} Å "
            "(CaM-M13, PDB 2BBM-derived). Default linker is "
            f"{LINKER_SIGMA_A.value:.3f} Å."
        )

    thermal_prior = st.checkbox("Thermal prior (Phillips 2012 CTPRa DSC)", value=True)
    t_assay = None
    if thermal_prior:
        t_assay = st.number_input(
            "t_assay_C",
            value=float(DEFAULT_OPERATING_TEMPERATURE_C),
            step=1.0,
            help="E. coli operating choice, not a measured Tm.",
        )

    st.subheader("Optional observation")
    st.caption("User-entered y only. This is not a wet-lab import.")
    obs_n = st.number_input("Observed n_repeats", N_REPEATS_MIN, N_REPEATS_MAX, N_REPEATS_MIN)
    obs_y = st.number_input("Observed y", value=0.0, step=0.05)
    if st.button("Add user-entered observation"):
        st.session_state.obs_rows.append(
            {"n_repeats": int(obs_n), "y": float(obs_y), "source": "user_entered"}
        )
    if st.button("Clear observations"):
        st.session_state.obs_rows = []
    if st.session_state.obs_rows:
        st.dataframe(pd.DataFrame(st.session_state.obs_rows), hide_index=True)

    run_clicked = st.button("Run design", type="primary")

if run_clicked:
    request = {
        "design_id": design_id,
        "n_repeats": int(n_repeats),
        "payloads": payloads,
        "thermal_prior": thermal_prior,
        "t_assay_C": None if t_assay is None else float(t_assay),
        "observations": list(st.session_state.obs_rows),
    }
    try:
        st.session_state.last_run = run_sandbox(request)
        st.session_state.last_error = None
    except Exception as exc:
        st.session_state.last_error = str(exc)
        st.session_state.last_run = None

if st.session_state.last_error:
    st.error(st.session_state.last_error)

bundle = st.session_state.last_run
if bundle is None:
    st.info("Enter a design on the left and run it. Nothing is scored until then.")
    st.stop()

inp = bundle["input"]
proc = bundle["process"]
report = bundle["result"]
library = bundle["library"]

st.header("2. Process")
p1, p2 = st.columns((1, 1))
with p1:
    st.subheader("Steps actually called")
    for step in proc["steps"]:
        st.write(f"- {step}")
with p2:
    st.subheader("Input that was sent")
    st.json(inp)
    for note in proc["notes"]:
        st.warning(note)

st.header("3. Result data")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("n_repeats", report["n_repeats"])
m2.metric("next_n", "None" if report["next_n"] is None else str(report["next_n"]))
sep = report.get("separation") or {}
m3.metric(
    "next_delta_i",
    "None" if sep.get("next_delta_i") is None else str(sep.get("next_delta_i")),
)
m4.metric("calibrated", str(report["calibrated"]))
m5.metric("stability", report["stability_state"])

if report["calibrated"]:
    st.error("calibrated is true. That should not happen from this sandbox.")

tab_sum, tab_size, tab_confirm, tab_dry, tab_n, tab_sep, tab_struct, tab_reg, tab_warn, tab_json = st.tabs(
    [
        "This scaffold",
        "Sequence / MW",
        "Structure + stability",
        "Dry lab data",
        "n library",
        "Δi scan",
        "Cα scene",
        "Team register",
        "Warnings / omitted",
        "Raw JSON",
    ]
)

with tab_sum:
    dist_rows = [
        {
            "pair": key,
            "distance_A": report["pair_distances_A"].get(key),
            "p_clash": report["p_clash"].get(key),
            "c_eff_M": report["c_eff_M"].get(key),
        }
        for key in report["pair_distances_A"]
    ]
    if dist_rows:
        st.dataframe(pd.DataFrame(dist_rows), hide_index=True)
    else:
        st.info("No payload pair distances on this design.")
    st.write(
        {
            "theta_ss": report["theta_ss"],
            "theta_95": [report["theta_95_lower"], report["theta_95_upper"]],
            "da": report["da"],
            "p_capture": report["p_capture"],
            "tm_C": report["tm_C"],
            "delta_g": report["delta_g"],
            "delta_g_units": report["delta_g_units"],
            "highest_cited_delta_g_n": report["highest_cited_delta_g_n"],
        }
    )
    st.caption(
        "da and p_capture stay empty unless k_cat, K_m, k_escape, and v_prod "
        "are supplied. This sandbox does not invent those rates."
    )

with tab_size:
    notes = bundle.get("payload_size") or []
    if not notes:
        st.info(
            "No mw_Da was supplied. Sequence and mass are optional. "
            "They do not replace radius_A. Erickson Rmin is a lower bound, not a clash radius."
        )
    else:
        st.caption(
            "Rmin is Erickson 2009 eq 2.2 (DOI 10.1007/s12575-009-9008-x). "
            "Clash still uses the typed radius_A."
        )
        st.dataframe(pd.DataFrame(notes), hide_index=True)

with tab_confirm:
    confirmation = bundle.get("confirmation")
    if not confirmation:
        st.info("Confirmation table needs zero or two payloads.")
    else:
        st.caption(
            "calibrated is false. Thermal pass is a matched Phillips 2012 CTPRa DSC Tm "
            "above the assay temperature. ΔG is printed and does not set that pass."
        )
        for note in confirmation["notes"]:
            st.caption(note)
        conf_df = pd.DataFrame(confirmation["rows"])
        rigid = int(conf_df["rigid_screw"].sum())
        thermal_pass = int((conf_df["thermal_state"] == "pass").sum())
        both = int(
            ((conf_df["thermal_state"] == "pass") & conf_df["steric_feasible"]).sum()
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Rigid screw (contour ≤ lp)", f"{rigid} / {len(conf_df)}")
        c2.metric("Thermal pass", f"{thermal_pass} / {len(conf_df)}")
        c3.metric("Thermal pass and steric feasible", f"{both} / {len(conf_df)}")
        show = conf_df[
            [
                "n_repeats",
                "contour_nm",
                "rigid_screw",
                "end_pair_chord_A",
                "end_pair_facing_cosine",
                "p_instability",
                "end_pair_p_clash",
                "end_pair_c_eff_M",
                "physics_score",
                "steric_feasible",
                "thermal_state",
                "tm_C",
                "delta_g",
                "delta_g_units",
            ]
        ]
        st.dataframe(show, hide_index=True)
        st.download_button(
            "Download confirmation CSV",
            data=conf_df.to_csv(index=False),
            file_name=f"{report['design_id']}_confirmation.csv",
            mime="text/csv",
        )

with tab_dry:
    dry = bundle.get("drylab") or {}
    learning = dry.get("active_learning") or {}
    st.caption(
        "These rows are measurements of the models. next_n and next_delta_i are the "
        "next coordinates to measure. They are not use-case optima. calibrated is false. "
        "The residual GP is not fit on these scores."
    )
    d1, d2, d3 = st.columns(3)
    d1.metric("next_n to measure", "None" if learning.get("next_n") is None else str(learning["next_n"]))
    d2.metric(
        "next_delta_i to measure",
        "None" if learning.get("next_delta_i") is None else str(learning["next_delta_i"]),
    )
    d3.metric("gp_fitted", str(dry.get("gp_fitted")))
    for note in learning.get("notes") or []:
        st.caption(note)
    meas = pd.DataFrame(dry.get("measurements") or [])
    panel = pd.DataFrame(dry.get("stability_panel") or [])
    if not meas.empty:
        st.subheader("Structural measurements")
        st.dataframe(meas, hide_index=True)
        st.download_button(
            "Download structural measurements CSV",
            data=meas.to_csv(index=False),
            file_name=f"{report['design_id']}_structure_measurements.csv",
            mime="text/csv",
        )
    if not panel.empty:
        st.subheader("Stability panel (series kept separate)")
        st.dataframe(panel, hide_index=True)
        st.download_button(
            "Download stability panel CSV",
            data=panel.to_csv(index=False),
            file_name=f"{report['design_id']}_stability_panel.csv",
            mime="text/csv",
            key="stability_csv",
        )
    st.download_button(
        "Download dry-lab JSON",
        data=json.dumps(dry, indent=2),
        file_name=f"{report['design_id']}_drylab.json",
        mime="application/json",
        key="drylab_json",
    )

with tab_n:
    n_df = pd.DataFrame(
        {
            "n_repeats": library["n_repeats"],
            "gp_mean": library["gp_mean"],
            "gp_std": library["gp_std"],
        }
    )
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=n_df["n_repeats"],
            y=n_df["gp_mean"],
            mode="lines+markers",
            name="posterior mean",
            error_y=dict(type="data", array=n_df["gp_std"], visible=True),
        )
    )
    if report["next_n"] is not None:
        fig.add_vline(
            x=report["next_n"],
            line_dash="dash",
            annotation_text="next_n (acquisition)",
        )
    fig.update_layout(
        xaxis_title="n_repeats",
        yaxis_title="posterior (physics units)",
        title="Library posterior. Unfitted unless you entered y.",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(n_df, hide_index=True)

with tab_sep:
    if not sep:
        st.info("Separation scan was not run.")
    else:
        st.write(
            {
                "gp_fitted": sep.get("gp_fitted"),
                "active_process": sep.get("active_process"),
                "next_delta_i": sep.get("next_delta_i"),
                "design_delta_i": sep.get("design_delta_i"),
                "calibrated": sep.get("calibrated"),
            }
        )
        cand = pd.DataFrame(sep.get("candidates") or [])
        if not cand.empty:
            fig_s = go.Figure()
            fig_s.add_trace(
                go.Scatter(
                    x=cand["delta_i"],
                    y=cand["physics_score"],
                    mode="lines+markers",
                    name="physics_score",
                )
            )
            if sep.get("next_delta_i") is not None:
                fig_s.add_vline(
                    x=sep["next_delta_i"],
                    line_dash="dash",
                    annotation_text="next_delta_i (unfitted)",
                )
            fig_s.update_layout(
                xaxis_title="delta_i",
                yaxis_title="physics_score",
                title="Separation scan on this scaffold",
            )
            st.plotly_chart(fig_s, use_container_width=True)
            st.dataframe(cand, hide_index=True)
        for note in sep.get("notes") or []:
            st.caption(note)

with tab_struct:
    scene = bundle.get("scene") or {}
    ca = scene.get("ca_A") or []
    if ca:
        fig3 = go.Figure()
        fig3.add_trace(
            go.Scatter3d(
                x=[point[0] for point in ca],
                y=[point[1] for point in ca],
                z=[point[2] for point in ca],
                mode="markers",
                name="Cα",
                marker=dict(size=2, color="#1f4b3a"),
            )
        )
        sites = scene.get("sites_A") or []
        if sites:
            fig3.add_trace(
                go.Scatter3d(
                    x=[point[0] for point in sites],
                    y=[point[1] for point in sites],
                    z=[point[2] for point in sites],
                    mode="markers",
                    name="junction",
                    marker=dict(size=4, color="#c4a35a"),
                )
            )
        for payload in scene.get("payloads") or []:
            center = payload["center_A"]
            fig3.add_trace(
                go.Scatter3d(
                    x=[center[0]],
                    y=[center[1]],
                    z=[center[2]],
                    mode="markers+text",
                    name=f"payload r={payload['radius_A']} Å",
                    text=[f"r={payload['radius_A']:.1f} Å"],
                    marker=dict(size=8, color="#8c3a3a"),
                )
            )
        fig3.update_layout(
            title="Placed Cα cloud and payload centers",
            scene=dict(aspectmode="data", xaxis_title="x (Å)", yaxis_title="y (Å)", zaxis_title="z (Å)"),
        )
        st.plotly_chart(fig3, use_container_width=True)
        for note in scene.get("notes") or []:
            st.caption(note)
    st.json(report.get("structure"))

with tab_reg:
    st.caption("Team lengths 2, 3, 14, 20 recorded beside the scan. Not acquisition targets.")
    st.json(report.get("registers"))

with tab_warn:
    st.subheader("Warnings")
    if report["warnings"]:
        for item in report["warnings"]:
            st.write(f"- {item}")
    else:
        st.write("None.")
    st.subheader("Omitted")
    if report["omitted"]:
        for item in report["omitted"]:
            st.write(f"- {item}")
    else:
        st.write("None.")

with tab_json:
    st.download_button(
        "Download report JSON",
        data=json.dumps(bundle, indent=2),
        file_name=f"{report['design_id']}_sandbox.json",
        mime="application/json",
    )
    st.json(bundle)
