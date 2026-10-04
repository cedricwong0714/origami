import type { Metadata } from "next";
import { KineticsBoard } from "@/components/kinetics-board";

export const metadata: Metadata = {
  title: "SpyCatcher–SpyTag · ORIGAMI",
  description: "Spy lock time course from the Zakeri 2012 rate, or from rates you type.",
};

export default function SpyKineticsPage() {
  return <KineticsBoard pane="spy" />;
}
