import type { Metadata } from "next";
import { ThermoCalculator } from "@/components/thermo-calculator";

export const metadata: Metadata = {
  title: "ΔG calculator · ORIGAMI",
  description:
    "Two-state Gibbs–Helmholtz arithmetic for caller-supplied ΔH, ΔCp, and Tm. calibrated stays false.",
};

export default function ThermoCalculatorPage() {
  return <ThermoCalculator />;
}
