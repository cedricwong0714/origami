import type { Metadata } from "next";
import { WizardBoard } from "@/components/wizard-board";

export const metadata: Metadata = {
  title: "Design wizard · ORIGAMI",
  description: "Step through chassis evaluation and a software passport.",
};

export default function WizardPage() {
  return <WizardBoard />;
}
