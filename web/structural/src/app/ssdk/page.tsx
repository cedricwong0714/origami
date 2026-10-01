import type { Metadata } from "next";
import { SsdkBoard } from "@/components/ssdk-board";

export const metadata: Metadata = {
  title: "SSDK chassis · ORIGAMI",
  description:
    "Structure, stability, docking, and kinetics for one CTPR length. calibrated = false.",
};

export default function SsdkPage() {
  return <SsdkBoard />;
}
