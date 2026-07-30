# src/ui/cli.py
import argparse
import sys
from src.core.schema import DesignSpec, ScaffoldSpec, MoCloPart
from src.ui.dashboard_backend import PipelineController

def main():
    parser = argparse.ArgumentParser(description="CLASP Synthetic Biology Design Copilot CLI")
    parser.add_argument("--design-id", type=str, default="CLI_DESIGN_001", help="Unique design identifier")
    parser.add_argument("--chassis", type=str, default="E_coli", choices=["cell_free", "E_coli", "B_subtilis"])
    args = parser.parse_args()

    print(f"=== Running CLASP Pipeline for {args.design_id} ({args.chassis}) ===")

    spec = DesignSpec(
        design_id=args.design_id,
        chassis=args.chassis,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[2, 4],
            persistence_length_nm=15.0
        ),
        payload_ids=["OtsA", "OtsB"],
        operating_mode="reversible"
    )

    parts = [
        MoCloPart(part_id="Promoter_J23100", overhang_5prime="GGAG", overhang_3prime="AATG", sequence="TTGACAGCTAGCTCAGTCCTAGGTATAATACTAGT"),
        MoCloPart(part_id="RBS_B0034", overhang_5prime="AATG", overhang_3prime="CGCT", sequence="AAAGAGGAGAA")
    ]

    initial_concs = {"S": 1.0, "E": 0.1, "ES": 0.0, "P": 0.0}

    controller = PipelineController()
    results = controller.run_full_pipeline(spec, parts, initial_concs)

    if results["status"] == "SUCCESS":
        print("[SUCCESS] Design passed multi-layer verification!")
        print(f"Compiled DNA Length: {len(results['assembled_dna'])} bp")
        print("GenBank Preview:")
        print(results["genbank_file"].split("\n")[0])
    else:
        print("[FAILED] Verification errors encountered:")
        for err in results["verification_report"].errors:
            print(f"  - {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()