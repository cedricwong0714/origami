import type { Metadata } from "next";
import { ThermoCalculator } from "@/components/thermo-calculator";

export const metadata: Metadata = {
  title: "Estimate ΔG · ORIGAMI",
  description:
    "Estimate unfolding ΔG at temperatures other than the melt. At Tm, ΔG is 0 for a two-state melt. The paper’s table value is shown separately. Full ΔG(T), ΔH(T), and ΔS(T) curves need both ΔHcal and ΔCp. calibrated = false.",
};

export default function ThermoCalculatorPage() {
  return <ThermoCalculator />;
}
