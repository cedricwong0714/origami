import type { Metadata } from "next";
import { ThermoCalculator } from "@/components/thermo-calculator";

export const metadata: Metadata = {
  title: "Estimate ΔG · ORIGAMI",
  description:
    "ΔG at the melting temperature is 0 for a two-state melt. The paper’s unfolding ΔG stays the table value. Full temperature curves appear only after ΔHcal and ΔCp are typed. calibrated stays false.",
};

export default function ThermoCalculatorPage() {
  return <ThermoCalculator />;
}
