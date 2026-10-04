"""Live modelling sandbox: screw, melt, clash, binding, next length.

From the repo root:

    pip install -e ".[ui]"
    streamlit run sandbox/modelling.py --server.port 48621 --server.address 0.0.0.0
"""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from origami.priors import DEFAULT_PAYLOAD_RADIUS_A, N_REPEATS_MAX, N_REPEATS_MIN
from sandbox.modelling_service import (
    length_series,
    run_binding,
    score_length,
    suggest_next_length,
)

st.set_page_config(page_title="ORIGAMI modelling sandbox", layout="wide")
st.title("ORIGAMI modelling sandbox")
st.caption(
    "These are calculations. They are not measurements on this fusion. "
    "Clash needs two radii. Binding needs concentrations in mol/L. "
    "A pass on next length uses a cutoff that has not been measured."
)

tab_score, tab_series, tab_bind, tab_next = st.tabs(
    ["One length", "Length series", "Binding", "Next length"]
)


def _radii(use_radii: bool, r_a: float, r_b: float) -> list[float] | None:
    if not use_radii:
        return None
    return [float(r_a), float(r_b)]


with tab_score:
    st.subheader("Score one length")
    st.write(
        "Always: length along the repeats, Phillips melting temperature, "
        "straight-line distance between two repeats. Clash and local "
        "concentration only if you type two radii."
    )
    n = st.number_input(
        "Repeat count",
        min_value=N_REPEATS_MIN,
        max_value=N_REPEATS_MAX,
        value=8,
        step=1,
        key="score_n",
    )
    use_radii = st.checkbox(
        "Type two payload radii (Å) to compute clash",
        value=False,
        key="score_radii_on",
    )
    r_a = r_b = float(DEFAULT_PAYLOAD_RADIUS_A.value)
    if use_radii:
        c1, c2 = st.columns(2)
        with c1:
            r_a = st.number_input(
                "Radius A (Å)",
                min_value=0.1,
                value=round(float(DEFAULT_PAYLOAD_RADIUS_A.value), 3),
                step=0.5,
                key="score_ra",
                help="Default is the CaM–M13 Cα sphere from PDB 2BBM. Label it as structure-derived.",
            )
        with c2:
            r_b = st.number_input(
                "Radius B (Å)",
                min_value=0.1,
                value=round(float(DEFAULT_PAYLOAD_RADIUS_A.value), 3),
                step=0.5,
                key="score_rb",
            )
    if st.button("Run this length", type="primary"):
        try:
            report = score_length(int(n), radii_A=_radii(use_radii, r_a, r_b))
            st.session_state["score_report"] = report
            st.session_state["score_error"] = None
        except ValueError as exc:
            st.session_state["score_error"] = str(exc)
    if st.session_state.get("score_error"):
        st.error(st.session_state["score_error"])
    report = st.session_state.get("score_report")
    if report:
        structure = report["structure"]
        stability = report["stability"]
        docking = report["docking"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Length along repeats (nm)", f"{structure['contour_nm']:.3f}")
        m2.metric("Melt (°C)", f"{stability['tm_C']:.2f}" if stability["tm_C"] else "—")
        m3.metric("Straight-line distance (Å)", f"{docking['chord_A']:.2f}")
        m4.metric("Repeats used", ", ".join(str(i) for i in docking["indices"]))
        if docking["clash_computable"]:
            st.write(
                f"Chance the payloads overlap: {docking['p_clash']:.3f} (0 to 1). "
                f"Local concentration: {docking['c_eff_M']:.3e} M."
            )
        else:
            st.info("Clash and local concentration were not computed. Type two radii.")
        if stability.get("past_longest_cited_length"):
            st.warning("This length is longer than the longest Phillips table row.")
        st.download_button(
            "Download JSON",
            json.dumps(report, indent=2),
            file_name=f"chassis-n{report['n_repeats']}.json",
            mime="application/json",
        )


with tab_series:
    st.subheader("Length series")
    st.write(
        "Phillips melting temperature and screw length for every n from 3 to 24. "
        "n = 3, 8, and 14 are the planned lengths. n = 17 is computable and is not a planned length."
    )
    s1, s2 = st.columns(2)
    with s1:
        n_min = st.number_input("From n", N_REPEATS_MIN, N_REPEATS_MAX, 3, 1, key="ser_min")
    with s2:
        n_max = st.number_input("To n", N_REPEATS_MIN, N_REPEATS_MAX, 24, 1, key="ser_max")
    series_radii = st.checkbox("Include clash (type two radii)", value=False, key="ser_radii_on")
    sr_a = sr_b = float(DEFAULT_PAYLOAD_RADIUS_A.value)
    if series_radii:
        d1, d2 = st.columns(2)
        with d1:
            sr_a = st.number_input("Radius A (Å)", 0.1, value=round(float(DEFAULT_PAYLOAD_RADIUS_A.value), 3), key="ser_ra")
        with d2:
            sr_b = st.number_input("Radius B (Å)", 0.1, value=round(float(DEFAULT_PAYLOAD_RADIUS_A.value), 3), key="ser_rb")
    if st.button("Run length series", type="primary"):
        try:
            rows = length_series(int(n_min), int(n_max), _radii(series_radii, sr_a, sr_b))
            st.session_state["series_rows"] = rows
            st.session_state["series_error"] = None
        except ValueError as exc:
            st.session_state["series_error"] = str(exc)
    if st.session_state.get("series_error"):
        st.error(st.session_state["series_error"])
    rows = st.session_state.get("series_rows")
    if rows:
        frame = pd.DataFrame(rows)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=frame["n_repeats"],
                y=frame["tm_C"],
                error_y={
                    "type": "data",
                    "array": frame["tm_95_upper_C"] - frame["tm_C"],
                    "arrayminus": frame["tm_C"] - frame["tm_95_lower_C"],
                    "visible": True,
                },
                mode="lines+markers",
                name="Melting temperature (°C)",
            )
        )
        for mark in (3, 8, 14):
            if mark in set(frame["n_repeats"]):
                fig.add_vline(x=mark, line_dash="dot", line_color="#C45C12")
        fig.update_layout(
            xaxis_title="Repeat count",
            yaxis_title="Melting temperature (°C)",
            template="simple_white",
        )
        st.plotly_chart(fig, use_container_width=True)
        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=frame["n_repeats"],
                y=frame["chord_A"],
                mode="lines+markers",
                name="Straight-line distance (Å)",
            )
        )
        fig2.update_layout(
            xaxis_title="Repeat count",
            yaxis_title="Straight-line distance (Å)",
            template="simple_white",
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(frame, use_container_width=True)
        st.download_button(
            "Download CSV",
            frame.to_csv(index=False),
            file_name="length-series.csv",
            mime="text/csv",
        )


with tab_bind:
    st.subheader("Binding")
    st.write(
        "Three calculations. Concentrations are moles per litre. "
        "None of these rates were measured on our protein."
    )
    mode = st.selectbox(
        "Which calculation",
        (
            "recruitment_steady",
            "covalent_timecourse",
            "nanobit_complementation",
        ),
        format_func=lambda value: {
            "recruitment_steady": "Bound fraction (peptide Kd 0.19 nM)",
            "covalent_timecourse": "Spy lock over time (Zakeri 1.4×10³ M⁻¹ s⁻¹)",
            "nanobit_complementation": "LgBiT–SmBiT complex (printed Kd 190 μM)",
        }[value],
    )
    fields: dict = {}
    if mode == "recruitment_steady":
        fields["c_free_M"] = st.number_input(
            "Free concentration (M)",
            min_value=0.0,
            value=1e-8,
            format="%.2e",
            key="bind_c",
        )
    elif mode == "covalent_timecourse":
        b1, b2 = st.columns(2)
        with b1:
            fields["tag0_M"] = st.number_input("SpyTag (M)", 0.0, value=1e-5, format="%.2e", key="tag")
        with b2:
            fields["catcher0_M"] = st.number_input(
                "SpyCatcher (M)", 0.0, value=1e-5, format="%.2e", key="catcher"
            )
    else:
        n1, n2 = st.columns(2)
        with n1:
            fields["lg0_M"] = st.number_input("LgBiT (M)", 0.0, value=1e-6, format="%.2e", key="lg")
        with n2:
            fields["sm0_M"] = st.number_input("SmBiT (M)", 0.0, value=1e-6, format="%.2e", key="sm")
    if st.button("Run binding", type="primary"):
        try:
            result = run_binding(mode, **fields)
            st.session_state["bind_result"] = result
            st.session_state["bind_error"] = None
        except ValueError as exc:
            st.session_state["bind_error"] = str(exc)
    if st.session_state.get("bind_error"):
        st.error(st.session_state["bind_error"])
    result = st.session_state.get("bind_result")
    if result:
        if result.get("mode") == "recruitment_steady" or "recruitment" in result:
            rec = result.get("recruitment") or {}
            st.metric("Fraction bound", f"{rec.get('theta_ss', float('nan')):.4e}")
            st.write(
                f"95% range from the Kd: {rec.get('theta_95_lower'):.3e} to "
                f"{rec.get('theta_95_upper'):.3e}. Kd {rec.get('kd_M'):.3e} M."
            )
        if "equilibrium_complex_M" in result:
            st.metric("Equilibrium complex (M)", f"{result['equilibrium_complex_M']:.3e}")
            rates = result.get("rates_used") or {}
            st.write(
                f"k_off/k_on {rates.get('kinetic_kd_M')}. Printed Kd {rates.get('printed_kd_M')} M."
            )
        series = (result.get("series") or {}) if isinstance(result.get("series"), dict) else {}
        if series.get("time_s") and series.get("adduct_M"):
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(x=series["time_s"], y=series["adduct_M"], mode="lines", name="Adduct (M)")
            )
            fig.update_layout(
                xaxis_title="Time (s)",
                yaxis_title="Adduct (M)",
                template="simple_white",
            )
            st.plotly_chart(fig, use_container_width=True)
        st.download_button(
            "Download JSON",
            json.dumps(result, indent=2),
            file_name="binding.json",
            mime="application/json",
        )


with tab_next:
    st.subheader("Next length")
    st.write(
        "Leave readings blank to rank lengths from the docking score. "
        "Type a luminescence reading to adjust that ranking. "
        "The first next length is the one to use. Other methods may disagree. "
        "A pass uses a cutoff that has not been measured."
    )
    l1, l2 = st.columns(2)
    with l1:
        learn_min = st.number_input("From n", N_REPEATS_MIN, N_REPEATS_MAX, 3, 1, key="learn_min")
    with l2:
        learn_max = st.number_input("To n", N_REPEATS_MIN, N_REPEATS_MAX, 14, 1, key="learn_max")
    obs_text = st.text_area(
        "Optional readings (JSON list). Example: "
        '[{"n_repeats": 8, "y": 0.4, "fidelity": 1}]',
        value="[]",
        height=100,
    )
    if st.button("Suggest next length", type="primary"):
        try:
            observations = json.loads(obs_text)
            if not isinstance(observations, list):
                raise ValueError("Readings must be a JSON list.")
            learned = suggest_next_length(int(learn_min), int(learn_max), observations)
            st.session_state["learn_report"] = learned
            st.session_state["learn_error"] = None
        except (ValueError, json.JSONDecodeError) as exc:
            st.session_state["learn_error"] = str(exc)
    if st.session_state.get("learn_error"):
        st.error(st.session_state["learn_error"])
    learned = st.session_state.get("learn_report")
    if learned:
        rec = learned.get("recommendation") or {}
        st.metric("Measure this repeat count", learned.get("next_n"))
        st.write(
            f"Luminescence fit: n = {rec.get('next_n')}. "
            f"Docking-score fit: n = {rec.get('design_engine_next_n')}. "
            f"Luminescence with dry and lab readings: n = {rec.get('multifidelity_luminescence_n')}. "
            f"Lengths to run together: {rec.get('batch_n')}. Use the first. They are not averaged."
        )
        st.download_button(
            "Download JSON",
            json.dumps(learned, indent=2),
            file_name="next-length.json",
            mime="application/json",
        )
