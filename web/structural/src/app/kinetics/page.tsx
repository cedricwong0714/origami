import type { Metadata } from "next";
import { KineticsBoard } from "@/components/kinetics-board";

export const metadata: Metadata = {
  title: "Scaffold kinetics · ORIGAMI",
  description:
    "Literature-prior kinetics emulation with vacant lab Spy rates. calibrated = false, hypothesis_only.",
};

export default function KineticsPage() {
  return <KineticsBoard />;
}
