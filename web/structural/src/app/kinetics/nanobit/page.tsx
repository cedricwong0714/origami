import type { Metadata } from "next";
import { KineticsBoard } from "@/components/kinetics-board";

export const metadata: Metadata = {
  title: "Light reporter · ORIGAMI",
  description: "NanoBiT complex from the Dixon 2016 rates and concentrations you type.",
};

export default function NanoBitKineticsPage() {
  return <KineticsBoard pane="nanobit" />;
}