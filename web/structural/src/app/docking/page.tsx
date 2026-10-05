import type { Metadata } from "next";
import { DockingBoard } from "@/components/docking-board";

export const metadata: Metadata = {
  title: "Will it bind? · ORIGAMI",
  description:
    "Compare a typed tightness with how crowded the two ends are, then with the light reporter and the Spy lock.",
};

export default function DockingPage() {
  return <DockingBoard pane="affinity" />;
}
