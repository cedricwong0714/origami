import type { Metadata } from "next";
import { StabilityBoard } from "@/components/stability-board";

export const metadata: Metadata = {
  title: "Stability confirmation · ORIGAMI",
  description:
    "Calculated melting temperature and unfolding ΔG at n = 3, 8, and 14. Pass or fail at 37 °C uses the calculated melt from each paper’s fit. Nothing here is calibrated to wet-lab data (calibrated = false).",
};

export default function StabilityPage() {
  return <StabilityBoard />;
}
