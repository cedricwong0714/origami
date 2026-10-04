import type { Metadata } from "next";
import { DockingBoard } from "@/components/docking-board";

export const metadata: Metadata = {
  title: "Docking affinity · ORIGAMI",
  description:
    "Compare a typed Kd or Ka with the local concentration, then with LgBiT–SmBiT and SpyCatcher–SpyTag.",
};

export default function DockingPage() {
  return <DockingBoard pane="affinity" />;
}
