import type { Metadata } from "next";
import { KineticsBoard } from "@/components/kinetics-board";

export const metadata: Metadata = {
  title: "How much is bound? · ORIGAMI",
  description:
    "Bound fraction, Spy lock over time, and light-reporter complex from published rates. Not measured on this fusion.",
};

export default function KineticsPage() {
  return <KineticsBoard pane="bound" />;
}
