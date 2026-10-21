import type { Metadata } from "next";
import { WizardBoard } from "@/components/wizard-board";

export const metadata: Metadata = {
  title: "Step through one length · ORIGAMI",
  description: "Pick a repeat count from 3 to 24 and read the screw, melt, and docking distance.",
};

export default function WizardPage() {
  return <WizardBoard />;
}
