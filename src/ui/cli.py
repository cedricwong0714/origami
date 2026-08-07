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
