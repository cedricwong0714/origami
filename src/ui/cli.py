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


def _cmd_learn_ssdk(args: argparse.Namespace) -> int:
    """Run the SSDK learner on a JSON body and print the decision summary."""
    import json

    from origami.ssdk.learn import SsdkLearnError, learn_ssdk

    try:
        body = json.loads(args.json_body)
    except json.JSONDecodeError as exc:
        print(f"learn-ssdk failed: {exc}", file=sys.stderr)
        return 2
    if not isinstance(body, dict):
        print("learn-ssdk failed: JSON object required", file=sys.stderr)
        return 2
    try:
        result = learn_ssdk(body)
    except SsdkLearnError as exc:
        print(f"learn-ssdk failed: {exc}", file=sys.stderr)
        return 2
    if args.full:
        print(json.dumps(result, indent=2))
        return 0
    _print_learn_summary(result)
    return 0


def _print_learn_summary(result: dict) -> None:
    """One decision summary for learn-ssdk and origami ssdk learn."""
    recommendation = result.get("recommendation") or {}
    multi = result.get("multioutput") or {}
    digest = (result.get("canonical") or {}).get("feature_matrix_sha256")
    print(f"primary_family: {recommendation.get('primary_family')}")
    print(f"next_n: {recommendation.get('next_n')}")
    print(f"design_engine_next_n: {recommendation.get('design_engine_next_n')}")
    print(f"multifidelity_luminescence_n: {recommendation.get('multifidelity_luminescence_n')}")
    print(f"batch: {recommendation.get('batch_n')}")
    print(f"overall_status: {multi.get('overall_status')}")
    print(f"omitted_outputs: {', '.join(multi.get('omitted_outputs') or []) or 'none'}")
    print(f"feature_matrix_sha256: {digest}")
    chassis = result.get("chassis_at_next_n") or {}
    structure = chassis.get("structure") or {}
    docking = chassis.get("docking") or {}
    kinetics = chassis.get("kinetics") or {}
    print(f"chassis_n: {chassis.get('n_repeats')}")
    print(f"chassis_contour_nm: {structure.get('contour_nm')}")
    print(f"chassis_clash_computable: {docking.get('clash_computable')}")
    print(f"chassis_kinetics_computable: {kinetics.get('computable')}")
    print("calibrated: false")


def _plate_learn_options(args: argparse.Namespace) -> dict:
    """Merge a JSON learn body with CLI bounds. Observations stay in the CSV."""
    import json

    raw = getattr(args, "json_body", None)
    if raw:
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError("JSON object required")
        if "observations" in body:
            raise ValueError("observations come from the plate file; do not pass them")
    else:
        body = {}
    if getattr(args, "n_min", None) is not None:
        body["n_min"] = args.n_min
    elif "n_min" not in body:
        body["n_min"] = 3
    if getattr(args, "n_max", None) is not None:
        body["n_max"] = args.n_max
    elif "n_max" not in body:
        body["n_max"] = 24
    return body


def _cmd_learn_plate(args: argparse.Namespace) -> int:
    """Run the SSDK learner on a plate-reader CSV."""
    import json

    from origami.lab.plate_reader import PlateReaderError
    from origami.ssdk.learn import SsdkLearnError
    from origami.ssdk.plate_pipeline import learn_from_plate

    try:
        result = learn_from_plate(args.csv, **_plate_learn_options(args))
    except (PlateReaderError, SsdkLearnError, OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"learn-plate failed: {exc}", file=sys.stderr)
        return 2
    if getattr(args, "full", False) or not getattr(args, "summary", False):
        print(json.dumps(result, indent=2))
        return 0
    _print_learn_summary(result)
    return 0


def _cmd_ssdk_chassis(args: argparse.Namespace) -> int:
    """Print one structure, stability, docking, and kinetics evaluation."""
    import json

    from origami.ssdk.chassis import ChassisError, evaluate_chassis

    try:
        body = json.loads(args.json_body)
        if not isinstance(body, dict):
            raise ValueError("JSON object required")
        report = evaluate_chassis(body)
    except (json.JSONDecodeError, ChassisError, ValueError) as exc:
        print(f"ssdk chassis failed: {exc}", file=sys.stderr)
        return 2
    if args.full:
        print(json.dumps(report, indent=2))
        return 0
    structure = report["structure"]
    stability = report["stability"]
    docking = report["docking"]
    kinetics = report["kinetics"]
    print(f"n_repeats: {report['n_repeats']}")
    print(f"contour_nm: {structure['contour_nm']}")
    print(f"rigid_screw: {structure['rigid_screw']}")
    print(f"tm_C: {stability['tm_C']}")
    print(f"delta_g: {stability['delta_g']}")
    print(f"clash_computable: {docking.get('clash_computable')}")
    print(f"kinetics_computable: {kinetics.get('computable')}")
    print("calibrated: false")
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
    """Freeze a prospective prediction (Docs §1.6).

    Without ``--scaffold`` this is the calcium dose-response. With
    ``--scaffold`` it also records screw geometry and the Phillips
    length curve at ``--n-repeats``. The luminescence interval stays
    the ±30% placeholder in both modes, and that curve does not depend
    on repeat count.
    """
    if getattr(args, "scaffold", False):
        return _cmd_freeze_scaffold(args)
    import json

    from src.core.clasp_assembly import CLASPParameters, predict_luminescence
    from src.predictions.freeze import freeze_prediction
    from src.predictions.luminescence_interval import placeholder_interval
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
        entry = placeholder_interval(value)
        entry["most_sensitive_parameter"] = sens["most_sensitive_parameter"]
        entry["parameter_elasticities"] = sens["elasticities"]
        predictions[f"ca_{c_uM:g}uM"] = entry

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


def _cmd_freeze_scaffold(args: argparse.Namespace) -> int:
    """Freeze geometry and the Phillips length curve at one repeat count."""
    import json

    from src.predictions.scaffold_freeze import write_scaffold_freeze

    if getattr(args, "n_repeats", None) is None:
        print("freeze --scaffold requires --n-repeats", file=sys.stderr)
        return 2
    if not getattr(args, "prediction_id", None):
        print("freeze --scaffold requires --prediction-id", file=sys.stderr)
        return 2
    calcium = [float(item) for item in args.calcium_uM.split(",")]
    path = write_scaffold_freeze(
        args.n_repeats,
        args.prediction_id,
        overwrite=args.overwrite,
        calcium_uM=calcium,
        e_t=args.e_t,
        m_t=args.m_t,
        t_end=args.t_end,
    )
    print(f"[OK] Frozen scaffold prediction written: {path}")
    if args.json:
        print(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2))
    return 0


def _cmd_export_genbank(args: argparse.Namespace) -> int:
    from origami.export.constructs import ConstructError
    from origami.export.genbank import genbank_for_n

    try:
        print(genbank_for_n(args.n_repeats), end="")
    except ConstructError as exc:
        print(f"export-genbank failed: {exc}", file=sys.stderr)
        return 2
    return 0


def _cmd_export_sbol(args: argparse.Namespace) -> int:
    from origami.export.constructs import ConstructError
    from origami.export.sbol import sbol_for_n

    try:
        print(sbol_for_n(args.n_repeats), end="")
    except ConstructError as exc:
        print(f"export-sbol failed: {exc}", file=sys.stderr)
        return 2
    return 0


def _cmd_export_sbml(args: argparse.Namespace) -> int:
    import json

    from origami.export.sbml import sbml_from_kinetics_body
    from origami.kinetics.simulate import KineticsSimError

    try:
        print(sbml_from_kinetics_body(json.loads(args.json_body)), end="")
    except (json.JSONDecodeError, KineticsSimError, ValueError) as exc:
        print(f"export-sbml failed: {exc}", file=sys.stderr)
        return 2
    return 0


def _cmd_passport(args: argparse.Namespace) -> int:
    import json

    from origami.export.passport import chassis_passport
    from origami.ssdk.chassis import ChassisError

    try:
        print(json.dumps(chassis_passport(json.loads(args.json_body)), indent=2, default=str))
    except (json.JSONDecodeError, ChassisError, ValueError) as exc:
        print(f"passport failed: {exc}", file=sys.stderr)
        return 2
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    import json

    from origami.export.benchmark import run_benchmark

    report = run_benchmark()
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


def _cmd_synthetic(args: argparse.Namespace) -> int:
    import json

    from origami.export.synthetic import synthetic_learn_rows

    n_values = [int(x) for x in args.n_values.split(",") if x.strip()]
    print(json.dumps(synthetic_learn_rows(n_values, seed=args.seed), indent=2))
    return 0


def _cmd_batch_chassis(args: argparse.Namespace) -> int:
    import json
    from pathlib import Path

    from origami.export.batch import batch_chassis_csv
    from origami.ssdk.chassis import ChassisError

    try:
        text = Path(args.csv).read_text(encoding="utf-8")
        print(json.dumps(batch_chassis_csv(text), indent=2, default=str))
    except (OSError, ChassisError, ValueError) as exc:
        print(f"batch-chassis failed: {exc}", file=sys.stderr)
        return 2
    return 0


def _cmd_fetch_literature(args: argparse.Namespace) -> int:
    import json
    from pathlib import Path

    from origami.literature.fetch import (
        LiteratureFetchError,
        fetch_and_store,
        search_crossref,
    )

    try:
        if args.seed:
            seed = json.loads(
                Path("data/literature/seed_dois.json").read_text(encoding="utf-8")
            )
            records = []
            for doi in seed["dois"]:
                records.append(fetch_and_store(str(doi)))
            print(json.dumps({"calibrated": False, "records": records}, indent=2))
            return 0
        if args.doi:
            print(json.dumps(fetch_and_store(args.doi), indent=2))
            return 0
        if args.query:
            hits = search_crossref(args.query, rows=args.rows)
            print(
                json.dumps(
                    {
                        "calibrated": False,
                        "usable_as_prior": False,
                        "query": args.query,
                        "hits": hits,
                    },
                    indent=2,
                )
            )
            return 0
    except (LiteratureFetchError, OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"fetch-literature failed: {exc}", file=sys.stderr)
        return 2
    print("fetch-literature needs --doi, --query, or --seed", file=sys.stderr)
    return 2


def _cmd_compare_plate(args: argparse.Namespace) -> int:
    """Score a plate CSV against the checksummed scaffold freezes."""
    import hashlib
    import json
    from pathlib import Path

    from origami.lab.freeze_compare import FreezeCompareError, compare_plate_csv
    from origami.lab.plate_reader import PlateReaderError

    path = Path(args.csv)
    try:
        text = path.read_text(encoding="utf-8")
        report = compare_plate_csv(
            text,
            source=path.name,
            sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )
    except (OSError, UnicodeDecodeError, FreezeCompareError, PlateReaderError) as exc:
        print(f"compare-plate failed: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    propagated = report["parameter_error"]["parameter_error_propagated"]
    print(f"parameter_error_propagated: {propagated}")
    print(report["parameter_error"]["reason"])
    for row in report["comparisons"]:
        if row["status"] != "compared":
            print(
                f"  {row['construct']} n={row['n_repeats']}: {row['status']} — {row['detail']}"
            )
            continue
        flag = "IN" if row["within_95ci"] else "OUT"
        print(
            f"  {row['construct']} n={row['n_repeats']} {row['frozen_key']}: "
            f"obs={row['observed']:.4g} pred={row['predicted']:.4g} "
            f"err={row['error']:+.4g} [{flag}] {row.get('uncertainty_method')}"
        )
    print(f"untested frozen keys: {len(report['untested_predictions'])}")
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
        help="Freeze a prospective prediction (calcium curve, or --scaffold geometry)",
    )
    freeze.add_argument("--prediction-id", type=str, required=True)
    freeze.add_argument(
        "--scaffold",
        action="store_true",
        help=(
            "Also freeze contour, axial span, and the Phillips length curve "
            "at --n-repeats. Luminescence is stored and labelled as independent of n."
        ),
    )
    freeze.add_argument(
        "--n-repeats",
        type=int,
        default=None,
        help="Repeat count for --scaffold (planned series: 3, 8, 14)",
    )
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

    plate_vs = sub.add_parser(
        "compare-plate",
        help="Score a plate CSV against the checksummed scaffold freezes",
    )
    plate_vs.add_argument("csv", help="Plate CSV. Optional column calcium_uM selects the frozen dose.")
    plate_vs.add_argument("--json", action="store_true")
    plate_vs.set_defaults(func=_cmd_compare_plate)

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
    lp.add_argument("--n-min", type=int, default=None)
    lp.add_argument("--n-max", type=int, default=None)
    lp.add_argument(
        "--json-body",
        default=None,
        help="Learn options other than observations (construct, kinetics, quantify_luminescence)",
    )
    lp.add_argument("--summary", action="store_true", help="Print the decision summary instead of JSON")
    lp.set_defaults(func=_cmd_learn_plate)

    ssdk_cmd = sub.add_parser(
        "ssdk",
        help="One entry for chassis evaluation and the shared learner",
    )
    ssdk_sub = ssdk_cmd.add_subparsers(dest="ssdk_command", required=True)
    chassis_cmd = ssdk_sub.add_parser("chassis", help="Structure, stability, docking, and kinetics")
    chassis_cmd.add_argument("--json-body", required=True)
    chassis_cmd.add_argument("--full", action="store_true")
    chassis_cmd.set_defaults(func=_cmd_ssdk_chassis)
    ssdk_learn = ssdk_sub.add_parser("learn", help="Same learner as learn-ssdk")
    ssdk_learn.add_argument("--json-body", required=True)
    ssdk_learn.add_argument("--full", action="store_true")
    ssdk_learn.set_defaults(func=_cmd_learn_ssdk)
    ssdk_plate = ssdk_sub.add_parser(
        "learn-plate",
        help="Plate CSV plus the same learn options, printed as the decision summary",
    )
    ssdk_plate.add_argument("csv")
    ssdk_plate.add_argument("--json-body", default=None)
    ssdk_plate.add_argument("--n-min", type=int, default=None)
    ssdk_plate.add_argument("--n-max", type=int, default=None)
    ssdk_plate.add_argument("--full", action="store_true")
    ssdk_plate.set_defaults(func=_cmd_learn_plate, summary=True)

    ssdk = sub.add_parser(
        "learn-ssdk",
        help="Score a JSON learn body and print the learner family, next n, and batch",
    )
    ssdk.add_argument("--json-body", required=True, help="JSON object for POST /api/ssdk/learn")
    ssdk.add_argument("--full", action="store_true", help="Print the full JSON response")
    ssdk.set_defaults(func=_cmd_learn_ssdk)

    exp_gb = sub.add_parser("export-genbank", help="Protein GenBank for a team n=3,8,14 sequence")
    exp_gb.add_argument("--n-repeats", type=int, required=True)
    exp_gb.set_defaults(func=_cmd_export_genbank)

    exp_sbol = sub.add_parser("export-sbol", help="SBOL 3 XML for a team n=3,8,14 sequence")
    exp_sbol.add_argument("--n-repeats", type=int, required=True)
    exp_sbol.set_defaults(func=_cmd_export_sbol)

    exp_sbml = sub.add_parser("export-sbml", help="SBML for a shipped kinetics mode")
    exp_sbml.add_argument("--json-body", required=True)
    exp_sbml.set_defaults(func=_cmd_export_sbml)

    exp_pass = sub.add_parser("passport", help="JSON chassis passport")
    exp_pass.add_argument("--json-body", required=True)
    exp_pass.set_defaults(func=_cmd_passport)

    bench = sub.add_parser("benchmark", help="Self-test literature tables and exporters")
    bench.set_defaults(func=_cmd_benchmark)

    syn = sub.add_parser("synthetic", help="Labelled dry learner fixtures (not wet data)")
    syn.add_argument("--n-values", default="3,8,14")
    syn.add_argument("--seed", type=int, default=0)
    syn.set_defaults(func=_cmd_synthetic)

    batch = sub.add_parser("batch-chassis", help="Chassis table from a CSV of n_repeats")
    batch.add_argument("csv")
    batch.set_defaults(func=_cmd_batch_chassis)

    lit = sub.add_parser(
        "fetch-literature",
        help="Fetch Crossref/Europe PMC metadata for a DOI or search (no PDFs, no priors)",
    )
    lit.add_argument("--doi", default=None)
    lit.add_argument("--query", default=None)
    lit.add_argument("--rows", type=int, default=5)
    lit.add_argument("--seed", action="store_true", help="Fetch data/literature/seed_dois.json")
    lit.set_defaults(func=_cmd_fetch_literature)

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
