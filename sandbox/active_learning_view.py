"""Build the GP + discrete-BO view used by the screenshot sandbox.

Training rows are the AMBER/MATLAB end-to-end lengths at n = 3, 8, and 14
from the PCGEM26 wiki stage-2 table. They are in-silico dry-lab outputs.
The residual GP learns those lengths. Bayesian optimization names the next
unmeasured n. Local concentration and locking time are then recomputed at
the posterior length, with the team's fitted locking rate. The crystal
screw and the Zakeri-page rate stay on the figure as the comparison.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from origami.design_engine.active_learning import entropy, expected_improvement, recommend
from origami.dry_lab_md import (
    DRY_LAB_MD_SOURCE,
    MD_LENGTH_ROWS,
    md_end_to_end_observations,
)
from origami.engine import ClaspDesignEngine, EngineResult, Observation
from origami.learned_kinetics import ConditionedLibrary, condition_on_length_posterior
from origami.priors import DEFAULT_PAYLOAD_RADIUS_A, N_REPEATS_MAX, N_REPEATS_MIN

SCREENSHOT_DEMO_N = tuple(row.n_repeats for row in MD_LENGTH_ROWS)
SCREENSHOT_DEMO_Y = {row.n_repeats: row.end_to_end_A for row in MD_LENGTH_ROWS}
DEMO_NOTE = DRY_LAB_MD_SOURCE
UCB_KAPPA = 1.8
CLASH_LIMIT = 0.85
_ACQUISITION_KEYS = ("ucb", "entropy", "ei")


@dataclass(frozen=True)
class AcquisitionChoice:
    key: str
    n_repeats: int
    acquisition: float
    acquisition_name: str


@dataclass
class ActiveLearningSandbox:
    result: EngineResult
    demo_loaded: bool
    figure: go.Figure
    library_rows: list[dict[str, float | int | str | bool | None]]
    choices: list[AcquisitionChoice]
    acquisition: str
    conditioned: ConditionedLibrary | None = None


def screenshot_demo_observations(
    n_min: int,
    n_max: int,
    demo_n: tuple[int, ...] = SCREENSHOT_DEMO_N,
) -> list[Observation]:
    """Return the dry-lab MD end-to-end rows that fall inside the library."""
    del demo_n
    return md_end_to_end_observations(n_min, n_max)


def _acquisition_scores(
    result: EngineResult,
    acquisition: str,
    kappa: float = UCB_KAPPA,
) -> tuple[np.ndarray, str]:
    mean = result.posterior.mean
    std = result.posterior.std
    observed = {o.n_repeats for o in result.observations}
    if acquisition == "ucb":
        scores = mean + kappa * std
        name = f"UCB(κ={kappa})"
    elif acquisition == "entropy":
        scores = entropy(std)
        name = "posterior entropy (information gain proxy)"
    elif acquisition == "ei":
        n = np.array(result.candidates)
        mask_obs = np.array([int(v) in observed for v in n])
        best = float(np.max(mean[mask_obs])) if np.any(mask_obs) else float(np.max(mean))
        scores = expected_improvement(mean, std, best)
        name = "expected improvement"
    else:
        raise ValueError(f"unknown acquisition {acquisition}")
    return scores, name


def acquisition_choices(result: EngineResult) -> list[AcquisitionChoice]:
    """Next integer under each rule. The three integers are not averaged."""
    observed = {o.n_repeats for o in result.observations}
    X = np.asarray(result.candidates, dtype=float).reshape(-1, 1)
    choices: list[AcquisitionChoice] = []
    for key in _ACQUISITION_KEYS:
        nxt = recommend(
            X,
            result.posterior,
            result.physics_scores,
            result.p_instability,
            observed=observed,
            acquisition=key,
        )
        choices.append(
            AcquisitionChoice(
                key=key,
                n_repeats=nxt.n_repeats,
                acquisition=nxt.acquisition,
                acquisition_name=nxt.acquisition_name,
            )
        )
    return choices


def library_table(
    result: EngineResult,
    acquisition: str,
    conditioned: ConditionedLibrary | None = None,
) -> list[dict[str, float | int | str | bool | None]]:
    scores, name = _acquisition_scores(result, acquisition)
    observed = {o.n_repeats for o in result.observations}
    lo, hi = result.posterior.interval_95()
    conditioned_by_n = {} if conditioned is None else {row.n_repeats: row for row in conditioned.rows}
    rows: list[dict[str, float | int | str | bool | None]] = []
    for i, n in enumerate(result.candidates):
        unused = n not in observed
        legal = bool(result.p_instability[i] < CLASH_LIMIT and unused)
        conditioned_row = conditioned_by_n.get(int(n))
        rows.append(
            {
                "n": int(n),
                "physics_score": float(result.physics_scores[i]),
                "gp_mean": float(result.posterior.mean[i]),
                "gp_std": float(result.posterior.std[i]),
                "ci95_lo": float(lo[i]),
                "ci95_hi": float(hi[i]),
                "literature_chord_A": None if conditioned_row is None else conditioned_row.literature_chord_A,
                "ceff_literature_M": None if conditioned_row is None else conditioned_row.ceff_literature_M,
                "ceff_posterior_M": None if conditioned_row is None else conditioned_row.ceff_posterior_M,
                "half_life_team_s": None if conditioned_row is None else conditioned_row.half_life_team_s,
                "acquisition": float(scores[i]),
                "acquisition_name": name,
                "observed": not unused,
                "legal_for_next": legal,
                "is_next": int(n) == result.next_experiment.n_repeats,
                "literature_best": False
                if conditioned is None
                else int(n) == conditioned.literature_best_n,
            }
        )
    return rows


def _log10_concentration(value_M: float) -> float | None:
    """Plot local concentration only while it is still on a readable scale."""
    if value_M <= 0 or value_M < 1e-15:
        return None
    return float(np.log10(value_M))


def build_gp_figure(
    result: EngineResult,
    acquisition: str = "ucb",
    conditioned: ConditionedLibrary | None = None,
) -> go.Figure:
    """Posterior band on top, acquisition bars underneath, next n marked.

    When the posterior is a length, the crystal-screw chord is drawn with
    it, and a middle panel shows local concentration at both distances.
    """
    n = np.array(result.candidates)
    lo, hi = result.posterior.interval_95()
    nxt = result.next_experiment
    scores, score_name = _acquisition_scores(result, acquisition)
    observed = {o.n_repeats for o in result.observations}
    length_posterior = bool(result.observations) and result.observations[0].units == "Å"
    if conditioned is None:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            row_heights=[0.62, 0.38],
            vertical_spacing=0.08,
            subplot_titles=(
                "GP posterior (end-to-end Å)" if length_posterior else "GP posterior (relative output)",
                f"Acquisition · {score_name}",
            ),
        )
        acquisition_row = 2
        figure_height = 560
    else:
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            row_heights=[0.40, 0.32, 0.28],
            vertical_spacing=0.07,
            subplot_titles=(
                "End-to-end: crystal screw and MD posterior",
                "Local concentration at each distance",
                f"Acquisition · {score_name}",
            ),
        )
        acquisition_row = 3
        figure_height = 820
    if not result.observations:
        fig.add_trace(
            go.Scatter(
                x=n,
                y=result.physics_scores,
                name="physics score S(n)",
                mode="lines+markers",
                line=dict(color="#7A7A7A"),
            ),
            row=1,
            col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=list(n) + list(n[::-1]),
            y=list(hi) + list(lo[::-1]),
            fill="toself",
            name="95% interval",
            line=dict(width=0),
            fillcolor="rgba(38, 111, 177, 0.22)",
            hoverinfo="skip",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=n,
            y=result.posterior.mean,
            name="GP posterior mean",
            mode="lines+markers",
            line=dict(color="#266FB1", width=2),
            marker=dict(size=6, color="#266FB1"),
        ),
        row=1,
        col=1,
    )
    if conditioned is not None:
        fig.add_trace(
            go.Scatter(
                x=n,
                y=[row.literature_chord_A for row in conditioned.rows],
                name="crystal-screw end-to-end",
                mode="lines",
                line=dict(color="#7A7A7A", width=2, dash="dash"),
            ),
            row=1,
            col=1,
        )
    if result.observations:
        fig.add_trace(
            go.Scatter(
                x=[o.n_repeats for o in result.observations],
                y=[o.y for o in result.observations],
                mode="markers",
                name="AMBER MD end-to-end",
                marker=dict(size=14, color="black", symbol="x"),
            ),
            row=1,
            col=1,
        )
    if conditioned is not None:
        fig.add_trace(
            go.Scatter(
                x=n,
                y=[_log10_concentration(row.ceff_literature_M) for row in conditioned.rows],
                name="crystal-screw local concentration",
                mode="lines+markers",
                line=dict(color="#7A7A7A", width=2, dash="dash"),
                marker=dict(size=5, color="#7A7A7A"),
                connectgaps=False,
            ),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=n,
                y=[_log10_concentration(row.ceff_posterior_M) for row in conditioned.rows],
                name="MD posterior local concentration",
                mode="lines+markers",
                line=dict(color="#266FB1", width=2),
                marker=dict(size=5, color="#266FB1"),
            ),
            row=2,
            col=1,
        )
    bar_colors = []
    for value in n:
        length = int(value)
        if length == nxt.n_repeats:
            bar_colors.append("#E07A2F")
        elif length in observed:
            bar_colors.append("#B0B0B0")
        else:
            bar_colors.append("#9BB8D3")
    fig.add_trace(
        go.Bar(
            x=n,
            y=scores,
            name="acquisition score",
            marker_color=bar_colors,
            hovertemplate="n=%{x}<br>score=%{y:.3f}<extra></extra>",
        ),
        row=acquisition_row,
        col=1,
    )
    panel_rows = (1, 2, 3) if conditioned is not None else (1, 2)
    for row in panel_rows:
        fig.add_vline(
            x=nxt.n_repeats,
            line_dash="dash",
            line_color="#C45C26",
            row=row,
            col=1,
        )
    if conditioned is not None and conditioned.literature_best_n != nxt.n_repeats:
        fig.add_vline(
            x=conditioned.literature_best_n,
            line_dash="dot",
            line_color="#5C5C5C",
            row=2,
            col=1,
        )
    # Keep the label inside the axes when the chosen length is at the right edge.
    on_right = nxt.n_repeats >= (float(n.min()) + float(n.max())) / 2
    fig.add_annotation(
        x=nxt.n_repeats,
        y=1,
        yref="y domain",
        text=f"next n={nxt.n_repeats}",
        showarrow=False,
        xanchor="right" if on_right else "left",
        yanchor="top",
        font=dict(color="#C45C26", size=13),
        row=1,
        col=1,
    )
    if conditioned is not None and conditioned.literature_best_n != nxt.n_repeats:
        screw_on_right = conditioned.literature_best_n >= (float(n.min()) + float(n.max())) / 2
        fig.add_annotation(
            x=conditioned.literature_best_n,
            y=1,
            yref="y domain",
            text=f"screw prefers n={conditioned.literature_best_n}",
            showarrow=False,
            xanchor="right" if screw_on_right else "left",
            yanchor="top",
            font=dict(color="#5C5C5C", size=12),
            row=2,
            col=1,
        )
    fig.update_layout(
        height=figure_height,
        template="simple_white",
        legend=dict(orientation="h", yanchor="top", y=-0.16, x=0),
        margin=dict(l=64, r=16, t=48, b=88),
        bargap=0.15,
    )
    x_pad = (float(n.min()) - 0.5, float(n.max()) + 0.5)
    fig.update_xaxes(range=list(x_pad), row=1, col=1)
    if conditioned is not None:
        fig.update_xaxes(range=list(x_pad), row=2, col=1)
    fig.update_xaxes(title_text="CTPR repeats n", dtick=1, range=list(x_pad), row=acquisition_row, col=1)
    y_title = "end-to-end length (Å)" if length_posterior else "relative output"
    fig.update_yaxes(title_text=y_title, row=1, col=1)
    if conditioned is not None:
        fig.update_yaxes(title_text="log10 C_eff (M)", row=2, col=1)
    fig.update_yaxes(title_text="acquisition", row=acquisition_row, col=1)
    return fig


def run_active_learning_sandbox(
    *,
    n_min: int = N_REPEATS_MIN,
    n_max: int = N_REPEATS_MAX,
    payload_radii_A: list[float] | None = None,
    acquisition: str = "ucb",
    extra_observations: list[Observation] | None = None,
    load_demo: bool = True,
) -> ActiveLearningSandbox:
    """Run the existing engine and pack a screenshot-ready view."""
    if n_min < N_REPEATS_MIN or n_max > N_REPEATS_MAX or n_min > n_max:
        raise ValueError("n_min/n_max must lie in the allowed CTPR library")
    if acquisition not in _ACQUISITION_KEYS:
        raise ValueError(f"unknown acquisition {acquisition}")
    radii = payload_radii_A or [
        DEFAULT_PAYLOAD_RADIUS_A.value,
        DEFAULT_PAYLOAD_RADIUS_A.value,
    ]
    eng = ClaspDesignEngine(
        payload_radii_A=radii,
        n_min=int(n_min),
        n_max=int(n_max),
        acquisition=acquisition,
    )
    if load_demo:
        for obs in screenshot_demo_observations(n_min, n_max):
            eng.add_observation(obs)
    for obs in extra_observations or []:
        eng.add_observation(obs)
    result = eng.run()
    conditioned = condition_on_length_posterior(result)
    return ActiveLearningSandbox(
        result=result,
        demo_loaded=load_demo and any(
            n_min <= n <= n_max for n in SCREENSHOT_DEMO_N
        ),
        figure=build_gp_figure(result, acquisition, conditioned),
        library_rows=library_table(result, acquisition, conditioned),
        choices=acquisition_choices(result),
        acquisition=acquisition,
        conditioned=conditioned,
    )
