import type { Metadata } from "next";
import { DockingBoard } from "@/components/docking-board";

export const metadata: Metadata = {
  title: "Docking geometry · ORIGAMI",
  description: "Screw distance, clash, and local concentration for any repeat count from 3 to 24.",
};

export default function DockingGeometryPage() {
  return <DockingBoard pane="geometry" />;
}
