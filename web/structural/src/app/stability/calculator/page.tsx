import type { Metadata } from "next";
import { ThermoCalculator } from "@/components/thermo-calculator";

export const metadata: Metadata = {
  title: "ΔG calculator · ORIGAMI",
  description:
    "ΔG at the melting temperature is 0 for a two-state transition. ΔH and ΔS are not required. Optional ΔHcal and ΔCp draw the temperature curves. calibrated stays false.",
};

export default function ThermoCalculatorPage() {
  return <ThermoCalculator />;
}
