import type { Metadata } from "next";
import { KineticsBoard } from "@/components/kinetics-board";

export const metadata: Metadata = {
  title: "Scaffold kinetics · ORIGAMI",
  description:
    "Stage-1 kinetics schema with vacant SpyTag rates and CaM–M13 recruitment steady state. calibrated = false.",
};

export default function KineticsPage() {
  return <KineticsBoard />;
}
