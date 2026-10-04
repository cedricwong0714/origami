import type { Metadata } from "next";
import { IntakeBoard } from "@/components/intake-board";

export const metadata: Metadata = {
  title: "Data intake · ORIGAMI",
  description:
    "Paste a plate file. Blanks are subtracted per batch. A pass against a saved luminescence band is a placeholder.",
};

export default function IntakePage() {
  return <IntakeBoard />;
}
