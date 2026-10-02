import type { Metadata } from "next";
import { IntakeBoard } from "@/components/intake-board";

export const metadata: Metadata = {
  title: "Data intake · ORIGAMI",
  description:
    "Plate-reader CSV import with per-batch blank correction, and the grouped ablation check. calibrated = false.",
};

export default function IntakePage() {
  return <IntakeBoard />;
}
