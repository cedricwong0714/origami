# src/ui/cli.py
"""ORIGAMI command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.core.schema import DesignSpec, MoCloPart, ScaffoldSpec
from src.data_ingestion import LearnTimeseriesValidationError, load_learn_timeseries_package
from src.scaffold_optimizer import InteractionClass, optimize_ctpr_spacing
from src.ui.dashboard_backend import PipelineController


def _cmd_pipeline(args: argparse.Namespace) -> int:
    print(f"=== Running CLASP Pipeline for {args.design_id} ({args.chassis}) ===")

    spec = DesignSpec(
        design_id=args.design_id,
        chassis=args.chassis,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[2, 4],
            persistence_length_nm=15.0,
        ),
        payload_ids=["OtsA", "OtsB"],
        operating_mode="reversible",
    )

    parts = [
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

    initial_concs = {"S": 1.0, "E": 0.1, "ES": 0.0, "P": 0.0}

    controller = PipelineController()
    results = controller.run_full_pipeline(spec, parts, initial_concs)

    if results["status"] == "SUCCESS":
        print("[SUCCESS] Design passed multi-layer verification!")
        print(f"Compiled DNA Length: {len(results['assembled_dna'])} bp")
        print("GenBank Preview:")
        print(results["genbank_file"].split("\n")[0])
        return 0

    print("[FAILED] Verification errors encountered:")
    for err in results["verification_report"].errors:
        print(f"  - {err}")
    return 1


def _cmd_validate_learn(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv)
    meta_path = Path(args.metadata)
    if not csv_path.is_file():
        print(f"[ERROR] CSV not found: {csv_path}", file=sys.stderr)
        return 1
    if not meta_path.is_file():
        print(f"[ERROR] Metadata not found: {meta_path}", file=sys.stderr)
        return 1

    try:
        pkg = load_learn_timeseries_package(
            csv_path,
            meta_path,
            require_controls_recorded=not args.allow_missing_controls,
        )
    except LearnTimeseriesValidationError as exc:
        print(f"[REJECTED] {exc}", file=sys.stderr)
        return 1

    print("[OK] Learn package validated")
    print(f"  record_id     : {pkg.metadata.record_id}")
    print(f"  data_class    : {pkg.metadata.data_class}")
    print(f"  mechanism     : {pkg.metadata.mechanism_type.value}")
    print(f"  n_points      : {len(pkg.product)}")
    print(f"  time_span     : {pkg.time[0]:.4g} – {pkg.time[-1]:.4g} {pkg.metadata.time_unit}")
    for warning in pkg.warnings:
        print(f"  [warning] {warning}")
    if pkg.metadata.data_class == "synthetic_fixture":
        print("  Note: synthetic_fixture — not Tier-1 lab data.")
    return 0


def _cmd_optimize(args: argparse.Namespace) -> int:
    try:
        interaction = InteractionClass(args.interaction)
        result = optimize_ctpr_spacing(
            args.radius_a,
            args.radius_b,
            interaction,
            km_M=args.km,
        )
    except (ValueError, KeyError) as exc:
        print(f"[REJECTED] {exc}", file=sys.stderr)
        return 1

    if args.json:
        import json

        print(json.dumps(result.model_dump(), indent=2, default=str))
        return 0

    print("[OK] CTPR spacing optimization (Tier-3 computational ranking)")
    print(f"  interaction   : {result.interaction_class.value}")
    print(f"  optimal Δi*   : {result.optimal_delta_i} repeats")
    print(f"  scaffold      : CTPR-{result.recommended_scaffold_repeats}")
    print(f"  best score Φ  : {result.best_score:.3f}")
    best = next(c for c in result.candidates if c.delta_i == result.optimal_delta_i)
    print(f"  docking pair  : repeats {best.docking_pair[0]} & {best.docking_pair[1]}")
    print(f"  note          : {result.honesty_note}")
    return 0


def _cmd_import_plate(args: argparse.Namespace) -> int:
    """Print blank-corrected observation rows from a plate-reader CSV."""
    import json

    from origami.lab.plate_reader import PlateReaderError, load_plate_csv

    try:
        result = load_plate_csv(args.csv)
    except (PlateReaderError, OSError, UnicodeDecodeError) as exc:
        print(f"import-plate failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


def _cmd_learn_plate(args: argparse.Namespace) -> int:
    """Run the SSDK learner on a plate-reader CSV."""
    import json

    from origami.lab.plate_reader import PlateReaderError
    from origami.ssdk.learn import SsdkLearnError
    from origami.ssdk.plate_pipeline import learn_from_plate

    try:
        result = learn_from_plate(args.csv, n_min=args.n_min, n_max=args.n_max)
    except (PlateReaderError, SsdkLearnError, OSError, UnicodeDecodeError) as exc:
        print(f"learn-plate failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


def _cmd_ablation(args: argparse.Namespace) -> int:
    """Print the grouped ablation report for a JSON dataset."""
    import json

    import numpy as np

    from src.gp_model.ablation import grouped_ablation

    try:
        with open(args.data, encoding="utf-8") as fh:
            d = json.load(fh)
        report = grouped_ablation(
            np.asarray(d["X"], dtype=float),
            np.asarray(d["y_obs"], dtype=float),
            np.asarray(d["y_mech"], dtype=float),
            list(d["groups"]),
            d.get("feature_names"),
        )
    except (KeyError, ValueError, OSError) as exc:
        print(f"ablation failed: {exc!r}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


def _cmd_freeze(args: argparse.Namespace) -> int:
    """Freeze a prospective CLASP dose-response prediction (Docs §1.6)."""
    import json

    from src.core.clasp_assembly import CLASPParameters, predict_luminescence
    from src.predictions.freeze import freeze_prediction
    from src.predictions.sensitivity import parameter_elasticities

    params = CLASPParameters()
    ca_grid = [float(x) for x in args.calcium_uM.split(",")]
    ca_M = [c * 1e-6 for c in ca_grid]
    values = predict_luminescence(
        __import__("numpy").asarray(ca_M),
        params=params,
        E_T=args.e_t,
        M_T=args.m_t,
        t_end=args.t_end,
    )
    predictions = {}
    for c_uM, y in zip(ca_grid, values):
        value = float(y)
        sens = parameter_elasticities(
            c_uM * 1e-6, params, E_T=args.e_t, M_T=args.m_t, t_end=args.t_end
        )
        predictions[f"ca_{c_uM:g}uM"] = {
            "most_sensitive_parameter": sens["most_sensitive_parameter"],
            "parameter_elasticities": sens["elasticities"],
            "predicted_value": value,
            # predict_luminescence does not propagate parameter error.
            # The band stays a fixed relative placeholder until that exists.
            "uncertainty_95_lower": value * 0.7,
            "uncertainty_95_upper": value * 1.3,
            "uncertainty_method": "fixed_relative_placeholder_pm_30_percent",
            "confidence_tier": "hypothesis_only",
            "units": "RLU",
        }

    path = freeze_prediction(
        args.prediction_id,
        design_spec={
            "E_T": args.e_t,
            "M_T": args.m_t,
            "calcium_uM": ca_grid,
            "t_end_s": args.t_end,
        },
        predictions=predictions,
        model_version="clasp_assembly_1.0.0",
        dataset_version="literature_only_v1",
        parameter_sources=[
            "CLASPParameters in src/core/clasp_assembly.py",
            (
                "k_lock=0.003 s^-1 is the existing ODE prior. "
                "origami.priors records that this value is not printed "
                "in Zakeri et al. 2012."
            ),
        ],
        assumptions=[
            "Fixed free calcium per condition",
            "Hill n=4 is the four-site value already stored on CLASPParameters",
            (
                "The reported interval is predicted_value multiplied by 0.7 and 1.3. "
                "It is a fixed relative placeholder, not a propagated 95% interval."
            ),
            "Tier-3 until wet-lab calibrated",
        ],
        overwrite=args.overwrite,
    )
    print(f"[OK] Frozen prediction written: {path}")
    if args.json:
        print(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2))
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    import json
    from pathlib import Path

    from src.predictions.freeze import compare_to_frozen

    obs = json.loads(Path(args.observations).read_text(encoding="utf-8"))
    path = compare_to_frozen(
        Path(args.frozen),
        observations=obs,
        comparison_id=args.comparison_id,
        overwrite=args.overwrite,
    )
    print(f"[OK] Comparison written: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key, row in payload["comparisons"].items():
        if row.get("status") == "missing_in_frozen":
            print(f"  {key}: missing in frozen")
        else:
            flag = "IN" if row["within_95ci"] else "OUT"
            print(
                f"  {key}: obs={row['observed']:.4g} pred={row['predicted']:.4g} "
                f"err={row['error']:+.4g} [{flag} 95% CI]"
            )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ORIGAMI — mechanism-aware design engine for CLASP",
    )
    sub = parser.add_subparsers(dest="command")

    pipe = sub.add_parser("pipeline", help="Run verification → MoClo → ODE demo pipeline")
    pipe.add_argument("--design-id", type=str, default="CLI_DESIGN_001")
    pipe.add_argument(
        "--chassis",
        type=str,
        default="E_coli",
        choices=["cell_free", "E_coli", "B_subtilis"],
    )
    pipe.set_defaults(func=_cmd_pipeline)

    learn = sub.add_parser(
        "validate-learn",
        help="Validate a Learn Mode CSV + metadata sidecar (checklist D)",
    )
    learn.add_argument("csv", help="Path to product time-series CSV")
    learn.add_argument("metadata", help="Path to .metadata.json sidecar")
    learn.add_argument(
        "--allow-missing-controls",
        action="store_true",
        help="Do not require blank/negative controls for tier1_experimental",
    )
    learn.set_defaults(func=_cmd_validate_learn)

    opt = sub.add_parser(
        "optimize",
        help="Rank CTPR docking spacings (Tier-3 computational ranking)",
    )
    opt.add_argument("--radius-a", type=float, default=45.0, help="Payload A radius [Å]")
    opt.add_argument("--radius-b", type=float, default=25.0, help="Payload B radius [Å]")
    opt.add_argument(
        "--interaction",
        type=str,
        default=InteractionClass.METABOLIC.value,
        choices=[c.value for c in InteractionClass],
    )
    opt.add_argument("--km", type=float, default=1e-4, help="Substrate K_m [M] (metabolic class)")
    opt.add_argument("--json", action="store_true", help="Emit full result as JSON")
    opt.set_defaults(func=_cmd_optimize)

    freeze = sub.add_parser(
        "freeze",
        help="Freeze a prospective CLASP calcium dose-response prediction",
    )
    freeze.add_argument("--prediction-id", type=str, required=True)
    freeze.add_argument(
        "--calcium-uM",
        type=str,
        default="0.1,0.5,1,2,5,10",
        help="Comma-separated free Ca²⁺ concentrations in µM",
    )
    freeze.add_argument("--e-t", type=float, default=1e-6)
    freeze.add_argument("--m-t", type=float, default=1e-6)
    freeze.add_argument("--t-end", type=float, default=3600.0)
    freeze.add_argument("--overwrite", action="store_true")
    freeze.add_argument("--json", action="store_true")
    freeze.set_defaults(func=_cmd_freeze)

    compare = sub.add_parser(
        "compare",
        help="Compare observations to a frozen prediction",
    )
    compare.add_argument("frozen", help="Path to frozen prediction JSON")
    compare.add_argument(
        "observations",
        help="JSON file mapping prediction keys to observed values",
    )
    compare.add_argument("--comparison-id", type=str, default=None)
    compare.add_argument("--overwrite", action="store_true")
    compare.set_defaults(func=_cmd_compare)

    plate = sub.add_parser(
        "import-plate",
        help="Blank-correct a plate-reader CSV into observation rows (JSON)",
    )
    plate.add_argument("csv", help="Long-format CSV: well,construct,n_repeats,batch,role,rlu")
    plate.set_defaults(func=_cmd_import_plate)

    lp = sub.add_parser(
        "learn-plate",
        help="Run the SSDK learner on a plate-reader CSV",
    )
    lp.add_argument("csv")
    lp.add_argument("--n-min", type=int, default=3)
    lp.add_argument("--n-max", type=int, default=24)
    lp.set_defaults(func=_cmd_learn_plate)

    ablate = sub.add_parser(
        "ablation",
        help="Grouped leave-one-group-out ablation of physics, GP and XGBoost",
    )
    ablate.add_argument(
        "data", help='JSON with keys "X", "y_obs", "y_mech", "groups" (and optional "feature_names")'
    )
    ablate.set_defaults(func=_cmd_ablation)

    # Back-compat: `origami --design-id X` runs pipeline without subcommand
    parser.add_argument("--design-id", type=str, default="CLI_DESIGN_001")
    parser.add_argument(
        "--chassis",
        type=str,
        default="E_coli",
        choices=["cell_free", "E_coli", "B_subtilis"],
    )

    args = parser.parse_args()
    if args.command is None:
        exit_code = _cmd_pipeline(args)
    else:
        exit_code = args.func(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
