import type { Metadata } from "next";
import { ThermoCalculator } from "@/components/thermo-calculator";

export const metadata: Metadata = {
  title: "Estimate ΔG · ORIGAMI",
  description:
    "Unfolding energy at a temperature you choose. At the melting temperature, that energy is 0. The paper’s printed value is shown separately.",
};

export default function ThermoCalculatorPage() {
  return <ThermoCalculator />;
}
