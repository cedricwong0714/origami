import type { Metadata } from "next";
import { KineticsBoard } from "@/components/kinetics-board";

export const metadata: Metadata = {
  title: "Scaffold kinetics · ORIGAMI",
  description:
    "Bound fraction, Spy lock over time, and LgBiT–SmBiT complex from published rates. Not measured on this fusion.",
};

export default function KineticsPage() {
  return <KineticsBoard pane="bound" />;
}
