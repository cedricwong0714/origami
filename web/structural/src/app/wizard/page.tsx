import type { Metadata } from "next";
import { WizardBoard } from "@/components/wizard-board";

export const metadata: Metadata = {
  title: "Step through one length · ORIGAMI",
  description: "Pick n = 3, 8, or 14 and read the screw, melt, and docking distance.",
};

export default function WizardPage() {
  return <WizardBoard />;
}
