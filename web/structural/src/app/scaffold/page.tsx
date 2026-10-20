import type { Metadata } from "next";
import { StructuralStudio } from "@/components/structural-studio";

export const metadata: Metadata = {
  title: "3D scaffold · ORIGAMI",
  description: "Helical coordinates of the CTPR repeats, drawn as a screw.",
};

export default function ScaffoldPage() {
  return <StructuralStudio />;
}
