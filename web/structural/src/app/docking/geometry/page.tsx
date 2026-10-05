import type { Metadata } from "next";
import { DockingBoard } from "@/components/docking-board";

export const metadata: Metadata = {
  title: "Distance and clash · ORIGAMI",
  description: "Straight-line end distance, overlap chance, and crowding for any repeat count from 3 to 24.",
};

export default function DockingGeometryPage() {
  return <DockingBoard pane="geometry" />;
}
