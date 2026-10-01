import type { Metadata } from "next";
import { LabBoard } from "@/components/lab-board";

export const metadata: Metadata = {
  title: "Lab chassis · ORIGAMI",
  description:
    "Intake for concentration, calcium EC50, SpyCatcher lock kinetics, and the four-tube bridge. calibrated = false.",
};

export default function LabPage() {
  return <LabBoard />;
}
