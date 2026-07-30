# src/ui/dashboard_backend.py
import numpy as np
from typing import Optional

from src.core.schema import DesignSpec, MoCloPart, VerificationReport
from src.moclo_compiler.assembly import assemble_level1_vector
from src.moclo_compiler.genbank import generate_genbank_file
from src.ode_model.solver import run_system_simulation
from src.verification.engine import evaluate_design
from src.evidence_engine.retriever import EvidenceRetriever
from src.gp_model.trainer import GPCorrectionModel
from src.gp_model.predictor import predict_augmented_kinetics
from src.experiment_design.generator import ExperimentGenerator

class PipelineController:
    def __init__(self):
        self.evidence_retriever = EvidenceRetriever()

    def run_full_pipeline(
        self,
        spec: DesignSpec,
        parts: list[MoCloPart],
        initial_concentrations: dict[str, float],
        time_span: tuple[float, float] = (0.0, 100.0),
        experimental_data: Optional[np.ndarray] = None
    ) -> dict:
        output = {}

        # 1. Multi-Layer Verification
        report: VerificationReport = evaluate_design(spec, parts, initial_concentrations)
        output["verification_report"] = report

        if not report.is_valid:
            output["status"] = "VERIFICATION_FAILED"
            return output

        # 2. MoClo Vector Assembly & GenBank Generation
        assembled_dna = assemble_level1_vector(parts)
        genbank_file = generate_genbank_file(spec.design_id, parts, assembled_dna)
        output["assembled_dna"] = assembled_dna
        output["genbank_file"] = genbank_file

        # Match time grid size to experimental_data length if provided
        num_points = len(experimental_data) if experimental_data is not None else 100

        # 3. Baseline ODE Kinetic Integration
        time_points, concentrations = run_system_simulation(
            initial_concentrations, 
            time_span, 
            num_points=num_points
        )
        output["time_points"] = time_points
        output["baseline_concentrations"] = concentrations

        # 4. GP Correction & Active Learning
        if experimental_data is not None and "P" in concentrations:
            gp = GPCorrectionModel()
            ode_product = concentrations["P"]
            gp.fit(time_points, ode_product, experimental_data)

            augmented_results = predict_augmented_kinetics(time_points, ode_product, gp)
            output["augmented_kinetics"] = augmented_results

            generator = ExperimentGenerator(gp)
            recommendations = generator.suggest_next_experiments(
                candidate_time_points=time_points,
                candidate_ode_baseline=ode_product,
                top_k=3,
                strategy="UCB"
            )
            output["next_experiment_recommendations"] = recommendations

        output["status"] = "SUCCESS"
        return output